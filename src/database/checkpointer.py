from typing import Any

from sqlalchemy import String, select, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from src.database.base import Base


class Checkpoint(Base):
    __tablename__ = "checkpoints"

    thread_id: Mapped[str] = mapped_column(String, primary_key=True, nullable=False)
    checkpoint_ns: Mapped[str] = mapped_column(
        String,
        primary_key=True,
        nullable=False,
        server_default=text("''"),
    )
    checkpoint_id: Mapped[str] = mapped_column(String, primary_key=True, nullable=False)
    parent_checkpoint_id: Mapped[str | None] = mapped_column(String, nullable=True)
    type_: Mapped[str | None] = mapped_column("type", String, nullable=True)

    checkpoint: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    metadata_: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )

    @staticmethod
    async def get_by_id(thread_id: str, session: AsyncSession) -> list["Checkpoint"]:
        return await session.scalars(
            select(Checkpoint)
            .where(Checkpoint.thread_id == thread_id)
            .distinct(Checkpoint.thread_id)
        )
