import asyncio
import uuid
import re
import time
import hashlib
from urllib.parse import urlparse
import urllib.robotparser as urobot

from bs4 import BeautifulSoup
import httpx

# Optional quality/extraction deps (auto-fallback if missing)
try:
    import trafilatura  # pip install trafilatura
except Exception:
    trafilatura = None

try:
    from simhash import Simhash  # pip install simhash
except Exception:
    Simhash = None

# ---- Your own imports (kept)
from controller.embed import insert_embedding_logic

# ===============================
# Config
# ===============================
API_URL = "http://127.0.0.1:8000/message"  # your FastAPI chat endpoint
SEARXNG_URL = "http://localhost:8888/search"  # SearxNG base
TIMEOUT = httpx.Timeout(60.0)
HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/125 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
}
MAX_BYTES = 2_000_000
DEFAULT_PER_HOST_DELAY = 3.0
EMBED_MAX_TOKENS = 800
EMBED_OVERLAP = 100
SUMMARIZE_BEFORE_EMBED = False

# Quality knobs
MIN_TEXT_CHARS = 400  # drop ultra-short pages
QUALITY_THRESHOLD = 0.45
NEAR_DUP_HAMMING = 3

# ===============================
# Keyword prompt
# ===============================
CONTEXT = (
    "You are a curious software developer who wants to stay updated on the latest in software development and technology. "
    "Your job is to suggest a SINGLE concise keyword or short phrase (2–4 words max) specifically about programming languages, frameworks, developer tools, AI for coding, infrastructure, UI/UX, or emerging practical tech trends. "
    "Reply ONLY in English with that keyword or phrase, no sentences, no lists, no explanations."
)
PROMPT = "Suggest a keyword search for today."

# ===============================
# Utilities
# ===============================
_last_hit: dict[str, float] = {}
_robots_cache: dict[str, tuple[urobot.RobotFileParser | None, float]] = {}
_seen_simhashes: set[int] = set()

STOPWORDS = set("""
    the of and to in a is that for on with as it by from an at this be are was or if not but have has you your we our they their can will about into over after more other using new via also than
""".split())

def now() -> float:
    return time.time()

async def throttle(host: str, delay: float):
    t = _last_hit.get(host, 0.0)
    wait = max(0.0, delay - (now() - t))
    if wait > 0:
        await asyncio.sleep(wait)
    _last_hit[host] = now()

def tokenish_len(s: str) -> int:
    return len(re.findall(r"\S+", s))

def chunk_text(text: str, max_tokens: int = EMBED_MAX_TOKENS, overlap: int = EMBED_OVERLAP) -> list[str]:
    paras = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks: list[str] = []
    buf: list[str] = []
    buf_tokens = 0

    for p in paras:
        t = tokenish_len(p)
        if t > max_tokens:
            words = p.split()
            i = 0
            step = max(1, max_tokens - overlap)
            while i < len(words):
                piece = " ".join(words[i:i + max_tokens])
                chunks.append(piece)
                i += step
            continue

        if buf_tokens + t <= max_tokens:
            buf.append(p)
            buf_tokens += t
        else:
            if buf:
                merged = "\n\n".join(buf)
                chunks.append(merged)
                tail_words = merged.split()[-overlap:]
                buf = [" ".join(tail_words), p]
                buf_tokens = len(tail_words) + t
            else:
                chunks.append(p)

    if buf:
        chunks.append("\n\n".join(buf))
    return chunks

def sha256_text(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()

# ===============================
# Quality functions
# ===============================

def stopword_ratio(s: str) -> float:
    words = re.findall(r"\b\w+\b", s.lower())
    if not words:
        return 0.0
    sw = sum(1 for w in words if w in STOPWORDS)
    return sw / max(1, len(words))


def title_overlap(title: str, text: str) -> float:
    tw = set(re.findall(r"\b\w+\b", (title or "").lower()))
    cw = set(re.findall(r"\b\w+\b", (text or "").lower()))
    if not tw or not cw:
        return 0.0
    return len(tw & cw) / max(1, len(tw))


def quality_score(title: str, text: str) -> float:
    n_chars = len(text)
    n_words = len(re.findall(r"\b\w+\b", text))
    swr = stopword_ratio(text)
    tov = title_overlap(title, text)
    score = (
        (min(n_words, 1200) / 1200.0) * 0.45 +
        (min(swr, 0.65) / 0.65) * 0.25 +
        min(tov, 0.6) * 0.15 +
        (min(n_chars, 8000) / 8000.0) * 0.15
    )
    return score


def passes_quality(title: str, text: str) -> bool:
    if len(text) < MIN_TEXT_CHARS:
        return False
    return quality_score(title, text) >= QUALITY_THRESHOLD


def simhash_text(s: str) -> int | None:
    if not Simhash:
        return None
    tokens = re.findall(r"\w+", s.lower())
    return Simhash(tokens).value if tokens else None


def is_near_duplicate(s: str, hamming_threshold: int = NEAR_DUP_HAMMING) -> bool:
    h = simhash_text(s)
    if h is None:
        return False  # no simhash installed; skip dup check
    for existing in _seen_simhashes:
        if bin(h ^ existing).count("1") <= hamming_threshold:
            return True
    _seen_simhashes.add(h)
    return False

# ===============================
# Robots.txt handling
# ===============================
async def load_robots(client: httpx.AsyncClient, base_url: str) -> tuple[urobot.RobotFileParser | None, float]:
    host = urlparse(base_url).netloc
    if host in _robots_cache:
        return _robots_cache[host]

    scheme = urlparse(base_url).scheme or "http"
    robots_url = f"{scheme}://{host}/robots.txt"

    rp = urobot.RobotFileParser()
    delay = DEFAULT_PER_HOST_DELAY

    try:
        r = await client.get(robots_url, headers=HEADERS, timeout=10.0)
        if r.status_code == 200 and r.text:
            rp.parse(r.text.splitlines())
            m = re.search(r"(?im)^\s*crawl-delay\s*:\s*([\d.]+)\s*$", r.text)
            if m:
                delay = float(m.group(1))
        else:
            rp = None
    except Exception:
        rp = None

    _robots_cache[host] = (rp, delay)
    return _robots_cache[host]


async def allowed_by_robots(client: httpx.AsyncClient, url: str, ua: str = "*") -> tuple[bool, float]:
    rp, delay = await load_robots(client, url)
    allowed = True if rp is None else rp.can_fetch(ua, url)
    return allowed, delay

# ===============================
# Extraction (trafilatura first, fallback to BS4)
# ===============================

def extract_readable(html: str, base_url: str | None = None) -> tuple[str, str | None, str]:
    # Try trafilatura when available
    if trafilatura is not None:
        try:
            text = trafilatura.extract(
                html,
                include_tables=False,
                include_comments=False,
                favor_precision=True,
                url=base_url,
            )
            if text:
                meta = None
                try:
                    meta = trafilatura.metadata.extract_metadata(html, url=base_url)
                except Exception:
                    meta = None
                title = getattr(meta, "title", "") if meta else ""
                date = getattr(meta, "date", None) if meta else None
                return (title or "", date, text.strip())
        except Exception:
            pass

    # Fallback: BeautifulSoup heuristic with tolerant parser
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript", "iframe"]):
        tag.decompose()
    node = soup.find("article") or soup.find("main") or soup.body or soup
    for tag in node.find_all(["nav", "aside", "footer", "form"]):
        tag.decompose()
    title = (soup.title.string or "").strip() if soup.title and soup.title.string else ""
    meta_date = None
    md = (
        soup.find("meta", {"property": "article:published_time"})
        or soup.find("meta", {"name": "date"})
        or soup.find("meta", {"property": "og:article:published_time"})
    )
    if md and md.get("content"):
        meta_date = md["content"]
    text = node.get_text(separator="\n", strip=True)
    text = re.sub(r"\n{2,}", "\n\n", text)
    return title, meta_date, text

# ===============================
# HTTP helpers
# ===============================
async def fetch_page(client: httpx.AsyncClient, url: str) -> str | None:
    try:
        host = urlparse(url).netloc
        allowed, delay = await allowed_by_robots(client, url)

        if not allowed:
            print(f"[robots] Disallowed: {url}")
            return None

        await throttle(host, delay)

        r = await client.get(url, headers=HEADERS, timeout=TIMEOUT, follow_redirects=True)
        if r.status_code >= 400:
            print(f"[fetch] {url} -> HTTP {r.status_code}")
            return None
        if len(r.content) > MAX_BYTES:
            print(f"[fetch] {url} -> too large ({len(r.content)} bytes)")
            return None

        ctype = (r.headers.get("content-type") or "").lower()
        if ("text/html" not in ctype) and ("application/xhtml" not in ctype):
            print(f"[fetch] {url} -> skipped content-type: {ctype}")
            return None

        return r.text
    except Exception as e:
        print(f"[fetch] {url} -> error: {e}")
        return None

# ===============================
# SearxNG HTML fallback search
# ===============================
async def searxng_search(client: httpx.AsyncClient, keyword: str, num: int = 10) -> list[dict]:
    url = f"{SEARXNG_URL}?q={keyword}"
    r = await client.get(url, headers=HEADERS, timeout=TIMEOUT)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    results = []
    for result in soup.select(".result")[:num]:
        a = result.select_one(".url_header")
        h3 = result.select_one("h3")
        p = result.select_one(".content")
        title = h3.get_text(strip=True) if h3 else ""
        link = a.get("href") if a else ""
        content = p.get_text(strip=True) if p else ""
        # quick URL hygiene: skip empty/bad links
        if not link:
            continue
        results.append({"title": title, "url": link, "content": content})
    return results

# ===============================
# AI chat
# ===============================
async def ai_chat(client: httpx.AsyncClient, context: str, prompt: str, session_id: str) -> str:
    resp_txt = ""
    async with client.stream(
        "POST",
        API_URL,
        json={
            "context": context,
            "text": prompt,
            "playAudio": False,
            "session_id": session_id,
            "stream": True,
        },
        headers={"Content-Type": "application/json"},
        timeout=TIMEOUT,
    ) as s:
        async for chunk in s.aiter_text():
            print(chunk, end="", flush=True)
            resp_txt += chunk
    return resp_txt.strip()

# ===============================
# Pipeline
# ===============================
async def process_url(client: httpx.AsyncClient, url: str, query: str):
    html = await fetch_page(client, url)
    if not html:
        return

    title, published_at, text = extract_readable(html, base_url=url)
    if not text or tokenish_len(text) < 10:
        return

    # Quality gate
    if not passes_quality(title, text):
        print(f"[quality] dropped {url}")
        return

    # Near-duplicate filter (page-level)
    if is_near_duplicate(text):
        print(f"[dup] dropped {url}")
        return

    chunks = chunk_text(text, max_tokens=EMBED_MAX_TOKENS, overlap=EMBED_OVERLAP)

    if SUMMARIZE_BEFORE_EMBED:
        for chunk in chunks:
            sid = str(uuid.uuid4())
            summary = await ai_chat(
                client,
                "You prepare data for RAG. Extract only the most important facts. "
                "Return a concise factual summary in plain text, < 768 characters.",
                f"Summarize for RAG:\n{chunk}",
                sid,
            )
            for piece in chunk_text(summary, max_tokens=700, overlap=0):
                decorated = (
                    f"{query.upper()} — {title} — {url}\n"
                    f"PUBLISHED: {published_at or 'unknown'}\n\n"
                    f"{piece}"
                )
                await insert_embedding_logic([decorated])
    else:
        for i, chunk in enumerate(chunks):
            decorated = (
                f"{query.upper()} — {title} — {url}\n"
                f"PUBLISHED: {published_at or 'unknown'}\n\n"
                f"{chunk}"
            )
            await insert_embedding_logic([decorated])

    print(f"[indexed] {url} ({len(chunks)} chunks)")

async def main():
    print("Running search…")
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT, headers=HEADERS, follow_redirects=True) as client:
            while True:
                session_id = str(uuid.uuid4())
                keyword = await ai_chat(client, CONTEXT, PROMPT, session_id)
                print(f"\n\n[keyword] {keyword}\n")

                results = await searxng_search(client, keyword, num=3)
                print(f"[searxng] {len(results)} results")

                for r in results:
                    url = r["url"]
                    title = r["title"]
                    print(f"\n==> {title}\n{url}")
                    await process_url(client, url, keyword)
                    await asyncio.sleep(2.0)

                await asyncio.sleep(15.0)

    except Exception as e:
        print(f"[error] {e}")
    finally:
        print("Search complete.")

if __name__ == "__main__":
    asyncio.run(main())
