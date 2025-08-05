from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from controller.message import MessageRequest, handle_message_logic, stream_response_logic

router = APIRouter()


@router.post("/message")
async def handle_message(request: MessageRequest):
    """
    Unified endpoint to handle text, image, and audio requests.
    """
    return await handle_message_logic(request)