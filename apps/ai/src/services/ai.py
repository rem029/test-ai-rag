from typing import Optional
from services.embed import embed_text
from services.audio import text_to_speech_yapper
from services.db import get_embeddings_from_db, get_recent_messages, save_message
from services.clients import model_main


async def analyze_image(image_data: str) -> str:
    """
    Analyze the given image and return a description.
    """
    # Placeholder logic for vision analysis
    return await client.chat(
        model=MODELS["vision"],
        images=[image_data],
        stream=True,
    )


async def stream_response_logic(
    session_id: str,
    text: str,
    stream: bool = True,
    context: Optional[str] = None,
    image_base64: Optional[str] = None,
    audioResponse: bool = False,
):
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
        system_prompt = "Keep answer short and straightforward. Base your answer on the context provided. if there is no context, use the default context.\n"
        system_prompt += f"{context}\n"
        system_prompt += "You may use the facts below to answer questions. Do not fabricate or assume details.\n\n"
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

    recent_messages = await get_recent_messages(
        limit=5, session_id=session_id
    )  # Fetch the last 5 messages
    recent_messages.reverse()  # Reverse the list to maintain chronological order

    print("Last messages:\n===")
    for msg in recent_messages:
        print(msg["role"], ":", msg["message"])
        messages.append({"role": msg["role"], "content": msg["message"]})
        print("===")

    messages = [
        {"role": "system", "content": system_prompt},
    ]
    print("System messages:\n===\n", system_prompt, "\n===")

    if image_base64:
        messages.append(
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": text},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{image_base64}"},
                    },
                ],
            }
        )
    else:
        messages.append({"role": "user", "content": text})

    await save_message(text, "user", embedding, session_id)

    # ---------------------------------------------------------
    #
    # insert here thinking action to be made decided by gemma3
    # if user asks for a summary, summarize the last 6 messages
    # if user ask to remember you should embed the message and save it
    # model should also decide wether to save the message sessionId wise or available to all
    #
    # ---------------------------------------------------------

    print("Response:\n")
    if stream:
        text_response = ""
        # Use OpenAI's async streaming API
        stream_resp = await model_main.chat.completions.create(
            model="",
            messages=messages,
            stream=True,
        )
        async for part in stream_resp:
            content = part.choices[0].delta.content or ""

            if getattr(part, "done", False):
                if hasattr(part, "usage"):
                    print(f"Tokens used: {part.usage}")

                embedding = await embed_text(text_response)
                await save_message(text_response, "assistant", embedding, session_id)
            for char in content:
                text_response += char
                print(char, end="", flush=True)
                yield char
        if audioResponse:
            audio_file = await text_to_speech_yapper(text_response)
            yield f"\n[AUDIO_FILE:{audio_file}]"
    else:
        response = await model_main.chat.completions.create(
            model="",
            messages=messages,
            stream=False,
        )
        content = response.choices[0].message.content
        embedding = await embed_text(content)
        await save_message(content, "assistant", embedding, session_id)

        if audioResponse:
            audio_file = await text_to_speech_yapper(content)
            for char in content:
                print(char, end="", flush=True)
                yield char
            yield f"\nAudio generated: {audio_file}"
        else:
            for char in content:
                print(char, end="", flush=True)
                yield char
