import asyncio
import uuid
from httpx import AsyncClient, Timeout
from yapper import PiperSpeaker, PiperVoiceGB
from bs4 import BeautifulSoup

timeout = Timeout(300.0)
session_id = str(uuid.uuid4())
api_url = "http://127.0.0.1:8000/message"
context = (
    "You are a curious software developer wants to know all things."
    "Your job is to suggest interesting keyword searches. "
    "Reply ONLY in English language with a plain text keyword or phrase for searching, no sentences or explanations."
)
prompt = "Suggest a keyword search for today."


async def scrape_bing(keyword: str) -> list:
    """Scrape Bing search results for the given keyword."""
    url = f"https://www.bing.com/search?q={keyword}"
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "en-US,en;q=0.9",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Referer": "https://www.bing.com/",
    }
    async with AsyncClient(headers=headers, follow_redirects=True) as client:
        resp = await client.get(url)
        print(f"Scraping Bing for keyword: {keyword}")
        print(f"Response status: {resp.status_code}")
        soup = BeautifulSoup(resp.text, "html.parser")
        results = []
        for li in soup.select("li.b_algo"):
            title_tag = li.find("h2")
            link_tag = title_tag.find("a") if title_tag else None
            if title_tag and link_tag:
                title = title_tag.get_text(strip=True)
                link = link_tag.get("href")
                results.append({"title": title, "link": link})
        return results


async def scrape_duckduckgo(keyword: str) -> list:
    """Scrape DuckDuckGo search results for the given keyword."""
    url = f"https://duckduckgo.com/html/?q={keyword}"
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "en-US,en;q=0.9",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Referer": "https://duckduckgo.com/",
    }
    async with AsyncClient() as client:
        resp = await client.get(url, headers=headers)
        soup = BeautifulSoup(resp.text, "html.parser")
        print(f"Scraping DuckDuckGo for keyword: {keyword}")
        print(f"Response status: {resp.status_code}")
        results = []
        for a in soup.select(".result__a"):
            title = a.get_text(strip=True)
            link = a.get("href")
            results.append({"title": title, "link": link})
        return results

async def scrape_searxng(keyword: str) -> list:
    """Scrape DuckDuckGo search results for the given keyword."""
    url = f"http://localhost:8888/search?q={keyword}"
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "en-US,en;q=0.9",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Referer": "https://duckduckgo.com/",
    }
    async with AsyncClient() as client:
        resp = await client.get(url, headers=headers)
        soup = BeautifulSoup(resp.text, "html.parser")
        print(f"Scraping DuckDuckGo for keyword: {keyword}")
        print(f"Response status: {resp.status_code}")
        results = []
        for result in soup.select(".result"):
            a = result.find(".url_header")
            p = result.find(".content")

            title = a.get_text(strip=True) if a else ""
            link = a.get("href") if a else ""
            content = p.get_text(strip=True) if p else ""
            results.append({"title": title, "link": link, "content": content})
        return results

async def scrape_link(url: str) -> str:
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "en-US,en;q=0.9",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Referer": "https://duckduckgo.com/",
    }
    async with AsyncClient() as client:
        resp = await client.get(url, headers=headers)
        soup = BeautifulSoup(resp.text, "html.parser")
        print(f"Response status: {resp.status_code}")
        page_text = soup.get_text(separator="\n", strip=True)
        return page_text


async def api_search(client: AsyncClient, context, prompt, session_id):
    response = ""
    async with client.stream(
        "POST",
        f"{api_url}",
        json={
            "context": context,
            "text": prompt,
            "playAudio": False,
            "session_id": session_id,
            "stream": True,
        },
        headers={"Content-Type": "application/json"},
    ) as stream_response:
        async for chunk in stream_response.aiter_text():
            print(chunk, end="", flush=True)
            response += chunk

    return response


async def main():
    print("Running search...")
    try:
        while True:
            current_search = ""

            async with AsyncClient(timeout=timeout) as client:
                current_search = await api_search(client, context, prompt, session_id)
                print(f"\nCurrent search result: {current_search}")

                speaker = PiperSpeaker(voice=PiperVoiceGB.CORI)
                speaker.say(f"Searching for... {current_search}")

                # Use the search result to search internet with web scraping
                results_searxng = await scrape_searxng(current_search)
                # results_bing = await scrape_bing(current_search)

                print("Top results from SearxNG and Bing:\n")
                # results = results_searxng + results_bing
                results = results_searxng

                for result in results:
                    print(f"Title: {result['title']}")
                    print(f"Link: {result['link']}")
                    print(f"Content: {result['content']}")

                    results = await scrape_link(result["link"])
                    print(f"Content: {results[:200]}...")

                    print()

                await asyncio.sleep(5)

    except Exception as e:
        print(f"Error occurred: {e}")
    finally:
        print("Search complete.")


asyncio.run(main())
