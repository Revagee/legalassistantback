from datetime import UTC, datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import Boolean, String, and_, delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from src.database.base import BaseEntity


class User(BaseEntity):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    email_verification_token: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True, default=None
    )
    email_verification_expires_at: Mapped[Optional[datetime]] = mapped_column(
        nullable=True, default=None
    )

    @classmethod
    async def get_by_email(cls, email: str, session: AsyncSession) -> Optional["User"]:
        """Get user by email address."""
        # Perform case-insensitive email lookup
        query = select(cls).where(func.lower(cls.email) == email.lower())
        result = await session.execute(query)
        return result.scalar_one_or_none()

    @classmethod
    async def get_by_id(cls, user_id: UUID, session: AsyncSession) -> Optional["User"]:
        """Get user by ID."""
        return await session.get(cls, user_id)

    @classmethod
    async def get_by_verification_token(
        cls, token: str, session: AsyncSession
    ) -> Optional["User"]:
        """Get user by email verification token."""
        query = select(cls).where(
            and_(
                cls.email_verification_token == token,
                cls.email_verification_expires_at > datetime.now(UTC),
            )
        )
        result = await session.execute(query)
        return result.scalar_one_or_none()

    @classmethod
    async def cleanup_unverified_with_expired_tokens(cls, session: AsyncSession) -> int:
        """Delete unverified accounts where the email verification token is expired."""
        now_utc = datetime.now(UTC)

        query = delete(cls).where(
            and_(
                cls.email_verified == False,  # noqa: E712
                cls.email_verification_expires_at <= now_utc,
            )
        )

        await session.execute(query)
        await session.commit()

        return None

    async def verify_email(self, session: AsyncSession) -> None:
        """Mark user's email as verified."""
        self.email_verified = True
        self.email_verification_token = None
        self.email_verification_expires_at = None
        await session.commit()

    def to_dict(self) -> dict:
        """Convert user to dictionary for API responses."""
        return {
            "id": str(self.id),
            "email": self.email,
            "email_verified": self.email_verified,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
