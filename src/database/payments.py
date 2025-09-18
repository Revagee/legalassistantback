# from src.database.base import BaseEntity
# from sqlalchemy.orm import Mapped, mapped_column
# from sqlalchemy import ForeignKey
# from uuid import UUID


# class Payment(BaseEntity):
#     __tablename__ = "payments"

#     user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
#     subscription_id: Mapped[UUID] = mapped_column(ForeignKey("subscriptions.id"), nullable=False)
