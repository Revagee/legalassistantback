from datetime import UTC, datetime, timedelta
from typing import Optional
from uuid import UUID

from sqlalchemy import ForeignKey, String, and_, delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from src.database.base import BaseEntity


class RefreshToken(BaseEntity):
    __tablename__ = "refresh_tokens"

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    token_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(nullable=False)
    revoked_at: Mapped[Optional[datetime]] = mapped_column(nullable=True, default=None)

    @classmethod
    async def create_token(
        cls,
        user_id: UUID,
        token_hash: str,
        session: AsyncSession,
        expires_in_days: int = 30,
    ) -> "RefreshToken":
        """Create a new refresh token."""
        expires_at = datetime.now(UTC) + timedelta(days=expires_in_days)
        token = cls(user_id=user_id, token_hash=token_hash, expires_at=expires_at)
        if session:
            session.add(token)
        return token

    @classmethod
    async def get_by_token_hash(
        cls, token_hash: str, session: AsyncSession
    ) -> Optional["RefreshToken"]:
        """Get refresh token by hash if it's valid (not expired or revoked)."""
        query = select(cls).where(
            and_(
                cls.token_hash == token_hash,
                cls.expires_at > datetime.now(UTC),
                cls.revoked_at.is_(None),
            )
        )
        result = await session.execute(query)
        return result.scalar_one_or_none()

    @classmethod
    async def revoke_token(cls, token_hash: str, session: AsyncSession) -> bool:
        """Revoke a refresh token."""
        token = await cls.get_by_token_hash(token_hash, session)
        if token:
            token.revoked_at = datetime.now(UTC)
            await session.commit()
            return True
        return False

    @classmethod
    async def revoke_all_user_tokens(cls, user_id: UUID, session: AsyncSession) -> None:
        """Revoke all refresh tokens for a user."""
        query = select(cls).where(
            and_(cls.user_id == user_id, cls.revoked_at.is_(None))
        )
        result = await session.execute(query)
        tokens = result.scalars().all()

        for token in tokens:
            token.revoked_at = datetime.now(UTC)

        await session.commit()

    @classmethod
    async def cleanup_expired_tokens(cls, session: AsyncSession) -> int:
        """Remove expired and revoked tokens."""
        cutoff_date = datetime.now(UTC)
        query = delete(cls).where(cls.expires_at < cutoff_date)
        result = await session.execute(query)
        await session.commit()
        return result.rowcount

    async def revoke(self, session: AsyncSession) -> None:
        """Revoke this token."""
        self.revoked_at = datetime.now(UTC)
        await session.commit()

    def is_valid(self) -> bool:
        """Check if token is still valid."""
        now = datetime.now(UTC)
        return self.expires_at > now and self.revoked_at is None
