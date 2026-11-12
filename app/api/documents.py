import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Path, Response, status

from app.api.deps import SessionDep, require_api_key
from app.exceptions import DocumentNotFoundError
from app.models import SummaryStatus
from app.schemas import ErrorResponse, SummaryOut
from app.services import summaries as summary_service

router = APIRouter(prefix="/documents", tags=["documents"], dependencies=[Depends(require_api_key)])

_ERRORS: dict[int | str, dict[str, Any]] = {
    401: {"model": ErrorResponse, "description": "Invalid or missing API key"},
    404: {"model": ErrorResponse, "description": "Document not found"},
}

DocumentId = Annotated[uuid.UUID, Path(alias="id", description="Document id")]


@router.post(
    "/{id}/summary",
    response_model=SummaryOut,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Request a document's summary",
    description=(
        "Queues the summary; it is generated in the background, usually within seconds. "
        "Then poll `GET /documents/{id}/summary` until `status` is `ready` or `failed`. "
        "Requesting again is safe: a ready summary is returned as is (`200`), a failed one is "
        "tried again."
    ),
    responses={**_ERRORS, 200: {"model": SummaryOut, "description": "Summary already ready"}},
)
async def request_summary(
    document_id: DocumentId, session: SessionDep, response: Response
) -> SummaryOut:
    try:
        summary = await summary_service.request_summary(session, document_id)
    except DocumentNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    if summary.status == SummaryStatus.READY:
        response.status_code = status.HTTP_200_OK
    return SummaryOut.model_validate(summary, from_attributes=True)


@router.get(
    "/{id}/summary",
    response_model=SummaryOut,
    summary="Get a document's summary",
    description=(
        "Current state of the summary: `not_requested` until `POST /documents/{id}/summary`, "
        "then `pending`, then `ready` or `failed`."
    ),
    responses=_ERRORS,
)
async def get_summary(document_id: DocumentId, session: SessionDep) -> SummaryOut:
    try:
        summary = await summary_service.get_summary(session, document_id)
    except DocumentNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return SummaryOut.model_validate(summary, from_attributes=True)
