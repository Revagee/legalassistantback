from fastapi import APIRouter

from src.api.auth import auth
from src.api.chat import chat
from src.api.chat import thread
from src.api.chat import threads
from src.api.payments import subscription

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(chat.router, prefix="/chat", tags=["Chat"])
api_router.include_router(thread.router, prefix="/thread", tags=["Chat"])
api_router.include_router(threads.router, prefix="/threads", tags=["Chat"])
api_router.include_router(subscription.router, prefix="/payments", tags=["Payments"])
