import asyncio
import subprocess
import httpx


async def run_ai_instance(port):
    """
    Run an instance of the AI server on the specified port.
    """
    process = subprocess.Popen(
        ["uvicorn", "main:app", "--host", "127.0.0.1", "--port", str(port)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return process


async def debate(topic):
    """
    Facilitate a debate between two AI instances on a given topic.
    """
    # Start two AI instances on different ports
    ai1_port = 8000
    ai2_port = 8001

    # ai1_process = await run_ai_instance(ai1_port)
    # ai2_process = await run_ai_instance(ai2_port)

    # Wait for servers to start
    await asyncio.sleep(5)

    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(30.0)) as client:
            # AI 1 initiates the debate
            async with client.stream(
                "POST",
                f"http://127.0.0.1:{ai1_port}/message",
                json={"text": f"What are your thoughts on {topic}?"},
            ) as response_ai1:
                async for chunk in response_ai1.aiter_text():
                    print("AI 1:", chunk, end="", flush=True)

            # AI 2 responds
            async with client.stream(
                "POST",
                f"http://127.0.0.1:{ai2_port}/message",
                json={"text": chunk},
            ) as response_ai2:
                async for chunk in response_ai2.aiter_text():
                    print("AI 2:", chunk, end="", flush=True)

    finally:
        print("Debate finished.")
        # Terminate both AI instances
        # ai1_process.terminate()
        # ai2_process.terminate()


if __name__ == "__main__":
    topic = input("Enter a topic for the debate: ")
    asyncio.run(debate(topic))
