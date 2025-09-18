import logging

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.cron_jobs.payments import delete_expired_subscriptions
from src.cron_jobs.users import cleanup_unverified_accounts
from datetime import datetime
from datetime import UTC
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from contextlib import asynccontextmanager

from src.api.api import api_router  # noqa: E402

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        func=delete_expired_subscriptions,
        trigger="interval",
        hours=12,
        next_run_time=datetime.now(UTC),
    )
    scheduler.add_job(
        func=cleanup_unverified_accounts,
        trigger="interval",
        hours=12,
        next_run_time=datetime.now(UTC),
    )
    scheduler.start()
    app.state.scheduler = scheduler
    yield
    scheduler.shutdown(wait=False)

app = FastAPI(
    title="Pravo Helper API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "localhost:5173",
        "http://localhost:5173",
        "http://pravohelper.com",
        "https://pravohelper.com",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    return {
        "status": "online",
        "message": "Pravo Helper API is running",
    }


app.include_router(api_router, prefix="")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
