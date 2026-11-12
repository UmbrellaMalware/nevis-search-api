"""Data passed between the API and the service layer.

The API turns request schemas into these DTOs and turns DTOs into response schemas; services
never see API schemas and never hand ORM objects back to the API. Validation of user input stays
in the API schemas, so DTOs only describe the shape of the data.
"""

import uuid
from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict

from app.models import SummaryStatus


class _DTO(BaseModel):
    model_config = ConfigDict(frozen=True, from_attributes=True)


# --- Input ----------------------------------------------------------------------------------


class ClientCreateData(_DTO):
    first_name: str
    last_name: str
    email: str
    description: str | None
    social_links: list[str]


class DocumentCreateData(_DTO):
    title: str
    content: str


# --- Output ---------------------------------------------------------------------------------


class ClientDTO(_DTO):
    id: uuid.UUID
    first_name: str
    last_name: str
    email: str
    description: str | None
    social_links: list[str]
    created_at: datetime


class DocumentBriefDTO(_DTO):
    """A document without its (potentially large) content, as returned by search."""

    id: uuid.UUID
    client_id: uuid.UUID
    title: str
    created_at: datetime
    summary_status: SummaryStatus
    summary: str | None


class DocumentDTO(DocumentBriefDTO):
    content: str


class SummaryDTO(_DTO):
    document_id: uuid.UUID
    status: SummaryStatus
    summary: str | None
    error: str | None  # why the summary failed (status = failed)


# --- Search ---------------------------------------------------------------------------------


class MatchType(StrEnum):
    LEXICAL = "lexical"  # substring / fuzzy match on client email, name or description
    SEMANTIC = "semantic"  # Sentence-BERT similarity (optionally via a glossary synonym)
    FULL_TEXT = "full_text"  # Postgres full-text match on document content


class ClientHit(_DTO):
    client: ClientDTO
    score: float  # fused RRF score; higher is better
    matched_by: list[MatchType]


class DocumentHit(_DTO):
    document: DocumentBriefDTO
    snippet: str  # the part of the document that matched
    score: float  # fused RRF score; higher is better
    matched_by: list[MatchType]


type SearchResult = ClientHit | DocumentHit
