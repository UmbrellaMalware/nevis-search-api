from collections.abc import AsyncIterator

import pytest
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from app.repositories.synonyms import SynonymRepository, normalize


@pytest.fixture
async def synonyms(db: AsyncEngine) -> AsyncIterator[SynonymRepository]:
    async with AsyncSession(db) as session:
        yield SynonymRepository(session)


def test_normalize() -> None:
    assert normalize("  Proof-of   ADDRESS?! ") == "proof of address"
    assert normalize("???") == ""


@pytest.mark.parametrize("query", ["address proof", "Address Proof", "client address proof pdf"])
async def test_glossary_term_in_query_expands(synonyms: SynonymRepository, query: str) -> None:
    expansions = await synonyms.expand(query)

    assert "utility bill" in expansions
    assert "bank statement" in expansions


async def test_matches_whole_words_only(synonyms: SynonymRepository) -> None:
    # "photo id" is a term; "photo identification" must not trigger it via a partial word.
    assert await synonyms.expand("photo identification") == []
    assert "passport" in await synonyms.expand("photo id")


async def test_unknown_query_has_no_expansions(synonyms: SynonymRepository) -> None:
    assert await synonyms.expand("quarterly portfolio review") == []
    assert await synonyms.expand("?!") == []
