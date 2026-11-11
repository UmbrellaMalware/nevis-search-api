import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Path, status

from app.api.deps import EmbedderDep, SessionDep, require_api_key
from app.models import Client, Document
from app.schemas import ClientCreate, ClientOut, DocumentCreate, DocumentOut, ErrorResponse
from app.services import clients as client_service
from app.services import documents as document_service

router = APIRouter(prefix="/clients", tags=["clients"], dependencies=[Depends(require_api_key)])

_AUTH_ERROR: dict[int | str, dict[str, Any]] = {
    401: {"model": ErrorResponse, "description": "Invalid or missing API key"}
}


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=ClientOut,
    responses={
        **_AUTH_ERROR,
        409: {"model": ErrorResponse, "description": "Email already in use"},
    },
)
async def create_client(
    payload: ClientCreate, session: SessionDep, embedder: EmbedderDep
) -> Client:
    try:
        return await client_service.create_client(session, embedder, payload)
    except client_service.EmailAlreadyExistsError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.post(
    "/{id}/documents",
    status_code=status.HTTP_201_CREATED,
    response_model=DocumentOut,
    responses={
        **_AUTH_ERROR,
        404: {"model": ErrorResponse, "description": "Client not found"},
    },
)
async def create_document(
    client_id: Annotated[uuid.UUID, Path(alias="id", description="Client id")],
    payload: DocumentCreate,
    session: SessionDep,
    embedder: EmbedderDep,
) -> Document:
    try:
        return await document_service.create_document(session, embedder, client_id, payload)
    except document_service.ClientNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
