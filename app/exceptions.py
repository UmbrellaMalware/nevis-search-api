"""Domain exceptions raised by the service layer and mapped to HTTP errors by the API layer."""

import uuid


class AppError(Exception):
    """Base class for all application (domain) errors."""


class EmailAlreadyExistsError(AppError):
    def __init__(self, email: str) -> None:
        super().__init__(f"A client with email '{email}' already exists")


class ClientNotFoundError(AppError):
    def __init__(self, client_id: uuid.UUID) -> None:
        super().__init__(f"Client '{client_id}' not found")


class DocumentNotFoundError(AppError):
    def __init__(self, document_id: uuid.UUID) -> None:
        super().__init__(f"Document '{document_id}' not found")


class DocumentAlreadyExistsError(AppError):
    def __init__(self, client_id: uuid.UUID, document_id: uuid.UUID) -> None:
        self.document_id = document_id
        super().__init__(
            f"Client '{client_id}' already has a document with this content: '{document_id}'"
        )
