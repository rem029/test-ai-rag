from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional
from controller.message import handle_message_logic, stream_response_logic

router = APIRouter()


class MessageRequest(BaseModel):
    text: Optional[str] = None
    image: Optional[str] = None  # Base64 encoded image
    audioResponse: Optional[bool] = False
    stream: Optional[bool] = False
    messages: Optional[list] = []  # Store conversation history
    context: Optional[str] = None  # Optional context to replace system_prompt


@router.post("/message")
async def handle_message(request: MessageRequest):
    """
    Unified endpoint to handle text, image, and audio requests.
    """
    request_data = {
        "text": request.text,
        "image": request.image,
        "audioResponse": request.audioResponse,
        "stream": request.stream,
        "context": request.context
    }
    
    if request.image:
        result = await handle_message_logic(request_data)
        return result

    if request.text:
        response_stream = stream_response_logic(request.text, request.stream, request.context)
        return StreamingResponse(response_stream, media_type="text/plain")

    if request.audioResponse:
        result = await handle_message_logic(request_data)
        return result

    return {"error": "Invalid request"}