from functools import lru_cache
from typing import cast

import anyio
import numpy as np
from sentence_transformers import SentenceTransformer


class Embedder:
    """Thin async wrapper around a Sentence-BERT model.

    Encoding is CPU-bound, so it runs in a worker thread to keep the event loop free.
    A capacity limiter of 1 serialises calls: torch already uses all cores for one batch,
    and parallel batches would only fight over them.
    """

    def __init__(self, model_name: str, revision: str | None = None) -> None:
        self._model = SentenceTransformer(model_name, revision=revision, device="cpu")
        self._limiter = anyio.CapacityLimiter(1)

    @property
    def dimension(self) -> int:
        dim = self._model.get_sentence_embedding_dimension()
        assert dim is not None
        return int(dim)

    def embed_sync(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        vectors = self._model.encode(
            texts, batch_size=32, normalize_embeddings=True, convert_to_numpy=True
        )
        return cast(list[list[float]], np.asarray(vectors, dtype=np.float32).tolist())

    async def embed(self, texts: list[str]) -> list[list[float]]:
        return await anyio.to_thread.run_sync(self.embed_sync, texts, limiter=self._limiter)


@lru_cache
def load_embedder(model_name: str, revision: str | None = None) -> Embedder:
    """Load each model once per process (loading takes seconds and ~100 MB of RAM)."""
    return Embedder(model_name, revision)
