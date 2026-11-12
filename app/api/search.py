from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import EmbedderDep, SessionDep, require_api_key
from app.config import get_settings
from app.schemas import ClientSearchHit, DocumentSearchHit, ErrorResponse, SearchHit
from app.services import search as search_service
from app.services.dto import ClientHit, SearchResult

router = APIRouter(tags=["search"], dependencies=[Depends(require_api_key)])


@router.get(
    "/search",
    response_model=list[SearchHit],
    summary="Search clients and documents",
    description=(
        "Hybrid search. Clients match by substring/fuzzy email, name or description and by the "
        "meaning of their description; documents match by meaning (Sentence-BERT, with domain "
        "synonyms such as *address proof* -> *utility bill*) and by exact terms (full-text). "
        "Results are one list ranked by relevance; `type` tells clients and documents apart."
    ),
    responses={
        401: {"model": ErrorResponse, "description": "Invalid or missing API key"},
        422: {"description": "Missing, blank or too long query"},
    },
)
async def search(
    q: Annotated[str, Query(min_length=1, max_length=500, description="Search query")],
    session: SessionDep,
    embedder: EmbedderDep,
) -> list[SearchHit]:
    if not q.strip():
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Query must not be blank")
    settings = get_settings()
    results = await search_service.search(
        session,
        embedder,
        q,
        min_similarity=settings.search_min_similarity,
        limit=settings.search_result_limit,
    )
    return [_to_schema(result) for result in results]


def _to_schema(result: SearchResult) -> SearchHit:
    if isinstance(result, ClientHit):
        return ClientSearchHit.model_validate(result, from_attributes=True)
    return DocumentSearchHit.model_validate(result, from_attributes=True)
