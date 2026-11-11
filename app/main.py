from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.api import clients, health, search
from app.config import get_settings
from app.db import create_engine
from app.services.embeddings import load_embedder


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    engine = create_engine(settings.database_url)
    app.state.engine = engine
    app.state.sessionmaker = async_sessionmaker(engine, expire_on_commit=False)
    app.state.embedder = load_embedder(settings.embedding_model, settings.embedding_model_revision)
    try:
        yield
    finally:
        await engine.dispose()


def create_app() -> FastAPI:
    app = FastAPI(
        title="Nevis Search API",
        version="0.1.0",
        description="Search across clients and their documents.",
        lifespan=lifespan,
    )
    app.include_router(health.router)
    app.include_router(clients.router)
    app.include_router(search.router)
    return app


app = create_app()
