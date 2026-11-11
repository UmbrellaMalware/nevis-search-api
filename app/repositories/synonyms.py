import re

from sqlalchemy import Text, literal, literal_column, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import SearchSynonym


def normalize(text: str) -> str:
    """Lowercase words separated by single spaces (the format terms are stored in)."""
    return " ".join(re.findall(r"\w+", text.lower()))


class SynonymRepository:
    """Reads the query-expansion glossary (table `search_synonyms`)."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def expand(self, query: str) -> list[str]:
        """Synonyms of every glossary term the query contains as whole words.

        "Proof of address?" contains the term "proof of address" -> ["utility bill", ...].
        Whole-word matching avoids "photo id" matching "photo identification" partially, etc.
        """
        normalized = normalize(query)
        if not normalized:
            return []
        padded_query = literal(f" {normalized} ", Text)
        padded_term = (
            literal_column("' '").op("||")(SearchSynonym.term).op("||")(literal_column("' '"))
        )
        rows = await self._session.scalars(
            select(SearchSynonym.synonym)
            .where(padded_query.contains(padded_term, autoescape=False))
            .distinct()
            .order_by(SearchSynonym.synonym)
        )
        return [s for s in rows if s != normalized]
