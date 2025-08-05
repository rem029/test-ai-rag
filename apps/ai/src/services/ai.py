import asyncio
import os
from typing import Optional
import uuid
from ollama import AsyncClient
import pyttsx3
from services.db import get_embeddings_from_db, get_recent_messages, save_message
from utils.constants import MODELS

client = AsyncClient(host='http://localhost:11434')

async def embed_text(text: str) -> dict:
    """
    Generate embedding for the given text using nomic-embed-text with Ollama.
    """
    # Use Ollama's embedding API to generate embeddings    
    try:
        
        response = await client.embeddings(model=MODELS['embed'], prompt=text)
        return {"embedding": response["embedding"]}
    except Exception as e:
        print(f"Error generating embedding: {e}")
        # Try alternative model names
        try:
            response = await client.embeddings(model="nomic-embed-text:latest", prompt=text)
            return {"embedding": response["embedding"]}
        except Exception as e2:
            print(f"Error with latest tag: {e2}")
            raise e2

async def text_to_speech(text: str) -> str:
    """
    Generate TTS audio for the given text using pyttsx3 (offline).
    Returns the path to the generated audio file.
    """
    try:
        # Create output directory if it doesn't exist
        current_dir = os.getcwd()
        output_dir = os.path.join(current_dir, "tmp", "audio_output")
        os.makedirs(output_dir, exist_ok=True)
        
        # Generate a unique filename
        filename = f"audio_{uuid.uuid4().hex[:8]}.wav"
        filepath = os.path.join(output_dir, filename)
        
        def _generate_speech():
            engine = None
            try:
                engine = pyttsx3.init()
                # Optional: Configure voice properties
                engine.setProperty('rate', 120)    # Speed of speech
                engine.setProperty('volume', 0.9)  # Volume level (0.0 to 1.0)
                
                # Save to file
                engine.save_to_file(text, filepath)
                engine.runAndWait()
                
                # Properly stop the engine
                engine.stop()
                
            except Exception as e:
                print(f"Error in TTS engine: {e}")
                raise e
            finally:
                # Clean up the engine
                if engine:
                    try:
                        engine.stop()
                    except:
                        pass
                    del engine
        
        # Run the blocking operation in a thread pool
        await asyncio.to_thread(_generate_speech)
        
        print(f"Audio file generated: {filepath}")
        return filepath
    except Exception as e:
        print(f"Error generating TTS: {e}")
        raise e

async def analyze_image(image_data: str) -> str:
    """
    Analyze the given image and return a description.
    """
    # Placeholder logic for vision analysis
    return await client.chat(
            model=MODELS['vision'],
            images=[image_data],
            stream=True,
        )

async def stream_response_logic(session_id: str,text: str, stream: bool = True, context: Optional[str] = None,image: Optional[str] = None, audioResponse: bool = False):
    """
    Stream response from Ollama API using the gemma3:1b-it-q4_K_M model.
    The text is sent as input, and the embedding is sent as context.
    Defaults context to null if no embedding is found.
    """
    if audioResponse:
        stream = False
    # Embedding and response generation logic
    embedding = await embed_text(text)
    db_embeddings = await get_embeddings_from_db(embedding)

    # Convert embedding to a string representation for context
    embedding_context = "\n".join([f"- {item['message']}" for item in db_embeddings])

    if context:
        system_prompt = f"{context}\n"
        system_prompt += "Keep answer short and straightforward. Base your answer on the context provided. if there is no context, use the default context.\n"
        system_prompt += f"\nContext:\n{embedding_context}"
    else:
        system_prompt = (
            "You are Mary Test's official support agent.\n\n"
            "Behavior Rules:\n"
            "- If greeted politely (e.g., 'hello', 'hi', 'good morning'), respond with:\n"
            '  "Hello, I am Mary Test\'s official support agent. How can I assist you today?"\n'
            "- If the question is NOT related to Mary Test, respond with:\n"
            '  "I\'m sorry, I can only answer questions about Mary Test."\n\n'
            "Topic Restriction:\n"
            "You are only allowed to answer questions directly related to the company Mary Test. "
            "Do not respond to general tech queries, personal questions, or anything outside the company's scope.\n\n"
            "You may only use the facts below to answer questions. Do not fabricate or assume details.\n\n"
            f"{embedding_context}\n"
            "Strictly respond using information from the list above."
        )

    messages = [
        {"role": "system", "content": system_prompt},
    ]

    print("System messages:\n===\n", system_prompt, "\n===")

    recent_messages = await get_recent_messages(limit=5, session_id=session_id)  # Fetch the last 5 messages
    recent_messages.reverse()  # Reverse the list to maintain chronological order
    print("Last messages:\n===")
    for msg in recent_messages:
        print(msg["role"], ":", msg["message"])
        messages.append({"role": msg["role"], "content": msg["message"]})
    print("===")

    model = MODELS['text']
    if image:
        model = MODELS['vision']
        messages.append({"role": "user", "content": text, "images": [image]})
    else:
        messages.append({"role": "user", "content": text})

    await save_message(text, "user", embedding, session_id)

    # insert here thinking action to be made decided by gemma3    
    # if user asks for a summary, summarize the last 6 messages
    # if user ask to remember you should embed the message and save it
    # model should also decide wether to save the message sessionId wise or available to all

    print(f"Model: {model}\n")
    print("Response:\n")
    if stream:
        text_response = ""
        async for part in await client.chat(
            model=model,
            messages=messages,
            stream=True,
        ):
            content = part["message"]["content"]
            if part.done:
                embedding = await embed_text(text_response)
                await save_message(text_response, "assistant", embedding, session_id)
            for char in content:  # Yield character by character
                text_response += char
                print(char, end="", flush=True)
                # Save the message content directly
                yield char
    else:
        response = await client.chat(
            model=model,
            messages=messages,
            stream=False,
        )
        content = response["message"]["content"]
        embedding = await embed_text(content)
        await save_message(content, "assistant", embedding, session_id)
        
        # If audio response is requested, convert to speech
        if audioResponse:
            audio_file = await text_to_speech(content)
            # First yield the text content
            for char in content:
                print(char, end="", flush=True)
                yield char
            # You might want to yield the audio file path or handle it differently
            yield f"\nAudio generated: {audio_file}"
        else:
            for char in content:  # Yield character by character
                print(char, end="", flush=True)
                yield char