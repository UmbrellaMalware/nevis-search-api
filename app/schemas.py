import uuid
from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, StringConstraints, field_validator

from app.models import SummaryStatus
from app.services.dto import MatchType

Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
SocialLink = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=2048)]
Description = Annotated[str, StringConstraints(strip_whitespace=True, max_length=10_000)]

MAX_DOCUMENT_CHARS = 100_000


class ErrorResponse(BaseModel):
    detail: str


class ClientCreate(BaseModel):
    first_name: Name
    last_name: Name
    email: EmailStr
    description: Description | None = None
    social_links: list[SocialLink] = Field(default_factory=list, max_length=50)

    @field_validator("description")
    @classmethod
    def _blank_description_is_none(cls, value: str | None) -> str | None:
        return value or None


class ClientOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    first_name: str
    last_name: str
    email: str
    description: str | None
    social_links: list[str]
    created_at: datetime


class DocumentCreate(BaseModel):
    title: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=500)]
    content: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=MAX_DOCUMENT_CHARS)
    ]


class DocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    client_id: uuid.UUID
    title: str
    content: str
    created_at: datetime
    summary_status: SummaryStatus
    summary: str | None


# --- Search ---------------------------------------------------------------------------------


class DocumentBrief(BaseModel):
    """A document as shown in search results: everything except the (potentially large) content."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    client_id: uuid.UUID
    title: str
    created_at: datetime
    summary_status: SummaryStatus
    summary: str | None


class ClientSearchHit(BaseModel):
    model_config = ConfigDict(from_attributes=True)  # built from app.services.dto.ClientHit

    type: Literal["client"] = "client"
    score: float = Field(description="Relevance (Reciprocal Rank Fusion); higher is better.")
    matched_by: list[MatchType]
    client: ClientOut


class DocumentSearchHit(BaseModel):
    model_config = ConfigDict(from_attributes=True)  # built from app.services.dto.DocumentHit

    type: Literal["document"] = "document"
    score: float = Field(description="Relevance (Reciprocal Rank Fusion); higher is better.")
    matched_by: list[MatchType]
    document: DocumentBrief
    snippet: str = Field(description="The part of the document that matched the query.")


SearchHit = Annotated[ClientSearchHit | DocumentSearchHit, Field(discriminator="type")]
