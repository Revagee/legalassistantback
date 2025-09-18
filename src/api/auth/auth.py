import logging
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError


from src.database.subscriptions import Subscription
import src.schema.auth as schema
from src.database.session import get_session
from src.database.password_resets import PasswordReset
from src.database.refresh_tokens import RefreshToken
from src.database.users import User
from src.database.plans import SubscriptionPlan
from src.database.subscriptions import SubscriptionStatus
from src.middleware.auth_middleware import get_current_user
from src.services.auth_service import AuthConfig, AuthService, TokenService
from src.services.email_service import EmailService
from sqlalchemy import select

router = APIRouter()
logger = logging.getLogger(__name__)

auth_service = AuthService()
email_service = EmailService()


@router.post(
    "/register",
    response_model=schema.RegisterResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register(user_data: schema.UserRegisterRequest):
    """Register a new user."""
    session = get_session()

    async with session:
        # Check if user already exists
        existing_user = await User.get_by_email(user_data.email.strip(), session)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Електронна адреса вже зареєстрована",
            )

        # Validate password strength
        if not auth_service.password_service.validate_password_strength(
            user_data.password
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=auth_service.get_password_requirements_error(),
            )

        # Hash password
        password_hash = auth_service.password_service.hash_password(user_data.password)

        # Generate email verification token
        verification_token, expires_at = (
            auth_service.email_token_service.create_verification_token(None)
        )

        # Create user
        user = User(
            email=user_data.email.strip(),
            name=user_data.name,
            password_hash=password_hash,
            email_verification_token=verification_token,
            email_verification_expires_at=expires_at,
        )

        try:
            session.add(user)
            await session.commit()
            await session.refresh(user)
        except IntegrityError:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Електронна адреса вже зареєстрована",
            )

        # Send verification email
        email_sent = await email_service.send_verification_email(
            user.email, verification_token
        )

        if not email_sent:
            logger.warning(f"Failed to send verification email to {user_data.email}")

        return schema.RegisterResponse(
            message="Реєстрація успішна. Перевірте електронну пошту та підтвердіть акаунт.",
        )


@router.post("/login", response_model=schema.TokenResponse)
async def login(user_data: schema.UserLoginRequest):
    """Authenticate user and return tokens."""
    async with get_session() as session:
        # Authenticate user
        user = await auth_service.authenticate_user(
            user_data.email.strip(), user_data.password, session
        )
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Невірні облікові дані"
            )

        # Check if email is verified
        if not user.email_verified:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Електронну адресу не підтверджено. Перевірте пошту та підтвердіть акаунт.",
            )

        # Create tokens
        access_token, refresh_token, expire = await auth_service.create_user_tokens(
            user, session
        )

        subscription = await session.scalar(select(Subscription).where(Subscription.user_id == user.id))
        if not subscription or subscription.status == SubscriptionStatus.FROZEN.value:
            plan_id = SubscriptionPlan.FREE.value
        else:
            plan_id = subscription.plan_id

        user_response = schema.UserResponse(name=user.name, email=user.email, plan_id=plan_id)

        return schema.TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=int(
                timedelta(hours=AuthConfig.ACCESS_TOKEN_EXPIRE_HOURS).total_seconds()
            ),
            user=user_response,
        )


@router.post("/refresh", response_model=schema.RefreshTokenResponse)
async def refresh_token(token_data: schema.RefreshTokenRequest):
    """Refresh access token using refresh token."""
    session = get_session()

    async with session:
        # Hash the refresh token
        token_service = TokenService()
        token_hash = token_service.hash_token(token_data.refresh_token)

        # Validate refresh token
        refresh_token = await RefreshToken.get_by_token_hash(token_hash, session)
        if not refresh_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Недійсний або прострочений токен оновлення",
            )

        # Get user
        user = await User.get_by_id(refresh_token.user_id, session)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Користувача не знайдено",
            )

        # Create new access token
        access_token, expire = token_service.create_access_token(user.id, user.email)

        return schema.RefreshTokenResponse(
            access_token=access_token,
            expires_in=int(
                timedelta(hours=AuthConfig.ACCESS_TOKEN_EXPIRE_HOURS).total_seconds()
            ),
        )


@router.post("/logout", response_model=schema.MessageResponse)
async def logout(
    logout_data: schema.LogoutRequest, current_user: User = Depends(get_current_user)
):
    """Logout user and revoke refresh token."""
    session = get_session()

    async with session:
        if logout_data.refresh_token:
            # Revoke specific refresh token
            token_service = TokenService()
            token_hash = token_service.hash_token(logout_data.refresh_token)
            await RefreshToken.revoke_token(token_hash, session)
        else:
            # Revoke all user's refresh tokens
            await RefreshToken.revoke_all_user_tokens(current_user.id, session)

        return schema.MessageResponse(message="Logged out successfully")


@router.post("/forgot-password", response_model=schema.MessageResponse)
async def forgot_password(request_data: schema.ForgotPasswordRequest):
    """Send password reset email."""
    session = get_session()

    async with session:
        # Check if user exists
        user = await User.get_by_email(request_data.email.strip(), session)
        if not user:
            # Don't reveal if email exists or not
            return schema.MessageResponse(
                message="Якщо електронна адреса існує, посилання для скидання пароля надіслано."
            )

        # Invalidate any existing password reset tokens
        await PasswordReset.invalidate_user_tokens(user.id, session)

        # Generate password reset token
        reset_token, expires_at = (
            auth_service.email_token_service.create_password_reset_token(user.id)
        )
        token_hash = auth_service.token_service.hash_token(reset_token)

        # Store password reset token
        password_reset = await PasswordReset.create_reset_token(
            user_id=user.id, token_hash=token_hash, session=session
        )
        session.add(password_reset)
        await session.commit()

        # Send reset email
        email_sent = await email_service.send_password_reset_email(
            user.email, reset_token
        )

        if not email_sent:
            logger.warning(
                f"Failed to send password reset email to {request_data.email}"
            )

        return schema.MessageResponse(
            message="Якщо електронна адреса існує, посилання для скидання пароля надіслано."
        )


@router.post("/reset-password", response_model=schema.MessageResponse)
async def reset_password(request_data: schema.ResetPasswordRequest):
    """Reset password using reset token."""
    session = get_session()

    async with session:
        # Validate password strength
        if not auth_service.password_service.validate_password_strength(
            request_data.new_password
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=auth_service.get_password_requirements_error(),
            )

        # Hash the reset token
        token_hash = auth_service.token_service.hash_token(request_data.token)

        # Get valid password reset token
        password_reset = await PasswordReset.get_valid_token(token_hash, session)
        if not password_reset:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Недійсний або прострочений токен для скидання пароля",
            )

        # Get user
        user = await User.get_by_id(password_reset.user_id, session)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Користувача не знайдено",
            )

        # Update password
        user.password_hash = auth_service.password_service.hash_password(
            request_data.new_password
        )

        # Mark token as used
        await password_reset.mark_as_used(session)

        # Revoke all refresh tokens for security
        await RefreshToken.revoke_all_user_tokens(user.id, session)

        await session.commit()

        return schema.MessageResponse(message="Пароль успішно змінено")


@router.get("/verify-email", response_model=schema.MessageResponse)
async def verify_email(token: str):
    """Verify user's email address."""
    session = get_session()

    async with session:
        # Get user by verification token
        user = await User.get_by_verification_token(token, session)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Строк дії токена підтвердження минув",
            )

        # Verify email
        await user.verify_email(session)

        return schema.MessageResponse(message="Електронну адресу успішно підтверджено")


@router.post("/resend-verification", response_model=schema.MessageResponse)
async def resend_verification_email(request_data: schema.ResendVerificationRequest):
    """Resend email verification email."""
    session = get_session()

    async with session:
        # Check if user exists
        user = await User.get_by_email(request_data.email.strip(), session)
        if not user:
            # Don't reveal if email exists or not
            return schema.MessageResponse(
                message="Якщо електронна адреса існує, лист для підтвердження надіслано."
            )

        # Check if email is already verified
        if user.email_verified:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Електронну адресу вже підтверджено",
            )

        # Generate new verification token
        verification_token, expires_at = (
            auth_service.email_token_service.create_verification_token(None)
        )

        # Update user with new verification token
        user.email_verification_token = verification_token
        user.email_verification_expires_at = expires_at

        await session.commit()

        # Send verification email
        email_sent = await email_service.send_verification_email(
            user.email, verification_token
        )

        if not email_sent:
            logger.warning(
                f"Failed to resend verification email to {request_data.email}"
            )

        return schema.MessageResponse(
            message="Лист для підтвердження надіслано успішно"
        )


@router.get("/me", response_model=schema.UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Get current user information."""
    async with get_session() as session:
        subscription = await session.scalar(select(Subscription).where(Subscription.user_id == current_user.id))
        if not subscription or subscription.status == SubscriptionStatus.FROZEN.value:
            plan_id = SubscriptionPlan.FREE.value
        else:
            plan_id = subscription.plan_id
    return schema.UserResponse(name=current_user.name, email=current_user.email, plan_id=plan_id)


@router.post("/change-password", response_model=schema.MessageResponse)
async def change_password(
    request_data: schema.ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
):
    """Change user's password."""
    session = get_session()

    async with session:
        # Verify current password
        if not auth_service.password_service.verify_password(
            request_data.current_password, current_user.password_hash
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current password is incorrect",
            )

        # Validate new password strength
        if not auth_service.password_service.validate_password_strength(
            request_data.new_password
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=auth_service.get_password_requirements_error(),
            )

        # Update password
        current_user.password_hash = auth_service.password_service.hash_password(
            request_data.new_password
        )
        await session.commit()

        # Revoke all refresh tokens for security
        await RefreshToken.revoke_all_user_tokens(current_user.id, session)

        return schema.MessageResponse(message="Пароль успішно змінено")


@router.delete("/delete-account", response_model=schema.MessageResponse)
async def delete_account(current_user: User = Depends(get_current_user)):
    """Delete the current user's account."""
    session = get_session()

    async with session:
        # Revoke all refresh tokens
        await RefreshToken.revoke_all_user_tokens(current_user.id, session)

        # Delete the user account
        await session.delete(current_user)
        await session.commit()

        return schema.MessageResponse(message="Акаунт успішно видалено")
