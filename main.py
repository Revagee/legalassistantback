import logging

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()

from src.api.v1.api import api_router  # noqa: E402

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Legal Boss API",
    version="1.0.0",
    docs_url=None,
    redoc_url=None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Specify your allowed origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    return {"status": "online", "message": "WatchNext API is running", "version": "1.0.0"}


app.include_router(api_router, prefix="")
