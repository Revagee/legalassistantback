import logging

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()

from src.api.v1.api import api_router  # noqa: E402

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Pravo Helper API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
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
