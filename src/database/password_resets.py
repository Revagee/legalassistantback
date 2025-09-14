from datetime import UTC, datetime, timedelta
from typing import Optional
from uuid import UUID

from sqlalchemy import ForeignKey, String, and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from src.database.base import BaseEntity


class PasswordReset(BaseEntity):
    __tablename__ = "password_resets"

    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(nullable=False)
    used_at: Mapped[Optional[datetime]] = mapped_column(nullable=True, default=None)

    @classmethod
    async def create_reset_token(
        cls, user_id: UUID, token_hash: str, session: AsyncSession, expires_in_hours: int = 24
    ) -> "PasswordReset":
        """Create a new password reset token."""
        expires_at = datetime.now(UTC) + timedelta(hours=expires_in_hours)
        reset_token = cls(user_id=user_id, token_hash=token_hash, expires_at=expires_at)
        if session:
            session.add(reset_token)
        return reset_token

    @classmethod
    async def get_valid_token(cls, token_hash: str, session: AsyncSession) -> Optional["PasswordReset"]:
        """Get a valid (unused and not expired) password reset token."""
        query = select(cls).where(
            and_(cls.token_hash == token_hash, cls.expires_at > datetime.now(UTC), cls.used_at.is_(None))
        )
        result = await session.execute(query)
        return result.scalar_one_or_none()

    @classmethod
    async def invalidate_user_tokens(cls, user_id: UUID, session: AsyncSession) -> None:
        """Mark all existing password reset tokens for a user as used."""
        query = select(cls).where(and_(cls.user_id == user_id, cls.used_at.is_(None)))
        result = await session.execute(query)
        tokens = result.scalars().all()

        for token in tokens:
            token.used_at = datetime.now(UTC)

        await session.commit()

    async def mark_as_used(self, session: AsyncSession) -> None:
        """Mark this token as used."""
        self.used_at = datetime.now(UTC)
        await session.commit()

    def is_valid(self) -> bool:
        """Check if token is still valid (not used and not expired)."""
        now = datetime.now(UTC)
        return self.expires_at > now and self.used_at is None
