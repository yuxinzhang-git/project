from fastapi import APIRouter, HTTPException

from app.schemas.chat import ChatRequest, ChatResponse
from app.services.chat import ChatService

router = APIRouter(prefix="/api", tags=["chat"])
service = ChatService()


@router.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    try:
        return service.reply(request.message, request.conversation_history)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Chat unavailable: {exc}") from exc

