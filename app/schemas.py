import uuid
from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, EmailStr, Field, StringConstraints, field_validator

from app.models import SummaryStatus

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
