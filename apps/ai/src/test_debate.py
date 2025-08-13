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


async def debate(topic = "Aliens", rounds=10, a1_title = "Alien Believer", a2_title = "Non Alien Believer"):
    """
    Facilitate a debate between two AI instances on a given topic.
    """
    # Start two AI instances on different ports
    ai1_port = 8081
    ai2_port = 8082
    ai3_port = 8083
    ai1_session_id = str(uuid.uuid4())
    ai2_session_id = str(uuid.uuid4())

    # ai1_process = await run_ai_instance(ai1_port)
    # ai2_process = await run_ai_instance(ai2_port)

    # Wait for servers to start
    await asyncio.sleep(2)

    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(300.0)) as client:
            responses = ''
            previous_response = ""
            
            for round_num in range(1, rounds + 1):
                print(f"\n{'='*50}")
                print(f"ROUND {round_num}")
                print(f"{'='*50}")
                
                # AI 1's turn
                print("\nAI 1 is thinking...")
                print(f"AI 1: ({a1_title}) ")
                
                if round_num == 1:
                    # First round - AI 1 initiates
                    prompt = (
                                f"What are your thoughts on {topic}? AI 1 is {a1_title}. AI 2 is {a2_title}. "
                                "Reply in plain text only. Do not use any symbols, markdown, or formatting—just a simple string."
                            )
                    context = f"You are AI 1 {a1_title} in a debate on the topic: {topic}.\nKeep your answers short and straightforward.\nThis is round 1. Present your initial position."
                else:
                    # Subsequent rounds - AI 1 responds to AI 2
                    prompt = (
                                f"{previous_response}"
                                "Reply in plain text only. Do not use any symbols, markdown, or formatting—just a simple string."
                              )
                    context = f"You are AI 1 {a1_title} in a debate on the topic: {topic}.\nKeep your answers short and straightforward.\nThis is round {round_num}. Respond to AI 2's {a2_title} argument and strengthen your position."

                ai1_response = ""
                async with client.stream(
                    "POST",
                    f"http://127.0.0.1:{ai1_port}/message",
                    json={"text": f"AI 1: {prompt}", "context": context, "playAudio": False, "session_id": ai1_session_id, "stream": True},
                    headers = {"Content-Type": "application/json"}
                ) as response_ai1:
                    async for chunk in response_ai1.aiter_text():
                        print(chunk, end="", flush=True)
                        ai1_response += chunk
                
                responses += f"AI 1 {a1_title}: {ai1_response}"
                # Initialize BaseSpeaker
                speaker = PiperSpeaker(voice=PiperVoiceGB.CORI)
                # Generate audio file
                speaker.say(ai1_response)

                # AI 2's turn
                print("\n\nAI 2 is thinking...")
                print(f"AI 2: ({a2_title}) ")
                
                if round_num == rounds:
                    context = f"You are AI 2 {a2_title} in a debate on the topic: {topic}.\nKeep your answers short and straightforward.\nThis is the final round {round_num}. Give your final rebuttal and closing argument. Reply in plain text only."
                else:
                    context = f"You are AI 2 {a2_title} in a debate on the topic: {topic}.\nKeep your answers short and straightforward.\nThis is round {round_num}. Counter AI 1's {a1_title} argument and present your position. Reply in plain text only."
                
                ai2_response = ""
                async with client.stream(
                    "POST",
                    f"http://127.0.0.1:{ai2_port}/message",
                    json={"text": f"AI 2: {ai1_response}" , "context": context,"playAudio": False,"session_id": ai2_session_id, "stream": True},
                    headers = {"Content-Type": "application/json"}
                ) as response_ai2:
                    async for chunk in response_ai2.aiter_text():
                        print(chunk, end="", flush=True)
                        ai2_response += chunk

                responses += f"AI 2 {a2_title}: {ai2_response}"
                # Initialize BaseSpeaker
                speaker = PiperSpeaker(voice=PiperVoiceGB.JENNY_DIOCO)
                # Generate audio file
                speaker.say(ai2_response)

                # Set up for next round
                previous_response = ai2_response

            print(f"\n\n{'='*50}")
            print("DEBATE CONCLUDED")
            print(f"{'='*50}")
            
            ai3_session_id = str(uuid.uuid4())
            
            print(f"Judge: ")
            
            judge_response = ""
            async with client.stream(
                    "POST",
                    f"http://127.0.0.1:{ai3_port}/message",
                    json={
                            "text": f"Summarize and tell me who won the debate here are the responses:\n{responses}",
                            "context": (f"Topic is discussed is about {topic}"
                                        "you are the judge of their responses."
                                        "Reply in plain text only. Do not use any symbols, markdown, or formatting—just a simple string."),
                            "playAudio": False,
                            "session_id": ai3_session_id,
                            "stream": True
                        },
                    headers = {"Content-Type": "application/json"}
                ) as response_ai3:
                    async for chunk in response_ai3.aiter_text():
                        print(chunk, end="", flush=True)
                        judge_response += chunk

            speaker = PiperSpeaker(voice=PiperVoiceGB.ALAN)
            # Generate audio file
            speaker.say(judge_response)
    finally:
        print("\nDebate finished.")
        # Terminate both AI instances
        # ai1_process.terminate()
        # ai2_process.terminate()


if __name__ == "__main__":
    topic = input("Enter a topic for the debate: (Aliens): ")
    a1_title = input("Enter title for AI 1 (Alien Believer): ")
    a2_title = input("Enter title for AI 2 (Non Alien Believer): ")
    
    if not topic.strip():
        topic = "Aliens"
        
    if not a1_title.strip():
        topic = "Alien Believer"
        
    if not a2_title.strip():
        topic = "Non Alien Believer"
    
    rounds = input("Enter number of rounds (default 10): ")
    rounds = int(rounds) if rounds.strip() else 10
    asyncio.run(debate(topic, rounds,a1_title, a2_title))
