"""Benchmark semantic search setups on a hand-labelled wealth-advisor corpus.

Setups: each embedding model with and without query expansion from the synonym glossary
(the same seed as migration 0002, matched the same way as the app: whole words in the query).
With the glossary, a document's score is its best similarity to the query or any synonym.

Metrics (higher is better):
  R@5      recall in the top 5 (relative to min(5, #relevant)), averaged over queries
  MRR      reciprocal rank of the first relevant document
  nDCG@10  binary-relevance nDCG of the top 10
  F1       best F1 over all (query, document) pairs with ONE global similarity threshold,
           noise queries included: how well a threshold separates matches from non-matches,
           which is what the API does
Ranking metrics are reported separately for queries whose concept is in the glossary and for
the others, so the glossary's effect is visible beyond the concepts it was written for.

Only the semantic retriever is measured; the API also runs full-text and lexical retrievers.

Run from the repo root inside the app image:
    python scripts/benchmark_search.py [--openai]
"""

import argparse
import gc
import importlib.util
import math
import os
import sys
from collections.abc import Callable
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from benchmark_dataset import DOCS, GLOSSARY_QUERIES, NOISE_QUERIES, OTHER_QUERIES  # noqa: E402

from app.repositories.synonyms import normalize  # noqa: E402

Embed = Callable[[list[str]], np.ndarray]

LOCAL_MODELS = [
    "sentence-transformers/all-MiniLM-L6-v2",
    "WealthFromAI/empire-embed",
    "philschmid/bge-base-financial-matryoshka",
]
OPENAI_MODELS = ["text-embedding-3-small", "text-embedding-3-large"]


def load_glossary() -> dict[str, list[str]]:
    path = next((ROOT / "migrations" / "versions").glob("0002_*.py"))
    spec = importlib.util.spec_from_file_location("migration_0002", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    glossary: dict[str, list[str]] = module.SYNONYMS
    return glossary


GLOSSARY = load_glossary()


def expand(query: str) -> list[str]:
    padded = f" {normalize(query)} "
    synonyms = {s for term, syns in GLOSSARY.items() if f" {term} " in padded for s in syns}
    return [query, *sorted(synonyms)]


def local_embedder(name: str) -> Embed:
    from sentence_transformers import SentenceTransformer

    model = SentenceTransformer(name, device="cpu")
    return lambda texts: np.asarray(model.encode(texts, normalize_embeddings=True))


def openai_embedder(name: str) -> Embed:
    from openai import OpenAI

    client = OpenAI()

    def embed(texts: list[str]) -> np.ndarray:
        vectors = np.asarray(
            [d.embedding for d in client.embeddings.create(model=name, input=texts).data]
        )
        return vectors / np.linalg.norm(vectors, axis=1, keepdims=True)

    return embed


def ranking_metrics(
    sims: np.ndarray, relevant: set[str], ids: list[str]
) -> tuple[float, float, float]:
    order = [ids[i] for i in np.argsort(-sims)]
    recall5 = len(relevant & set(order[:5])) / min(5, len(relevant))
    mrr = next((1 / (rank + 1) for rank, doc in enumerate(order) if doc in relevant), 0.0)
    dcg = sum(1 / math.log2(rank + 2) for rank, doc in enumerate(order[:10]) if doc in relevant)
    idcg = sum(1 / math.log2(rank + 2) for rank in range(min(10, len(relevant))))
    return recall5, mrr, dcg / idcg


def best_f1(scores: list[float], labels: list[bool]) -> tuple[float, float]:
    pairs = sorted(zip(scores, labels, strict=True), reverse=True)
    total_pos = sum(labels)
    best, best_t, tp = 0.0, 1.0, 0
    for k, (score, label) in enumerate(pairs, 1):
        tp += label
        f1 = 2 * tp / (k + total_pos)
        if f1 > best:
            best, best_t = f1, score
    return best, best_t


def evaluate(embed: Embed, use_glossary: bool) -> dict[str, float]:
    ids = list(DOCS)
    doc_vectors = embed([f"{title}\n{content}" for title, content in DOCS.values()])

    def sims_for(query: str) -> np.ndarray:
        variants = expand(query) if use_glossary else [query]
        return np.asarray((doc_vectors @ embed(variants).T).max(axis=1))

    result: dict[str, float] = {}
    scores: list[float] = []
    labels: list[bool] = []
    for group, queries in (("glossary", GLOSSARY_QUERIES), ("other", OTHER_QUERIES)):
        rows = []
        for query, relevant in queries.items():
            sims = sims_for(query)
            rows.append(ranking_metrics(sims, relevant, ids))
            scores += sims.tolist()
            labels += [doc in relevant for doc in ids]
        r5, mrr, ndcg = (float(np.mean(col)) for col in zip(*rows, strict=True))
        result |= {f"{group}_r5": r5, f"{group}_mrr": mrr, f"{group}_ndcg": ndcg}
    for query in NOISE_QUERIES:
        scores += sims_for(query).tolist()
        labels += [False] * len(ids)
    result["f1"], result["threshold"] = best_f1(scores, labels)
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--openai", action="store_true", help="also benchmark OpenAI embeddings")
    args = parser.parse_args()

    setups: list[tuple[str, Callable[[], Embed]]] = [
        (name.split("/")[-1], lambda name=name: local_embedder(name)) for name in LOCAL_MODELS
    ]
    if args.openai and os.environ.get("OPENAI_API_KEY"):
        setups += [(f"openai {n}", lambda n=n: openai_embedder(n)) for n in OPENAI_MODELS]

    n_docs = len(DOCS)
    n_queries = len(GLOSSARY_QUERIES) + len(OTHER_QUERIES)
    print(
        f"{n_docs} documents, {len(GLOSSARY_QUERIES)} glossary + {len(OTHER_QUERIES)} other "
        f"queries, {len(NOISE_QUERIES)} noise queries ({n_queries} labelled)\n"
    )
    print(
        "| setup | glossary queries R@5 / MRR / nDCG | other queries R@5 / MRR / nDCG "
        "| F1 @ best threshold |"
    )
    print("|---|---|---|---|")
    for name, factory in setups:
        embed = factory()
        for use_glossary in (False, True):
            m = evaluate(embed, use_glossary)
            label = f"{name} + glossary" if use_glossary else name
            print(
                f"| {label} "
                f"| {m['glossary_r5']:.2f} / {m['glossary_mrr']:.2f} / {m['glossary_ndcg']:.2f} "
                f"| {m['other_r5']:.2f} / {m['other_mrr']:.2f} / {m['other_ndcg']:.2f} "
                f"| {m['f1']:.2f} @ {m['threshold']:.2f} |"
            )
        del embed
        gc.collect()


if __name__ == "__main__":
    main()
