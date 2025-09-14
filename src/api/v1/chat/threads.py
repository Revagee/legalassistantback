from datetime import datetime

from sqlalchemy import select
from uuid import UUID

from fastapi import APIRouter, Depends
from src.middleware.auth_middleware import get_user_id_from_token

from src.database.utils import get_session
# from database.checkpoints import Checkpoint
from src.schema.chat import ThreadSchema

router = APIRouter()


@router.get(
    "",
    description="Get list of all user's threads.",
    response_model=list[ThreadSchema],
)
async def get_threads(user_id: UUID = Depends(get_user_id_from_token)):
    # async with get_session() as session:
    #     checkpoints = await session.scalars(
    #         select(Checkpoint)
    #         .where(Checkpoint.metadata_["user_id"].astext == str(user_id))
    #         .distinct(Checkpoint.thread_id)
    #     )

    # return [
    #     ThreadSchema(
    #         id=checkpoint.thread_id,
    #         chat_name=checkpoint.metadata_.get("chat_name", "New Chat"),
    #         created_at=checkpoint.metadata_.get(
    #             "last_activity_time", datetime.now().isoformat()
    #         ),
    #     )
    #     for checkpoint in checkpoints
    # ]

    from uuid import uuid4

    return [ThreadSchema(
        id=uuid4(),
        chat_name="New chat",
        created_at=datetime.now().isoformat()
    )]
