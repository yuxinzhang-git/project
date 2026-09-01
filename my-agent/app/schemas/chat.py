from pydantic import BaseModel


class ChatRequest(BaseModel):
    message: str
    conversation_history: list[dict] | None = None


class ChatResponse(BaseModel):
    reply: str
    tool_calls: list[dict] | None = None

