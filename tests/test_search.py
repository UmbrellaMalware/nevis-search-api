from typing import Any

import pytest
from httpx import AsyncClient

CLIENTS = [
    {
        "first_name": "John",
        "last_name": "Doe",
        "email": "john.doe@neviswealth.com",
        "description": "Retired engineer focused on capital preservation.",
    },
    {"first_name": "Maria", "last_name": "Garcia", "email": "maria@example.org"},
]

# title -> content, attached to the first client
DOCUMENTS = {
    "Utility bill": "Electricity utility bill for March 2026 issued to John Doe, 12 Baker Street.",
    "Passport copy": "Scanned copy of passport, nationality British, date of birth 01.02.1980.",
    "Portfolio review": "Quarterly review of equity and bond allocation with rebalancing advice.",
    "Wire instructions": "Transfer funds to IBAN DE89370400440532013000 before the end of month.",
}


@pytest.fixture
async def corpus(client: AsyncClient) -> dict[str, str]:
    """Creates the clients and documents above; returns {email or title: id}."""
    ids: dict[str, str] = {}
    for payload in CLIENTS:
        response = await client.post("/clients", json=payload)
        assert response.status_code == 201
        ids[payload["email"]] = response.json()["id"]
    owner = ids[CLIENTS[0]["email"]]
    for title, content in DOCUMENTS.items():
        response = await client.post(
            f"/clients/{owner}/documents", json={"title": title, "content": content}
        )
        assert response.status_code == 201
        ids[title] = response.json()["id"]
    return ids


async def _search(client: AsyncClient, q: str) -> list[dict[str, Any]]:
    response = await client.get("/search", params={"q": q})
    assert response.status_code == 200, response.text
    hits: list[dict[str, Any]] = response.json()
    return hits


def _titles(hits: list[dict[str, Any]]) -> list[str]:
    return [h["document"]["title"] for h in hits if h["type"] == "document"]


def _emails(hits: list[dict[str, Any]]) -> list[str]:
    return [h["client"]["email"] for h in hits if h["type"] == "client"]


# --- Clients -----------------------------------------------------------------------------------


async def test_company_name_finds_client_by_email_domain(
    client: AsyncClient, corpus: dict[str, str]
) -> None:
    hits = await _search(client, "NevisWealth")

    assert hits[0]["type"] == "client"
    assert hits[0]["client"]["email"] == "john.doe@neviswealth.com"
    assert "lexical" in hits[0]["matched_by"]


async def test_typo_still_finds_client(client: AsyncClient, corpus: dict[str, str]) -> None:
    assert "john.doe@neviswealth.com" in _emails(await _search(client, "neviswelth"))


async def test_full_name_finds_client(client: AsyncClient, corpus: dict[str, str]) -> None:
    assert _emails(await _search(client, "maria garcia")) == ["maria@example.org"]


async def test_like_wildcards_in_query_are_literal(
    client: AsyncClient, corpus: dict[str, str]
) -> None:
    # "%" must not act as a LIKE wildcard that matches every client.
    assert _emails(await _search(client, "%%")) == []


# --- Documents ---------------------------------------------------------------------------------


async def test_address_proof_finds_utility_bill(
    client: AsyncClient, corpus: dict[str, str]
) -> None:
    titles = _titles(await _search(client, "address proof"))

    assert titles[0] == "Utility bill"
    assert "Portfolio review" not in titles


async def test_semantic_match_without_shared_words(
    client: AsyncClient, corpus: dict[str, str]
) -> None:
    titles = _titles(await _search(client, "investment strategy"))

    assert titles[0] == "Portfolio review"


async def test_exact_identifier_is_found_by_full_text(
    client: AsyncClient, corpus: dict[str, str]
) -> None:
    hits = await _search(client, "DE89370400440532013000")
    documents = [h for h in hits if h["type"] == "document"]

    assert documents[0]["document"]["title"] == "Wire instructions"
    assert "full_text" in documents[0]["matched_by"]


async def test_document_hit_shape(client: AsyncClient, corpus: dict[str, str]) -> None:
    hit = next(h for h in await _search(client, "utility bill") if h["type"] == "document")

    assert hit["document"]["id"] == corpus["Utility bill"]
    assert hit["document"]["client_id"] == corpus["john.doe@neviswealth.com"]
    assert hit["document"]["summary_status"] == "pending"
    assert "content" not in hit["document"]
    assert "utility bill" in hit["snippet"].lower()
    assert hit["score"] > 0


async def test_document_found_by_two_retrievers_appears_once(
    client: AsyncClient, corpus: dict[str, str]
) -> None:
    hits = await _search(client, "utility bill")
    utility = [h for h in hits if h.get("document", {}).get("title") == "Utility bill"]

    assert len(utility) == 1
    assert set(utility[0]["matched_by"]) == {"semantic", "full_text"}


# --- General -----------------------------------------------------------------------------------


async def test_unrelated_query_returns_nothing(client: AsyncClient, corpus: dict[str, str]) -> None:
    assert await _search(client, "weather forecast") == []


async def test_results_are_sorted_by_score(client: AsyncClient, corpus: dict[str, str]) -> None:
    scores = [h["score"] for h in await _search(client, "john utility bill")]

    assert scores == sorted(scores, reverse=True)


async def test_empty_database_returns_empty_list(client: AsyncClient) -> None:
    assert await _search(client, "anything") == []


@pytest.mark.parametrize("params", [{}, {"q": ""}, {"q": "   "}, {"q": "x" * 501}])
async def test_invalid_query_returns_422(client: AsyncClient, params: dict[str, str]) -> None:
    response = await client.get("/search", params=params)

    assert response.status_code == 422
