import hashlib
import os
import secrets
from datetime import UTC, datetime, timedelta
from typing import Optional
from uuid import UUID

import bcrypt
import jwt
from fastapi import HTTPException, status

from src.database.refresh_tokens import RefreshToken
from src.database.users import User


class AuthConfig:
    """Authentication configuration."""

    SECRET_KEY = os.getenv(
        "JWT_SECRET_KEY", "your-secret-key-change-this-in-production"
    )
    ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
    REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "30"))
    EMAIL_VERIFICATION_EXPIRE_HOURS = int(
        os.getenv("EMAIL_VERIFICATION_EXPIRE_HOURS", "24")
    )
    PASSWORD_RESET_EXPIRE_HOURS = int(os.getenv("PASSWORD_RESET_EXPIRE_HOURS", "24"))


class PasswordService:
    """Service for password hashing and verification."""

    @staticmethod
    def hash_password(password: str) -> str:
        """Hash a password using bcrypt."""
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
        return hashed.decode("utf-8")

    @staticmethod
    def verify_password(password: str, hashed: str) -> bool:
        """Verify a password against its hash."""
        return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))

    @staticmethod
    def validate_password_strength(password: str) -> bool:
        """Validate password meets security requirements."""
        if len(password) < 8:
            return False

        has_upper = any(c.isupper() for c in password)
        has_lower = any(c.islower() for c in password)
        has_digit = any(c.isdigit() for c in password)

        return has_upper and has_lower and has_digit


class TokenService:
    """Service for JWT token management."""

    @staticmethod
    def create_access_token(user_id: UUID, email: str) -> tuple[str, datetime]:
        """Create a JWT access token."""
        expire = datetime.now(UTC) + timedelta(
            minutes=AuthConfig.ACCESS_TOKEN_EXPIRE_MINUTES
        )
        to_encode = {
            "sub": str(user_id),
            "email": email,
            "exp": expire,
            "iat": datetime.now(UTC),
            "type": "access",
        }
        encoded_jwt = jwt.encode(
            to_encode, AuthConfig.SECRET_KEY, algorithm=AuthConfig.ALGORITHM
        )
        return encoded_jwt, expire

    @staticmethod
    def create_refresh_token() -> str:
        """Create a secure refresh token."""
        return secrets.token_urlsafe(32)

    @staticmethod
    def verify_access_token(token: str) -> dict:
        """Verify and decode a JWT access token."""
        try:
            payload = jwt.decode(
                token, AuthConfig.SECRET_KEY, algorithms=[AuthConfig.ALGORITHM]
            )
            if payload.get("type") != "access":
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token type",
                )
            return payload
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Token has expired"
            )
        except jwt.PyJWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token"
            )

    @staticmethod
    def hash_token(token: str) -> str:
        """Hash a token for secure storage."""
        return hashlib.sha256(token.encode()).hexdigest()


class EmailTokenService:
    """Service for email verification and password reset tokens."""

    @staticmethod
    def generate_secure_token() -> str:
        """Generate a secure token for email verification or password reset."""
        return secrets.token_urlsafe(32)

    @staticmethod
    def create_verification_token(user_id: UUID) -> tuple[str, datetime]:
        """Create an email verification token."""
        token = EmailTokenService.generate_secure_token()
        expire = datetime.now(UTC) + timedelta(
            hours=AuthConfig.EMAIL_VERIFICATION_EXPIRE_HOURS
        )
        return token, expire

    @staticmethod
    def create_password_reset_token(user_id: UUID) -> tuple[str, datetime]:
        """Create a password reset token."""
        token = EmailTokenService.generate_secure_token()
        expire = datetime.now(UTC) + timedelta(
            hours=AuthConfig.PASSWORD_RESET_EXPIRE_HOURS
        )
        return token, expire


class AuthService:
    """Main authentication service."""

    def __init__(self):
        self.password_service = PasswordService()
        self.token_service = TokenService()
        self.email_token_service = EmailTokenService()

    async def authenticate_user(
        self, email: str, password: str, session
    ) -> Optional[User]:
        """Authenticate a user with email and password."""
        user = await User.get_by_email(email, session)
        if not user:
            return None

        if not self.password_service.verify_password(password, user.password_hash):
            return None

        return user

    async def create_user_tokens(
        self, user: User, session
    ) -> tuple[str, str, datetime]:
        """Create access and refresh tokens for a user."""
        # Create access token
        access_token, expire = self.token_service.create_access_token(
            user.id, user.email
        )

        # Create refresh token
        refresh_token = self.token_service.create_refresh_token()
        refresh_token_hash = self.token_service.hash_token(refresh_token)

        # Store refresh token in database
        db_refresh_token = await RefreshToken.create_token(
            user_id=user.id, token_hash=refresh_token_hash, session=session
        )
        session.add(db_refresh_token)
        await session.commit()

        return access_token, refresh_token, expire

    def get_password_requirements_error(self) -> str:
        """Get password requirements error message."""
        return (
            "Password must be at least 8 characters long and contain "
            "at least one uppercase letter, one lowercase letter, and one digit."
        )
