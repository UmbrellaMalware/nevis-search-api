from collections.abc import Hashable


class BestScores[K: Hashable, V]:
    """Keeps, per key, the value with the highest score; used to collapse many rows per item.

    A document has many chunks and a query has several variants (query + glossary synonyms), so
    one document comes back in many rows; it should appear once, with its best row:

        offer(doc_1, "chunk A", 0.41)
        offer(doc_1, "chunk B", 0.63)   -> doc_1 now keeps "chunk B", 0.63
        offer(doc_1, "chunk C", 0.50)   -> ignored, 0.50 < 0.63
        offer(doc_2, "chunk D", 0.55)
        top(10) -> [(doc_1, "chunk B", 0.63), (doc_2, "chunk D", 0.55)]

    On equal scores the first value offered stays.
    """

    def __init__(self) -> None:
        self._best: dict[K, tuple[V, float]] = {}

    def offer(self, key: K, value: V, score: float) -> None:
        """Keep `value` if `key` is new or `score` beats the score kept so far."""
        current = self._best.get(key)
        if current is None or score > current[1]:
            self._best[key] = (value, score)

    def top(self, limit: int) -> list[tuple[K, V, float]]:
        """The `limit` keys with the highest score, best first."""
        ranked = sorted(self._best.items(), key=lambda item: item[1][1], reverse=True)
        return [(key, value, score) for key, (value, score) in ranked[:limit]]
