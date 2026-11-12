from collections.abc import Awaitable, Callable
from typing import Any

type Hits = list[dict[str, Any]]
type Search = Callable[[str], Awaitable[Hits]]  # the `search` fixture


def titles(hits: Hits) -> list[str]:
    """Titles of the document hits, in result order."""
    return [h["document"]["title"] for h in hits if h["type"] == "document"]


def emails(hits: Hits) -> list[str]:
    """Emails of the client hits, in result order."""
    return [h["client"]["email"] for h in hits if h["type"] == "client"]
