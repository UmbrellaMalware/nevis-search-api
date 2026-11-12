"""General /search behaviour: validation, ordering, empty results."""

import pytest
from httpx import AsyncClient

from tests.helpers import Search


@pytest.mark.usefixtures("corpus")
async def test_unrelated_query_returns_nothing(search: Search) -> None:
    assert await search("weather forecast") == []


@pytest.mark.usefixtures("corpus")
async def test_results_are_sorted_by_score(search: Search) -> None:
    scores = [h["score"] for h in await search("john utility bill")]

    assert scores == sorted(scores, reverse=True)


async def test_empty_database_returns_empty_list(search: Search) -> None:
    assert await search("anything") == []


@pytest.mark.parametrize("params", [{}, {"q": ""}, {"q": "   "}, {"q": "x" * 501}])
async def test_invalid_query_returns_422(client: AsyncClient, params: dict[str, str]) -> None:
    response = await client.get("/search", params=params)

    assert response.status_code == 422
