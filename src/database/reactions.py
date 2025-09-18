from src.database.base import BaseEntity
from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column


class Reaction(BaseEntity):
    __tablename__ = "reactions"

    thread_id: Mapped[str] = mapped_column(String, nullable=False)
    likes: Mapped[int] = mapped_column(Integer, nullable=False)
    dislikes: Mapped[int] = mapped_column(Integer, nullable=False)
