import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, status

from app.api.deps import SessionDep, require_api_key
from app.exceptions import DocumentNotFoundError
from app.schemas import ErrorResponse, SummaryOut
from app.services import summaries as summary_service

router = APIRouter(prefix="/documents", tags=["documents"], dependencies=[Depends(require_api_key)])


@router.get(
    "/{id}/summary",
    response_model=SummaryOut,
    summary="Get a document's summary",
    description=(
        "Summaries are generated in the background after upload, usually within seconds. "
        "Poll this endpoint until `status` is `ready` (or `failed`)."
    ),
    responses={
        401: {"model": ErrorResponse, "description": "Invalid or missing API key"},
        404: {"model": ErrorResponse, "description": "Document not found"},
    },
)
async def get_summary(
    document_id: Annotated[uuid.UUID, Path(alias="id", description="Document id")],
    session: SessionDep,
) -> SummaryOut:
    try:
        summary = await summary_service.get_summary(session, document_id)
    except DocumentNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return SummaryOut.model_validate(summary, from_attributes=True)
