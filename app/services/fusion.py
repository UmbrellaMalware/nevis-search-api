"""Reciprocal Rank Fusion (RRF): merge ranked lists whose scores are not comparable.

Each list gives an item 1 / (k + rank) points (rank starts at 1); an item's fused score is the
sum over all lists that contain it. Only ranks are used, so lists scored with trigram
similarity, cosine similarity and ts_rank can be merged without normalising their scores.

Example with k = 60:

    semantic:  [utility_bill, passport]
    full_text: [passport]

    passport      1/62 + 1/61 = 0.0325   (found by both lists)
    utility_bill  1/61        = 0.0164
"""

from collections.abc import Callable, Hashable, Iterable, Sequence
from dataclasses import dataclass

RRF_K = 60  # the constant from the original RRF paper; damps the weight of the very top ranks


@dataclass(frozen=True, slots=True)
class Fused[T, S]:
    item: T  # the item as returned by the first list that contained it
    score: float
    sources: tuple[S, ...]  # labels of the lists that contained the item, in list order


def reciprocal_rank_fusion[T, S](
    ranked_lists: Iterable[tuple[S, Sequence[T]]],
    key: Callable[[T], Hashable],
    *,
    k: int = RRF_K,
) -> list[Fused[T, S]]:
    """Merge `(label, items best first)` lists into one list, highest fused score first.

    Items are identified by `key`, so the same client or document coming from two lists counts
    once; the first list's version of the item is kept (ties keep first-seen order).
    """
    items: dict[Hashable, T] = {}
    scores: dict[Hashable, float] = {}
    sources: dict[Hashable, list[S]] = {}
    for label, ranked in ranked_lists:
        for rank, item in enumerate(ranked, 1):
            item_key = key(item)
            items.setdefault(item_key, item)
            scores[item_key] = scores.get(item_key, 0.0) + 1 / (k + rank)
            sources.setdefault(item_key, []).append(label)
    ordered = sorted(scores, key=scores.__getitem__, reverse=True)
    return [Fused(items[i], scores[i], tuple(sources[i])) for i in ordered]
