import asyncio
import uuid
from httpx import AsyncClient, Timeout
from yapper import PiperSpeaker, PiperVoiceGB
from bs4 import BeautifulSoup

from controller.embed import insert_embedding_logic
from services.embed import chunk_text

timeout = Timeout(600.0)
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
        print(f"Scraping SearxNG for keyword: {keyword}")
        print(f"Response status: {resp.status_code}")
        results = []
        for result in soup.select(".result"):
            a = result.select_one(".url_header")
            h3 = result.select_one("h3")
            p = result.select_one(".content")

            title = h3.get_text(strip=True) if h3 else ""
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


async def ai_chat(client: AsyncClient, context, prompt, session_id):
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
        timeout=timeout,
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
            session_id = str(uuid.uuid4())
            async with AsyncClient(timeout=timeout) as client:
                current_search = await ai_chat(client, context, prompt, session_id)
                print(f"\nCurrent search result: {current_search}")

                # speaker = PiperSpeaker(voice=PiperVoiceGB.CORI)
                # speaker.say(f"Searching for... {current_search}")

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
                    print(f"Content: {results[:1000]}...")

                    if results:

                        chunks_results = chunk_text(results.strip(), 768)

                        for chunks_result in chunks_results:
                            session_summarizer_id = str(uuid.uuid4())
                            result_summary = await ai_chat(
                                client,
                                "You are my assistant preparing data for retrieval-augmented generation (RAG). Extract and summarize only the most important facts and information from the provided content. Make your summary concise and factual, strictly less than 768 characters, and use plain text only.",
                                f"Analyze and summarize the following for RAG:\n{chunks_result.strip()}",
                                session_summarizer_id,
                            )
                            print("Summarized content:\n=====\n", result_summary[:1000])
                            chunks_summary = chunk_text(result_summary, 700)
                            for chunk in chunks_summary:
                                print("Chunk: ", chunk)
                                print("Chunk.length: ", len(chunk))
                                await insert_embedding_logic(
                                    [f"{current_search.upper()} - {chunk}"]
                                )

                        print("Summarized ends here:\n=====\n")

                        # speaker = PiperSpeaker(voice=PiperVoiceGB.ALAN)
                        # speaker.say(f"Summarized content for {result_summary}")

                    await asyncio.sleep(15)  # Simulate processing time

    except Exception as e:
        print(f"Error occurred: {e}")
    finally:
        print("Search complete.")


asyncio.run(main())
