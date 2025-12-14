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
AI_NEXT_KEYWORD_FROM_RESULTS = (
    True  # after scraping results, ask AI to suggest the next keyword based on content
)
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
EMBED_MAX_TOKENS = 650
EMBED_OVERLAP = 100
SUMMARIZE_BEFORE_EMBED = False

# Quality knobs
MIN_TEXT_CHARS = 400  # drop ultra-short pages
QUALITY_THRESHOLD = 0.45
NEAR_DUP_HAMMING = 3

# Authoritative domains filter
authoritative_sites = [
    # Core languages / docs
    "developer.mozilla.org",
    "docs.github.com",
    "python.org",
    "react.dev",
    "nodejs.org",
    "kubernetes.io",
    "cloud.google.com",
    "aws.amazon.com",
    "learn.microsoft.com",
    # Frameworks & ecosystems
    "angular.dev",
    "vuejs.org",
    "nextjs.org",
    "nuxt.com",
    "flutter.dev",
    "dart.dev",
    # AI / ML developer platforms
    "pytorch.org",
    "tensorflow.org",
    "huggingface.co/docs",
    "langchain.com",
    # Infra / Cloud Native
    "cncf.io",
    "helm.sh",
    "prometheus.io",
    "grafana.com/docs",
    "hashicorp.com",
    # Databases
    "postgresql.org/docs",
    "mongodb.com/docs",
    "redis.io/docs",
    # DevOps & CI/CD
    "docker.com",
    "docs.gitlab.com",
    "circleci.com/docs",
]


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
SEEN_KEYWORDS_PATH = "seen_keywords.txt"  # persisted across runs

_last_hit: dict[str, float] = {}
_robots_cache: dict[str, tuple[urobot.RobotFileParser | None, float]] = {}
_seen_simhashes: set[int] = set()

STOPWORDS = set(
    """
    the of and to in a is that for on with as it by from an at this be are was or if not but have has you your we our they their can will about into over after more other using new via also than
""".split()
)


def now() -> float:
    return time.time()


def normalize_keyword(kw: str) -> str:
    """Lowercase, strip extra spaces and commas, keep 2–4 words."""
    kw = kw.replace(",", " ")
    parts = [p for p in kw.lower().split() if p]
    return " ".join(parts[:4])


def load_seen_keywords(path: str = SEEN_KEYWORDS_PATH) -> set[str]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return {line.strip() for line in f if line.strip()}
    except FileNotFoundError:
        return set()


# ---- AI-assisted next keyword selection from scraped content ----
async def ai_candidates_from_text(
    client: httpx.AsyncClient, text: str, k: int = 5
) -> list[str]:
    """Ask AI for concise keyword candidates from a page's text."""
    sid = str(uuid.uuid4())
    prompt = (
        "From the following technical content, extract up to "
        + str(k)
        + " concise search keywords (2-4 words each)."
        "Focus on software engineering topics (frameworks, APIs, tooling, performance, security, migration, releases)."
        "Return them one per line, lowercase, no punctuation, no numbering, no explanations."
        + text[:4000]  # trim for safety
    )
    out = await ai_chat(client, "You curate developer search terms.", prompt, sid)
    lines = [ln.strip().lower() for ln in out.splitlines() if ln.strip()]
    # normalize + keep 2-4 words
    cands = []
    for ln in lines:
        norm = normalize_keyword(ln)
        if 2 <= len(norm.split()) <= 4:
            cands.append(norm)
    return cands[:k]


async def propose_next_keyword(
    client: httpx.AsyncClient,
    urls: list[str],
    seen: set[str],
    per_page_chars: int = 3000,
) -> str:
    """Fetch a few pages, ask AI for keyword candidates per page, then pick the best unseen one by frequency and cross-doc presence."""
    all_cands: list[str] = []
    appeared_in_doc: dict[str, int] = {}
    fetched = 0
    for u in urls:
        if fetched >= 6:  # cap pages we consult for next keyword
            break
        html = await fetch_page(client, u)
        if not html:
            continue
        title, _, text = extract_readable(html, base_url=u)
        if not text:
            continue
        # take a slice to keep prompts small
        sample = (title + "" + text)[:per_page_chars]
        cands = await ai_candidates_from_text(client, sample, k=5)
        if not cands:
            continue
        fetched += 1
        # update global pools
        seen_in_this_doc = set()
        for c in cands:
            all_cands.append(c)
            if c not in seen_in_this_doc:
                appeared_in_doc[c] = appeared_in_doc.get(c, 0) + 1
                seen_in_this_doc.add(c)

    if not all_cands:
        return ""

    # rank by frequency and cross-doc diversity
    freq: dict[str, int] = {}
    for c in all_cands:
        freq[c] = freq.get(c, 0) + 1

    scored: list[tuple[str, float]] = []
    for c, f in freq.items():
        diversity = appeared_in_doc.get(c, 1)
        score = f * (1.0 + 0.75 * (diversity > 1))
        scored.append((c, score))
    scored.sort(key=lambda x: x[1], reverse=True)

    # Build a shortlist and let AI pick ONE best
    shortlist = [c for c, _ in scored if c not in seen][:10]
    if not shortlist:
        return ""

    sid = str(uuid.uuid4())
    prompt = (
        "Pick ONE best next search keyword from this list (2-4 words, lowercase)."
        "Prioritize specificity, technical relevance, and cross-source recurrence."
        "Return ONLY the keyword, no punctuation or extra text." + "".join(shortlist)
    )
    chosen = await ai_chat(
        client, "You choose one keyword for further developer research.", prompt, sid
    )
    return normalize_keyword(chosen).strip()


def save_seen_keyword(kw: str, path: str = SEEN_KEYWORDS_PATH) -> None:
    with open(path, "a", encoding="utf-8") as f:
        f.write(kw + "\n")


async def throttle(host: str, delay: float):
    t = _last_hit.get(host, 0.0)
    wait = max(0.0, delay - (now() - t))
    if wait > 0:
        await asyncio.sleep(wait)
    _last_hit[host] = now()


def tokenish_len(s: str) -> int:
    return len(re.findall(r"\S+", s))


def chunk_text(
    text: str, max_tokens: int = EMBED_MAX_TOKENS, overlap: int = EMBED_OVERLAP
) -> list[str]:
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
                piece = " ".join(words[i : i + max_tokens])
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


def build_site_filtered_query(keyword: str) -> str:
    site_filter = " OR ".join(f"site:{d}" for d in authoritative_sites)
    return f"({keyword}) ({site_filter})"


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
        (min(n_words, 1200) / 1200.0) * 0.45
        + (min(swr, 0.65) / 0.65) * 0.25
        + min(tov, 0.6) * 0.15
        + (min(n_chars, 8000) / 8000.0) * 0.15
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


async def load_robots(
    client: httpx.AsyncClient, base_url: str
) -> tuple[urobot.RobotFileParser | None, float]:
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


async def allowed_by_robots(
    client: httpx.AsyncClient, url: str, ua: str = "*"
) -> tuple[bool, float]:
    rp, delay = await load_robots(client, url)
    allowed = True if rp is None else rp.can_fetch(ua, url)
    return allowed, delay


# ===============================
# Extraction (trafilatura first, fallback to BS4)
# ===============================


def extract_readable(
    html: str, base_url: str | None = None
) -> tuple[str, str | None, str]:
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
    title = (
        (soup.title.string or "").strip() if soup.title and soup.title.string else ""
    )
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

        r = await client.get(
            url, headers=HEADERS, timeout=TIMEOUT, follow_redirects=True
        )
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
async def searxng_search(
    client: httpx.AsyncClient, keyword: str, num: int = 10
) -> list[dict]:
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
async def ai_chat(
    client: httpx.AsyncClient, context: str, prompt: str, session_id: str
) -> str:
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
# Pipeline helpers (discovery-driven keywording + AI next-keyword)
# ===============================
# ===============================


def current_year() -> int:
    return time.gmtime().tm_year


DISCOVERY_TEMPLATES = [
    "best practices {year}",
    "what's new {year}",
    "release notes {year}",
    "migration guide {year}",
    "deprecations {year}",
    "roadmap {year}",
    "performance tips {year}",
    "security best practices {year}",
]


def clean_text_for_phrases(s: str) -> str:
    # Keep alphanumerics, space, dash, underscore, slash without regex
    return "".join(ch if (ch.isalnum() or ch in " -_/") else " " for ch in s)


def extract_headings_and_title(html: str) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    texts: list[str] = []
    if soup.title and soup.title.string:
        texts.append(soup.title.string.strip())
    for tag in soup.find_all(["h1", "h2", "h3"]):
        txt = (tag.get_text(" ") or "").strip()
        if txt:
            texts.append(txt)
    for p in soup.find_all("p")[:5]:
        txt = (p.get_text(" ") or "").strip()
        if txt:
            texts.append(txt)
    return texts


def candidate_phrases_from_texts(texts: list[str], max_len: int = 4) -> list[str]:
    candidates: set[str] = set()
    for t in texts:
        t = clean_text_for_phrases(t.lower())
        words = [w for w in t.split() if w]
        n = len(words)
        for L in range(1, max_len + 1):
            for i in range(0, max(0, n - L + 1)):
                gram = words[i : i + L]
                while gram and gram[0] in STOPWORDS:
                    gram = gram[1:]
                while gram and gram[-1] in STOPWORDS:
                    gram = gram[:-1]
                if not gram:
                    continue
                if all((w in STOPWORDS or len(w) == 1) for w in gram):
                    continue
                phrase = " ".join(gram)
                if 2 <= len(phrase) <= 50:
                    candidates.add(phrase)
    return list(candidates)


def score_candidates(
    cands: list[str], docs_per_phrase: dict[str, int]
) -> list[tuple[str, float]]:
    freq: dict[str, int] = {}
    for c in cands:
        freq[c] = freq.get(c, 0) + 1
    scored: list[tuple[str, float]] = []
    for c, f in freq.items():
        diversity = docs_per_phrase.get(c, 1)
        length_boost = min(4, max(1, len(c.split()))) / 4.0
        score = f * (1.0 + 0.5 * (diversity > 1)) * length_boost
        scored.append((c, score))
    scored.sort(key=lambda x: x[1], reverse=True)
    return scored


async def discover_keyword(
    client: httpx.AsyncClient, year: int, per_query: int = 3, cap_pages: int = 20
) -> list[str]:
    """Search authoritative sites for current-year best practices/trends, then mine headings/titles into candidate keywords."""
    queries = [tpl.format(year=year) for tpl in DISCOVERY_TEMPLATES]
    site_filter = " OR ".join(f"site:{d}" for d in authoritative_sites)
    all_urls: list[str] = []
    for q in queries:
        wrapped = f"({q}) ({site_filter})"
        print(f"[search] keyword: {q}")
        print(f"[search] site_filter: {site_filter}")
        results = await searxng_search(client, wrapped, num=per_query)
        for r in results:
            url = r.get("url")
            if url:
                all_urls.append(url)
    seen_u: set[str] = set()
    urls: list[str] = []
    for u in all_urls:
        if u not in seen_u:
            seen_u.add(u)
            urls.append(u)
    urls = urls[:cap_pages]

    all_texts: list[str] = []
    docs_per_phrase: dict[str, int] = {}
    for u in urls:
        html = await fetch_page(client, u)
        if not html:
            continue
        texts = extract_headings_and_title(html)
        all_texts.extend(texts)
        for c in set(candidate_phrases_from_texts(texts)):
            docs_per_phrase[c] = docs_per_phrase.get(c, 0) + 1

    if not all_texts:
        return []

    all_cands = candidate_phrases_from_texts(all_texts)
    scored = score_candidates(all_cands, docs_per_phrase)
    return [c for c, _ in scored]


def build_query_with_sites(keyword: str) -> str:
    kw = normalize_keyword(keyword)
    site_filter = " OR ".join(f"site:{d}" for d in authoritative_sites)
    return f"({kw}) ({site_filter})"


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
            for piece in chunk_text(summary, max_tokens=650, overlap=0):
                decorated = (
                    f"{query.upper()} — {title} — {url}\n"
                    f"PUBLISHED: {published_at or 'unknown'}\n\n"
                    f"{piece}"
                )
                if tokenish_len(decorated) <= EMBED_MAX_TOKENS:
                    await insert_embedding_logic([decorated])
                else:
                    # If still too large, split further and insert each
                    subchunks = chunk_text(
                        decorated, max_tokens=EMBED_MAX_TOKENS, overlap=0
                    )
                    for sub in subchunks:
                        if tokenish_len(sub) <= EMBED_MAX_TOKENS:
                            await insert_embedding_logic([sub])
    else:
        for i, chunk in enumerate(chunks):
            decorated = (
                f"{query.upper()} — {title} — {url}\n"
                f"PUBLISHED: {published_at or 'unknown'}\n\n"
                f"{chunk}"
            )
            if tokenish_len(decorated) <= EMBED_MAX_TOKENS:
                await insert_embedding_logic([decorated])
            else:
                # If still too large, split further and insert each
                subchunks = chunk_text(
                    decorated, max_tokens=EMBED_MAX_TOKENS, overlap=0
                )
                for sub in subchunks:
                    if tokenish_len(sub) <= EMBED_MAX_TOKENS:
                        await insert_embedding_logic([sub])

    print(f"[indexed] {url} ({len(chunks)} chunks)")


# ===============================
# Main
# ===============================
async def main():
    print("Running search…")
    try:
        seen = load_seen_keywords()
        pending_keyword: str | None = None
        async with httpx.AsyncClient(
            timeout=TIMEOUT, headers=HEADERS, follow_redirects=True
        ) as client:
            while True:
                # Phase 1: choose seed keyword
                if pending_keyword:
                    keyword = pending_keyword
                    pending_keyword = None
                else:
                    # discovery-first
                    year = time.gmtime().tm_year
                    candidates = await discover_keyword(
                        client, year, per_query=4, cap_pages=24
                    )
                    keyword = ""
                    for cand in candidates:
                        norm = normalize_keyword(cand)
                        if norm and norm not in seen:
                            keyword = norm
                            break
                    if not keyword:
                        session_id = str(uuid.uuid4())
                        raw_keyword = await ai_chat(client, CONTEXT, PROMPT, session_id)
                        keyword = normalize_keyword(raw_keyword)

                if not keyword:
                    print("[keyword] empty; sleeping…")
                    await asyncio.sleep(10.0)
                    continue

                print(f"[keyword] {keyword}")
                seen.add(keyword)
                save_seen_keyword(keyword)

                # Phase 2: targeted scrape using site filters
                query = build_site_filtered_query(keyword)
                results = await searxng_search(client, query, num=5)
                print(f"[searxng] {len(results)} results")

                scraped_urls: list[str] = []
                for r in results:
                    url = r.get("url", "")
                    title = r.get("title", "")
                    if not url:
                        continue
                    scraped_urls.append(url)
                    print(f"==> {title} {url}")
                    await process_url(client, url, keyword)
                    await asyncio.sleep(2.0)

                # Phase 3: ask AI for the next keyword based on scraped content
                if AI_NEXT_KEYWORD_FROM_RESULTS and scraped_urls:
                    try:
                        next_kw = await propose_next_keyword(client, scraped_urls, seen)
                        if next_kw and next_kw not in seen:
                            print(f"[next] proposed next keyword: {next_kw}")
                            pending_keyword = next_kw
                            # note: do not add to seen yet; accept it next loop when we actually use it
                    except Exception as e:
                        print(f"[next] propose_next_keyword error: {e}")

                await asyncio.sleep(15.0)
                # Phase 1: discovery from authoritative sources for the current year
                year = time.gmtime().tm_year
                candidates = await discover_keyword(
                    client, year, per_query=4, cap_pages=24
                )

                # Pick the first unseen candidate as our keyword
                keyword = ""
                for cand in candidates:
                    norm = normalize_keyword(cand)
                    if norm and norm not in seen:
                        keyword = norm
                        break

                # Fallback: if discovery failed, ask the model once
                if not keyword:
                    session_id = str(uuid.uuid4())
                    raw_keyword = await ai_chat(client, CONTEXT, PROMPT, session_id)
                    keyword = normalize_keyword(raw_keyword)

                if not keyword:
                    print("[keyword] empty; sleeping…")
                    await asyncio.sleep(10.0)
                    continue

                print(f"[keyword] {keyword}")
                seen.add(keyword)
                save_seen_keyword(keyword)

                # Phase 2: targeted scrape using site filters
                query = build_site_filtered_query(keyword)
                results = await searxng_search(client, query, num=5)
                print(f"[searxng] {len(results)} results")

                for r in results:
                    url = r.get("url", "")
                    title = r.get("title", "")
                    if not url:
                        continue
                    print(f"==> {title} {url}")
                    await process_url(client, url, keyword)
                    await asyncio.sleep(2.0)

                await asyncio.sleep(15.0)

    except Exception as e:
        print(f"[error] {e}")
    finally:
        print("Search complete.")


if __name__ == "__main__":
    asyncio.run(main())
