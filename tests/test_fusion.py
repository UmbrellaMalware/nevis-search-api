from dataclasses import dataclass

import pytest

from app.services.fusion import reciprocal_rank_fusion


@dataclass(frozen=True)
class Match:
    document: str
    snippet: str


def test_item_found_by_several_lists_ranks_first() -> None:
    fused = reciprocal_rank_fusion(
        [("semantic", ["utility_bill", "passport"]), ("full_text", ["passport"])],
        key=str,
    )

    assert [(f.item, f.sources) for f in fused] == [
        ("passport", ("semantic", "full_text")),
        ("utility_bill", ("semantic",)),
    ]
    assert fused[0].score == pytest.approx(1 / 62 + 1 / 61)
    assert fused[1].score == pytest.approx(1 / 61)


def test_same_document_from_two_lists_keeps_the_first_lists_snippet() -> None:
    # Both retrievers found the utility bill, each via a different chunk of it.
    semantic = [Match("utility_bill", "Electricity bill for 12 Baker Street")]
    full_text = [Match("utility_bill", "Payment due by 31 March")]

    fused = reciprocal_rank_fusion(
        [("semantic", semantic), ("full_text", full_text)],
        key=lambda match: match.document,  # same document = same result, whatever the snippet
    )

    assert len(fused) == 1
    assert fused[0].item.snippet == "Electricity bill for 12 Baker Street"


def test_empty_lists() -> None:
    assert reciprocal_rank_fusion([("a", []), ("b", [])], key=str) == []
