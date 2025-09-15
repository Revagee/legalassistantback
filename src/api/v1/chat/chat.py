import json
import os
import logging
from datetime import datetime
from functools import partial
from typing import AsyncGenerator
from uuid import uuid4, UUID
from fastapi import APIRouter, Depends, status, Request
from fastapi.responses import StreamingResponse
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessageChunk, HumanMessage
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from src.database.utils import get_session
from src.middleware.auth_middleware import get_user_id_from_token
from src.ai.config import get_llm
from sqlalchemy import select, func, cast, Integer

# from database.checkpoints import Checkpoint
from src.ai.agent import LegalAgent
from src.api.v1.chat.utils import get_chat_service, get_config
from src.schema.chat import ChatRequest
from src.services.chat_service import ChatService
from fastapi.background import BackgroundTasks
from src.cache.redis import get_redis

router = APIRouter()
logger = logging.getLogger(__name__)


def _empty_sse_response() -> StreamingResponse:
    return StreamingResponse(
        [],
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


async def generate_chat_name(message: str) -> str:
    llm = get_llm("chat_name")
    chat_service = ChatService(llm)
    async with get_session() as session:
        checkpoint = await session.scalar(
            select(Checkpoint)
            .where(
                Checkpoint.user_id == user_id,
                Checkpoint.thread_id == thread_id,
            )
            .limit(1)
        )

        chat_name = await chat_service.generate_chat_name(request.message)


async def generate_response(
    request: ChatRequest, llm: BaseChatModel, stream_id: UUID, config: RunnableConfig
) -> None:
    r = get_redis()
    async with AsyncPostgresSaver.from_conn_string(
        conn_string=os.getenv("DATABASE_URL", ""),
    ) as checkpointer:
        graph = LegalAgent(
            llm=llm,
            checkpointer=checkpointer,
            store=None,
        ).get_graph()

        events = graph.astream(
            {"messages": HumanMessage(content=request.message)},
            config,
            stream_mode="messages",
        )

        async for msg, metadata in events:
            if msg.response_metadata and msg.response_metadata.get("finish_reason"):
                msg_id = await r.xadd(stream_id, {"type": "message_ended"})
                await r.set(f"{stream_id}:message_ended", msg_id)
            if (
                isinstance(msg, AIMessageChunk)
                and msg.content
                and metadata.get("agent", "") == "agent"
            ):
                await r.xadd(stream_id, {"type": "chunk", "content": msg.content})
        await r.xadd(stream_id, {"type": "end"})
        await r.set(f"{stream_id}:status", "completed")


@router.post("/message", status_code=status.HTTP_200_OK)
async def chat_message(
    request: ChatRequest,
    user_id: UUID = Depends(get_user_id_from_token),
    llm: BaseChatModel = Depends(partial(get_llm, "communication_agent")),
    *,
    background_tasks: BackgroundTasks,
) -> None:
    config = get_config(thread_id=request.thread_id, user_id=user_id)
    config["configurable"]["last_activity_time"] = datetime.now().isoformat()

    background_tasks.add_task(generate_chat_name, request.message)


    r = get_redis()

    stream_id = str(uuid4())
    await r.set(f"{stream_id}:status", "running")
    await r.set(str(request.thread_id), stream_id)

    background_tasks.add_task(
        generate_response,
        request,
        llm,
        stream_id,
        config,
    )

    return None


@router.get("/stream")
async def stream_tokens(thread_id: UUID, request: Request):
    r = get_redis()
    STREAM_ID: str | None = await r.get(str(thread_id))
    if not STREAM_ID:
        return _empty_sse_response()

    status: str | None = await r.get(f"{STREAM_ID}:status")
    if not status or status == "completed":
        return _empty_sse_response()

    group_name = f"group-{uuid4()}"

    message_ended_id = await r.get(f"{STREAM_ID}:message_ended")
    initial_group_id = message_ended_id or "0"

    await r.xgroup_create(STREAM_ID, group_name, id=initial_group_id, mkstream=True)

    async def get_chunks() -> AsyncGenerator[str, None]:
        while True:
            messages = await r.xreadgroup(
                groupname=group_name,
                consumername="0",
                streams={STREAM_ID: ">"},
                count=None,
            )

            if messages:
                for _, msgs in messages:
                    for msg_id, data in msgs:
                        yield f"data: {json.dumps(data)}\n\n"

                        await r.xack(STREAM_ID, group_name, msg_id)

            if:
                break

    return StreamingResponse(
        get_chunks(),
        media_type="text/event-stream",
        headers={
            "Content-Type": "text/event-stream",
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
