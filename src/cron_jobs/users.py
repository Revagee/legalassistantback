from src.database.users import User
from src.database.session import get_session


async def cleanup_unverified_accounts() -> None:
    async with get_session() as session:
        await User.cleanup_unverified_with_expired_tokens(session)
