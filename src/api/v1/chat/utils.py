from typing import Any
from uuid import UUID

from src.ai.config import get_llm
from src.services.chat_service import ChatService


def get_config(thread_id: UUID) -> dict[str, Any]:
    return {"configurable": {"thread_id": str(thread_id)}}


def get_chat_service() -> ChatService:
    return ChatService(llm=get_llm("chat_name"))
