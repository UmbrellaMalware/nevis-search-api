import secrets
from collections.abc import AsyncIterator
from typing import Annotated, cast

from fastapi import Depends, HTTPException, Request, Security, status
from fastapi.security import APIKeyHeader
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.config import get_settings
from app.services.embeddings import Embedder

_api_key_header = APIKeyHeader(
    name="X-API-Key",
    auto_error=False,
    description="API key. Required when the server is started with API_KEY set.",
)


async def require_api_key(api_key: Annotated[str | None, Security(_api_key_header)]) -> None:
    expected = get_settings().api_key
    if not expected:
        return  # auth disabled (local development)
    if api_key is None or not secrets.compare_digest(api_key.encode(), expected.encode()):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
            headers={"WWW-Authenticate": "APIKey"},
        )


async def get_session(request: Request) -> AsyncIterator[AsyncSession]:
    sessionmaker = cast(async_sessionmaker[AsyncSession], request.app.state.sessionmaker)
    async with sessionmaker() as session:
        yield session


def get_embedder(request: Request) -> Embedder:
    return cast(Embedder, request.app.state.embedder)


SessionDep = Annotated[AsyncSession, Depends(get_session)]
EmbedderDep = Annotated[Embedder, Depends(get_embedder)]
