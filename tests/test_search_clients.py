"""/search finding clients: by email, name or description, with typos."""

import pytest

from tests.helpers import Search, emails

pytestmark = pytest.mark.usefixtures("corpus")


async def test_company_name_finds_client_by_email_domain(search: Search) -> None:
    hits = await search("NevisWealth")

    assert hits[0]["type"] == "client"
    assert hits[0]["client"]["email"] == "john.doe@neviswealth.com"
    assert "lexical" in hits[0]["matched_by"]


async def test_typo_still_finds_client(search: Search) -> None:
    assert "john.doe@neviswealth.com" in emails(await search("neviswelth"))


async def test_full_name_finds_client(search: Search) -> None:
    assert emails(await search("maria garcia")) == ["maria@example.org"]


async def test_like_wildcards_in_query_are_literal(search: Search) -> None:
    # "%" must not act as a LIKE wildcard that matches every client.
    assert emails(await search("%%")) == []
