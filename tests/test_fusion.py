import pytest

from app.services.fusion import reciprocal_rank_fusion


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


def test_keeps_first_lists_version_of_an_item() -> None:
    fused = reciprocal_rank_fusion(
        [("a", [("doc", "first snippet")]), ("b", [("doc", "second snippet")])],
        key=lambda pair: pair[0],
    )
    assert [f.item for f in fused] == [("doc", "first snippet")]


def test_empty_lists() -> None:
    assert reciprocal_rank_fusion([("a", []), ("b", [])], key=str) == []
