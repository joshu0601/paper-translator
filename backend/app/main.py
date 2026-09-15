from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import annotations, chat, documents, search, summary
from app.config import get_settings
from app.database import init_db
from app.services import pipeline

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    pipeline.resume_interrupted()
    yield


app = FastAPI(
    title=f"{settings.app_name} API",
    version="0.1.0",
    description="AI academic paper reading, translation and grounded Q&A.",
    lifespan=lifespan,
)

# RFC 1918 ranges + localhost, any port.
_PRIVATE_ORIGIN_RE = (
    r"^https?://(localhost|127\.0\.0\.1|\[::1\]|10\.\d{1,3}\.\d{1,3}\.\d{1,3}"
    r"|192\.168\.\d{1,3}\.\d{1,3}|172\.(1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3})(:\d+)?$"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_origin_regex=_PRIVATE_ORIGIN_RE if settings.cors_allow_private_network else None,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(documents.router)
app.include_router(chat.router)
app.include_router(search.router)
app.include_router(annotations.router)
app.include_router(summary.router)


@app.get("/api/health", tags=["meta"])
def health():
    return {
        "status": "ok",
        "llm": settings.llm_provider,
        "embeddings": settings.embedding_provider,
        "translation": settings.translation_provider,
        "database": "postgresql" if settings.is_postgres else "sqlite",
    }
