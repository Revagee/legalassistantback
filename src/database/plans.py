from src.database.base import BaseWithTimestamps
from sqlalchemy import String, Integer, Float
from sqlalchemy.orm import Mapped, mapped_column
from enum import IntEnum


class SubscriptionPlan(IntEnum):
    FREE = 0
    MONTHLY = 1


class Plan(BaseWithTimestamps):
    __tablename__ = "plans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True) # SubscriptionType
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    billing_period: Mapped[str] = mapped_column(String(255), nullable=False) # day, week, month, year
