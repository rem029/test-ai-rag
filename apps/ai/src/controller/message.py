from typing import Optional
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from services.ai import stream_response_logic

class MessageRequest(BaseModel):
    session_id: Optional[str]
    text: Optional[str] = None
    image: Optional[str] = None  # Base64 encoded image
    audioResponse: Optional[bool] = False
    stream: Optional[bool] = False
    messages: Optional[list] = []  # Store conversation history
    context: Optional[str] = None  # Optional context to replace system_prompt


async def handle_message_logic(request: MessageRequest):
    """
    Handle message processing logic.
    """    
    
    if request.text:
        response_stream = stream_response_logic(request.session_id, request.text, request.stream, request.context, request.image,request.audioResponse)
        return StreamingResponse(response_stream, media_type="text/plain")

    if request.audioResponse:
        return {"message": "Audio response not yet implemented"}

    return {"error": "Invalid request"}


