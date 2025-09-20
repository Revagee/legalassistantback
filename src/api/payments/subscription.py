import os
from datetime import datetime
from fastapi import APIRouter
from fastapi import Depends
from uuid import uuid4
from src.schema.payments import (
    SubscriptionRequest,
    SubscriptionPlan,
    CallbackRequest,
    PlansResponse,
)
from src.schema.auth import UserResponse
from src.database.plans import Plan
from datetime import timedelta
from fastapi import Response
from src.middleware.auth_middleware import get_current_user
from src.database.users import User
from src.services.liqpay_client import liqpay_request
import logging
from src.database.subscriptions import Subscription
from src.database.session import get_session
from sqlalchemy import select
from src.database.subscriptions import SubscriptionStatus
from fastapi import HTTPException
import base64
import hashlib
import json

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/subscription")


@router.post("/create")
async def create_subscription(
    request: SubscriptionRequest, user: User = Depends(get_current_user)
):
    async with get_session() as session:
        if request.subscription_plan == SubscriptionPlan.FREE:
            return Response(status_code=400, content="План не може бути безкоштовним")

        subscription = await session.scalar(select(Subscription).where(Subscription.user_id == user.id))
        if subscription:
            return Response(status_code=409, content="Підписка вже існує")

        plan = await session.scalar(select(Plan).where(Plan.id == request.subscription_plan.value))
        if not plan:
            return Response(status_code=404, content="План не знайдений")

        order_id = uuid4()

        payload = {
            "action": "subscribe",
            "version": "3",
            "phone": request.phone,
            "amount": plan.amount,
            "currency": plan.currency,
            "description": "Зняття оплати за підписку.",
            "order_id": str(order_id),
            "subscribe": "1",
            "subscribe_date_start": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "subscribe_periodicity": plan.billing_period,
            "card": request.card,
            "card_exp_month": request.card_exp_month,
            "card_exp_year": request.card_exp_year,
            "card_cvv": request.cvv,
            "server_url": f"{os.getenv('API_BASE_URL')}/payments/subscription/callback",
        }

        res = await liqpay_request(payload)
        if res["status"] != "subscribed":
            return Response(status_code=400, content="Оплата не успішна")

        # Add subscription
        start_date = datetime.now()

        if plan.billing_period == "day":
            end_date = start_date + timedelta(days=1)
        elif plan.billing_period == "week":
            end_date = start_date + timedelta(days=7)
        elif plan.billing_period == "month":
            end_date = start_date + timedelta(days=30)
        elif plan.billing_period == "year":
            end_date = start_date + timedelta(days=365) # FIXME: consider leap years
        else:
            raise ValueError("Invalid billing period")

        subscription = Subscription(
            id=order_id,
            user_id=user.id,
            plan_id=plan.id,
            status=SubscriptionStatus.ACTIVE.value,
            start_date=start_date,
            end_date=end_date,
        )
        session.add(subscription)
        await session.commit()

    return UserResponse(name=user.name, email=user.email, plan_id=plan.id)


@router.post("/cancel")
async def cancel_subscription(user: User = Depends(get_current_user)):
    async with get_session() as session:
        subscription = await session.scalar(select(Subscription).where(Subscription.user_id == user.id))
        if not subscription:
            return Response(status_code=400, content="У користувача немає підписки")
        elif subscription.status != SubscriptionStatus.ACTIVE.value:
            return Response(status_code=400, content="Підписка не активна")

        payload = {
            "action": "unsubscribe",
            "version": "3",
            "order_id": str(subscription.id),
        }
        res = await liqpay_request(payload)

        if res["status"] != "unsubscribed":
            return Response(status_code=400, content="Скасування підписки не успішна")

        subscription.status = SubscriptionStatus.CANCELLED.value
        await session.commit()

    return Response(status_code=204, content="OK")


@router.post("/callback")
async def subscription_callback(request: CallbackRequest):
    """Handle LiqPay server-to-server callback.

    LiqPay sends form-encoded fields: `data` (base64 JSON) and `signature`.
    We verify the signature and return 200 on success.
    """
    private_key = os.getenv("LIQPAY_PRIVATE_KEY")
    if not private_key:
        logger.error("LiqPay private key is not configured; cannot verify callback signature")
        raise HTTPException(status_code=500, detail="Server misconfiguration")

    # Verify signature: signature = b64( sha1(private_key + data + private_key) )
    signature_raw = f"{private_key}{request.data}{private_key}".encode("utf-8")
    expected_signature = base64.b64encode(hashlib.sha1(signature_raw).digest()).decode("utf-8")

    if request.signature != expected_signature:
        logger.warning("Invalid LiqPay callback signature")
        raise HTTPException(status_code=400, detail="Invalid signature")

    # Decode payload
    payload_json = json.loads(base64.b64decode(request.data).decode("utf-8"))

    order_id = payload_json["order_id"]
    status = payload_json["status"]
    completion_date = payload_json["completion_date"]
    async with get_session() as session:
        subscription = await session.scalar(select(Subscription).where(Subscription.id == order_id))
        if not subscription:
            return Response(status_code=404, content="Підписка не знайдена")

        plan = await session.scalar(select(Plan).where(Plan.id == subscription.plan_id))
        if not plan:
            return Response(status_code=404, content="План не знайдений")

        if status == "success":
            if plan.billing_period == "day":
                delta = timedelta(days=1)
            elif plan.billing_period == "week":
                delta = timedelta(days=7)
            elif plan.billing_period == "month":
                delta = timedelta(days=30)
            elif plan.billing_period == "year":
                delta = timedelta(days=365)

            subscription.end_date = completion_date + delta
            subscription.status = SubscriptionStatus.ACTIVE.value
            subscription.plan_id = plan.id
        else:
            subscription.status = SubscriptionStatus.FROZEN.value

        await session.commit()

    return Response(status_code=204, content="OK")


@router.get("/plans", response_model=PlansResponse)
async def get_plans():
    async with get_session() as session:
        plans = await session.scalars(select(Plan))
        return PlansResponse(plans=[Plan(id=plan.id, name=plan.name, amount=plan.amount, currency=plan.currency, billing_period=plan.billing_period) for plan in plans])