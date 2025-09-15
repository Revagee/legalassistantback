from typing import Any
from uuid import UUID


def get_config(thread_id: UUID) -> dict[str, Any]:
    return {"configurable": {"thread_id": str(thread_id)}}
