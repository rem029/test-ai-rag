from typing import Optional
from services.ai import embed_text, analyze_image, text_to_speech, chat_with_model
from services.db import get_embeddings_from_db, save_message, get_recent_messages


async def handle_message_logic(request_data: dict):
    """
    Handle message processing logic.
    """
    text = request_data.get("text")
    image = request_data.get("image")
    audio_response = request_data.get("audioResponse", False)
    stream = request_data.get("stream", True)
    context = request_data.get("context")
    
    if image:
        # Vision logic
        description = await analyze_image(image)
        return {"description": description}

    if text:
        response_stream = stream_response_logic(text, stream, context)
        return response_stream

    if audio_response:
        # Text-to-speech logic
        audio_path = await text_to_speech(text)
        return {"audio_path": audio_path}

    return {"error": "Invalid request"}


async def stream_response_logic(text: str, stream: bool = True, context: Optional[str] = None):
    """
    Stream response from Ollama API using the gemma3:1b-it-q4_K_M model.
    The text is sent as input, and the embedding is sent as context.
    Defaults context to null if no embedding is found.
    """
    # Embedding and response generation logic
    embedding = await embed_text(text)
    db_embeddings = await get_embeddings_from_db(embedding)

    # Convert embedding to a string representation for context
    embedding_context = "\n".join([f"- {item['message']}" for item in db_embeddings])

    if context:
        system_prompt = f"{context}\n"
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

    recent_messages = await get_recent_messages(limit=5)  # Fetch the last 5 messages
    recent_messages.reverse()  # Reverse the list to maintain chronological order
    print("Last messages:\n===")
    for msg in recent_messages:
        print(msg["role"], ":", msg["message"])
        messages.append({"role": msg["role"], "content": msg["message"]})
    print("===")

    messages.append({"role": "user", "content": text})
    await save_message(text, "user", embedding)

    print("Response:\n")
    if stream:
        text_response = ""
        async for part in await chat_with_model(messages, stream=True):
            content = part["message"]["content"]
            if part.done:
                embedding = await embed_text(text_response)
                await save_message(text_response, "assistant", embedding)
            for char in content:  # Yield character by character
                text_response += char
                print(char, end="", flush=True)
                # Save the message content directly
                yield char
    else:
        response = await chat_with_model(messages, stream=False)
        content = response["message"]["content"]
        embedding = await embed_text(content)
        await save_message(content, "assistant", embedding)
        for char in content:  # Yield character by character
            print(char, end="", flush=True)
            yield char