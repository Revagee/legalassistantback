from src.database.session import get_session
from src.database.subscriptions import Subscription, SubscriptionStatus
from src.database.users import User
from sqlalchemy import delete, select, update
from datetime import datetime
from src.database.plans import SubscriptionPlan


async def delete_expired_subscriptions():
    async with get_session() as session:
        subscriptions_to_delete = await session.scalars(
            select(Subscription).where(
                Subscription.status == SubscriptionStatus.CANCELLED.value,
                Subscription.end_date < datetime.now()
            )
        )

        subscriptions_to_delete = subscriptions_to_delete.all()

        if subscriptions_to_delete:
            user_ids = [sub.user_id for sub in subscriptions_to_delete]
            await session.execute(
                update(User).where(User.id.in_(user_ids)).values(plan_id=SubscriptionPlan.FREE.value)
            )

            await session.execute(
                delete(Subscription).where(
                    Subscription.id.in_([sub.id for sub in subscriptions_to_delete])
                )
            )
            await session.commit()
