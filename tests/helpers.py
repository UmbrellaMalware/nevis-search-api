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


class FakeSummarizer:
    """Stands in for OpenAI: returns a canned summary and records what it was asked."""

    def __init__(self, summary: str = "A short summary.") -> None:
        self.summary = summary
        self.calls: list[tuple[str, str]] = []

    async def summarize(self, title: str, content: str) -> str:
        self.calls.append((title, content))
        return self.summary


class FailingSummarizer:
    """Stands in for OpenAI when the API call fails."""

    async def summarize(self, title: str, content: str) -> str:
        raise RuntimeError("OpenAI is unavailable")
