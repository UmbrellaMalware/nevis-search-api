"""/search finding documents: by meaning (with the glossary) and by exact terms."""

from tests.helpers import Search, titles


async def test_address_proof_finds_utility_bill(search: Search, corpus: dict[str, str]) -> None:
    found = titles(await search("address proof"))

    assert found[0] == "Utility bill"
    assert "Portfolio review" not in found


async def test_semantic_match_without_shared_words(search: Search, corpus: dict[str, str]) -> None:
    assert titles(await search("investment strategy"))[0] == "Portfolio review"


async def test_exact_identifier_is_found_by_full_text(
    search: Search, corpus: dict[str, str]
) -> None:
    documents = [h for h in await search("DE89370400440532013000") if h["type"] == "document"]

    assert documents[0]["document"]["title"] == "Wire instructions"
    assert "full_text" in documents[0]["matched_by"]


async def test_document_hit_shape(search: Search, corpus: dict[str, str]) -> None:
    hit = next(h for h in await search("utility bill") if h["type"] == "document")

    assert hit["document"]["id"] == corpus["Utility bill"]
    assert hit["document"]["client_id"] == corpus["john.doe@neviswealth.com"]
    assert hit["document"]["summary_status"] == "not_requested"
    assert "content" not in hit["document"]
    assert "utility bill" in hit["snippet"].lower()
    assert hit["score"] > 0


async def test_document_found_by_two_retrievers_appears_once(
    search: Search, corpus: dict[str, str]
) -> None:
    hits = await search("utility bill")
    utility = [h for h in hits if h.get("document", {}).get("title") == "Utility bill"]

    assert len(utility) == 1
    assert set(utility[0]["matched_by"]) == {"semantic", "full_text"}
