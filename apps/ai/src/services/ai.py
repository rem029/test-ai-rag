import os
from typing import Optional
from services.embed import embed_text
from services.audio import play_audio, text_to_speech_yapper
from services.db import get_embeddings_from_db, get_recent_messages, save_message
from services.clients import model_main
from services.logger import get_logger



def initialize_session_logging(session_id: str) -> str:
    """
    Initialize session logging for a given session ID.
    
    Args:
        session_id: The unique session identifier
        
    Returns:
        The path to the created log file
    """
    logger = get_logger()
    log_file_path = logger.setup_session_logging(session_id)
    logger.log_and_print(f"📄 [green]Session logging initialized:[/green] [blue]{log_file_path}[/blue]")
    return log_file_path


def end_session_logging(session_id: str, reason: str = "Normal termination"):
    """
    End session logging for a given session ID.
    
    Args:
        session_id: The unique session identifier
        reason: Reason for session termination
    """
    logger = get_logger()
    logger.log_session_end(session_id, reason)
    logger.log_and_print(f"📄 [blue]Session {session_id[:8]} ended:[/blue] [yellow]{reason}[/yellow]")


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
    # Get logger instance
    logger = get_logger()
    
    try:
        # Setup session logging if not already done
        if logger.session_logger is None:
            log_file_path = logger.setup_session_logging(session_id)
            logger.log_and_print(f"📄 [green]Session logging initialized:[/green] [blue]{log_file_path}[/blue]")
        
        # Log user input
        image_info = "Image attached" if image_base64 else "No image"
        logger.log_user_input(session_id, text, bool(image_base64), image_info)
        
        # Embedding and response generation logic
        embedding = await embed_text(text)
        db_embeddings = await get_embeddings_from_db(embedding)
        
        # Log embedding context
        logger.log_embedding_context(len(db_embeddings))

        # Convert embedding to a string representation for context
        embedding_context = "\n".join([f"- {item['message']}" for item in db_embeddings])

        if context:
            system_prompt = f"{context}\n"
            system_prompt += f"{embedding_context}"
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
        
        # Log system prompt
        logger.log_system_prompt(system_prompt)

        messages = [
            {"role": "system", "content": system_prompt},
        ]

        recent_messages = await get_recent_messages(
            limit=30, session_id=session_id
        )  # Fetch the last 30 messages
        recent_messages.reverse()  # Reverse the list to maintain chronological order

        # Log recent messages instead of printing
        logger.log_recent_messages(recent_messages)

        for msg in recent_messages:
            messages.append({"role": msg["role"], "content": msg["message"]})

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

        # Log AI response start
        logger.log_ai_response_start()
        logger.log_and_print("🤖 [bold green]AI Response:[/bold green]")
        
        if stream:
            text_response = ""
            audio_file_path = None
            # Use OpenAI's async streaming API
            stream_resp = await model_main.chat.completions.create(
                model="",
                messages=messages,
                stream=True,
                temperature=0.1,
            )
            async for part in stream_resp:
                content = part.choices[0].delta.content or ""
                finish_reason = part.choices[0].finish_reason or None

                if finish_reason == "stop":
                    if hasattr(part, "usage"):
                        token_info = f"Tokens used: {getattr(part.usage, 'total_tokens', 0)}"
                        logger.log_and_print(f"\n📊 [cyan]{token_info}[/cyan]")
                for char in content:
                    text_response += char
                    print(char, end="", flush=True)
                    yield char
            
            embedding = await embed_text(text_response)
            await save_message(text_response, "assistant", embedding, session_id)
            
            if audioResponse:
                try:
                    audio_file_path = await text_to_speech_yapper(text_response)
                    if audio_file_path and os.path.exists(audio_file_path):
                        play_audio(audio_file_path)
                        yield f"\n[AUDIO_FILE:{audio_file_path}]"
                except Exception as e:
                    logger.log_error(f"Audio generation failed: {str(e)}", "AUDIO_ERROR")
            
            # Log the complete response
            logger.log_ai_response(text_response, audio_file_path)
            
        else:
            response = await model_main.chat.completions.create(
                model="",
                messages=messages,
                stream=False,
                temperature=0.1,
            )
            content = response.choices[0].message.content
            embedding = await embed_text(content)
            await save_message(content, "assistant", embedding, session_id)

            audio_file_path = None
            if audioResponse:
                try:
                    audio_file_path = await text_to_speech_yapper(content)
                except Exception as e:
                    logger.log_error(f"Audio generation failed: {str(e)}", "AUDIO_ERROR")
                
            for char in content:
                print(char, end="", flush=True)
                yield char
                
            if audio_file_path and os.path.exists(audio_file_path):
                try:
                    play_audio(audio_file_path)
                    yield f"\n[AUDIO_FILE:{audio_file_path}]"
                except Exception as e:
                    logger.log_error(f"Audio playback failed: {str(e)}", "AUDIO_ERROR")
            
            # Log the complete response
            logger.log_ai_response(content, audio_file_path)
            
    except Exception as e:
        logger.log_error(f"Error in stream_response_logic: {str(e)}", "STREAM_ERROR")
        error_message = f"I apologize, but I encountered an error while processing your request: {str(e)}"
        for char in error_message:
            yield char
