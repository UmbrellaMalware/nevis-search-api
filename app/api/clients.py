import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Path, status

from app.api.deps import EmbedderDep, SessionDep, require_api_key
from app.exceptions import (
    ClientNotFoundError,
    DocumentAlreadyExistsError,
    EmailAlreadyExistsError,
)
from app.schemas import ClientCreate, ClientOut, DocumentCreate, DocumentOut, ErrorResponse
from app.services import clients as client_service
from app.services import documents as document_service
from app.services.dto import ClientCreateData, DocumentCreateData

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
) -> ClientOut:
    try:
        client = await client_service.create_client(
            session,
            embedder,
            ClientCreateData(
                first_name=payload.first_name,
                last_name=payload.last_name,
                email=str(payload.email),
                description=payload.description,
                social_links=payload.social_links,
            ),
        )
    except EmailAlreadyExistsError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return ClientOut.model_validate(client, from_attributes=True)


@router.post(
    "/{id}/documents",
    status_code=status.HTTP_201_CREATED,
    response_model=DocumentOut,
    responses={
        **_AUTH_ERROR,
        404: {"model": ErrorResponse, "description": "Client not found"},
        409: {
            "model": ErrorResponse,
            "description": "The client already has a document with this content; "
            "`detail` contains the existing document's id",
        },
    },
)
async def create_document(
    client_id: Annotated[uuid.UUID, Path(alias="id", description="Client id")],
    payload: DocumentCreate,
    session: SessionDep,
    embedder: EmbedderDep,
) -> DocumentOut:
    try:
        document = await document_service.create_document(
            session,
            embedder,
            client_id,
            DocumentCreateData(title=payload.title, content=payload.content),
        )
    except ClientNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except DocumentAlreadyExistsError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return DocumentOut.model_validate(document, from_attributes=True)
