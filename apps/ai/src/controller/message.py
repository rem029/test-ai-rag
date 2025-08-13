from typing import Optional
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from services.ai import stream_response_logic, initialize_session_logging, end_session_logging
from services.logger import get_logger
import uuid


class MessageRequest(BaseModel):
    session_id: Optional[str]
    text: Optional[str] = None
    image: Optional[str] = None  # Base64 encoded image
    audioResponse: Optional[bool] = False
    stream: Optional[bool] = False
    messages: Optional[list] = []  # Store conversation history
    context: Optional[str] = None  # Optional context to replace system_prompt
    playAudio: Optional[bool] = True


async def handle_message_logic(request: MessageRequest):
    """
    Handle message processing logic.
    """
    logger = get_logger()
    
    # Generate session_id if not provided
    if not request.session_id:
        request.session_id = str(uuid.uuid4())
        logger.log_and_print(f"🆔 [cyan]Generated new session ID:[/cyan] [blue]{request.session_id}[/blue]")
    
    # Initialize session logging if this is the first request for this session
    if logger.session_logger is None:
        initialize_session_logging(request.session_id)
        logger.log_and_print(f"🚀 [green]Session started:[/green] [blue]{request.session_id[:8]}...[/blue]")
    
    if request.text:
        try:
            response_stream = stream_response_logic(
                request.session_id, 
                request.text, 
                request.stream, 
                request.context, 
                request.image, 
                request.audioResponse,
                request.playAudio
            )
            return StreamingResponse(response_stream, media_type="text/plain")
        except Exception as e:
            logger.log_error(f"Error in message handling: {str(e)}", "MESSAGE_ERROR")
            return {"error": f"Failed to process message: {str(e)}"}

    if request.audioResponse and not request.text:
        logger.log_and_print("⚠️ [yellow]Audio response requested without text input[/yellow]", log_level="warning")
        return {"message": "Audio response requires text input"}

    logger.log_error("No valid input provided in request", "INVALID_REQUEST")
    return {"error": "Invalid request - no text provided"}


