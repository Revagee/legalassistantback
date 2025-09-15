from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from src.database.session import get_session
from src.database.users import User
from src.services.auth_service import TokenService

security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> User:
    """Get the current authenticated user from JWT token."""
    token = credentials.credentials

    # Verify the token
    token_service = TokenService()
    payload = token_service.verify_access_token(token)

    # Extract user ID from token
    user_id_str = payload.get("sub")
    if not user_id_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Недійсний токен: відсутній ідентифікатор користувача",
        )

    try:
        user_id = UUID(user_id_str)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Недійсний токен: неправильний формат ідентифікатора користувача",
        )

    # Get user from database
    session = get_session()
    async with session:
        user = await User.get_by_id(user_id, session)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Користувача не знайдено",
            )

        if not user.email_verified:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Електронну адресу не підтверджено",
            )

    return user
