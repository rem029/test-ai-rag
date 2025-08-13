import asyncio
import subprocess
import uuid
import httpx
from yapper import PiperSpeaker, PiperVoiceGB


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


async def debate(topic, rounds=10):
    """
    Facilitate a debate between two AI instances on a given topic.
    """
    # Start two AI instances on different ports
    ai1_port = 8081
    ai2_port = 8082
    ai1_session_id = str(uuid.uuid4())
    ai2_session_id = str(uuid.uuid4())

    # ai1_process = await run_ai_instance(ai1_port)
    # ai2_process = await run_ai_instance(ai2_port)

    # Wait for servers to start
    await asyncio.sleep(2)

    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(60.0)) as client:
            previous_response = ""
            
            for round_num in range(1, rounds + 1):
                print(f"\n{'='*50}")
                print(f"ROUND {round_num}")
                print(f"{'='*50}")
                
                # AI 1's turn
                print("\nAI 1 is thinking...")
                print("A1: ")
                
                if round_num == 1:
                    # First round - AI 1 initiates
                    prompt = f"What are your thoughts on {topic}?"
                    context = f"You are AI 1 in a debate on the topic: {topic}.\nKeep your answers short and straightforward.\nThis is round 1. Present your initial position."
                else:
                    # Subsequent rounds - AI 1 responds to AI 2
                    prompt = f"{previous_response}"
                    context = f"You are AI 1 in a debate on the topic: {topic}.\nKeep your answers short and straightforward.\nThis is round {round_num}. Respond to AI 2's argument and strengthen your position."

                ai1_response = ""
                async with client.stream(
                    "POST",
                    f"http://127.0.0.1:{ai1_port}/message",
                    json={"text": f"AI 1: {prompt}", "context": context, "playAudio": False, "session_id": ai1_session_id},
                    headers = {"Content-Type": "application/json"}
                ) as response_ai1:
                    async for chunk in response_ai1.aiter_text():
                        print(chunk, end="", flush=True)
                        ai1_response += chunk

                # Initialize BaseSpeaker
                speaker = PiperSpeaker(voice=PiperVoiceGB.CORI)
                # Generate audio file
                speaker.say(ai1_response)

                # AI 2's turn
                print("\n\nAI 2 is thinking...")
                print("A2: ")
                
                if round_num == rounds:
                    context = f"You are AI 2 in a debate on the topic: {topic}.\nKeep your answers short and straightforward.\nThis is the final round {round_num}. Give your final rebuttal and closing argument."
                else:
                    context = f"You are AI 2 in a debate on the topic: {topic}.\nKeep your answers short and straightforward.\nThis is round {round_num}. Counter AI 1's argument and present your position."
                
                ai2_response = ""
                async with client.stream(
                    "POST",
                    f"http://127.0.0.1:{ai2_port}/message",
                    json={"text": f"AI 2: {ai1_response}" , "context": context,"playAudio": False,"session_id": ai1_session_id},
                    headers = {"Content-Type": "application/json"}
                ) as response_ai2:
                    async for chunk in response_ai2.aiter_text():
                        print(chunk, end="", flush=True)
                        ai2_response += chunk

                # Initialize BaseSpeaker
                speaker = PiperSpeaker(voice=PiperVoiceGB.JENNY_DIOCO)
                # Generate audio file
                speaker.say(ai2_response)

                # Set up for next round
                previous_response = ai2_response

            print(f"\n\n{'='*50}")
            print("DEBATE CONCLUDED")
            print(f"{'='*50}")

    finally:
        print("\nDebate finished.")
        # Terminate both AI instances
        # ai1_process.terminate()
        # ai2_process.terminate()


if __name__ == "__main__":
    topic = input("Enter a topic for the debate: ")
    rounds = input("Enter number of rounds (default 10): ")
    rounds = int(rounds) if rounds.strip() else 10
    asyncio.run(debate(topic, rounds))
