"""Compare semantic-search quality of embedding setups on a small KYC-style corpus.

Modes:
  local          - all-MiniLM-L6-v2, query embedded as is
  local+glossary - all-MiniLM-L6-v2, query + glossary synonyms, max similarity per document
  openai-small   - OpenAI text-embedding-3-small (only if OPENAI_API_KEY is set)
  openai-large   - OpenAI text-embedding-3-large (only if OPENAI_API_KEY is set)

For every query the script reports the rank of each relevant document (1 = best) and the gap
between the weakest relevant and the strongest irrelevant document: a positive gap means a single
similarity threshold can separate them. Noise queries (nothing relevant) show the highest
similarity they reach, which is what the threshold has to stay above.

Run inside the app image:  python scripts/benchmark_search.py
"""

import os
from collections.abc import Callable

import numpy as np
from sentence_transformers import SentenceTransformer

DOCS = {
    "utility": "Utility bill\nElectricity utility bill for March 2026 issued to John Doe, "
    "12 Baker Street, London.",
    "bank_stmt": "Bank statement\nMonthly bank statement showing account balance and "
    "transactions for March.",
    "lease": "Tenancy agreement\nRental agreement for flat at 5 High Road, signed by tenant "
    "and landlord.",
    "passport": "Passport copy\nScanned copy of passport, nationality British, date of birth "
    "01.02.1980.",
    "portfolio": "Portfolio review\nQuarterly review of equity and bond allocation, "
    "rebalancing recommendations.",
    "tax": "Tax return\nAnnual income tax return with capital gains from share sales.",
    "payslip": "Payslip\nMonthly salary payslip from Acme Ltd, gross pay and deductions.",
}

# query -> relevant documents
QUERIES = {
    "address proof": {"utility", "bank_stmt", "lease"},
    "identity document": {"passport"},
    "source of funds": {"payslip", "bank_stmt"},
    "investment strategy": {"portfolio"},
    "taxes": {"tax"},
}
NOISE = ["weather forecast", "cooking recipe", "football match"]

# Same entries as the search_synonyms seed (migration 0002) for the queries above.
GLOSSARY = {
    "address proof": ["utility bill", "bank statement", "tenancy agreement", "council tax bill"],
    "identity document": ["passport", "driving licence", "national identity card"],
    "source of funds": ["payslip", "bank statement", "sale agreement", "inheritance"],
}

Embed = Callable[[list[str]], np.ndarray]


def local_embedder() -> Embed:
    model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2", device="cpu")
    return lambda texts: np.asarray(model.encode(texts, normalize_embeddings=True))


def openai_embedder(model: str) -> Embed:
    from openai import OpenAI

    client = OpenAI()

    def embed(texts: list[str]) -> np.ndarray:
        data = client.embeddings.create(model=model, input=texts).data
        vectors = np.asarray([d.embedding for d in data])
        return vectors / np.linalg.norm(vectors, axis=1, keepdims=True)

    return embed


def similarities(embed: Embed, query: str, doc_vectors: np.ndarray, glossary: bool) -> np.ndarray:
    variants = [query, *GLOSSARY.get(query, [])] if glossary else [query]
    return np.asarray((doc_vectors @ embed(variants).T).max(axis=1))


def run(name: str, embed: Embed, glossary: bool) -> None:
    names = list(DOCS)
    doc_vectors = embed(list(DOCS.values()))
    print(f"\n### {name}\n")
    print("| query | relevant: rank (similarity) | best irrelevant | gap |")
    print("|---|---|---|---|")
    for query, relevant in QUERIES.items():
        sims = similarities(embed, query, doc_vectors, glossary)
        order = list(np.argsort(-sims))
        rel = sorted((order.index(names.index(r)) + 1, r) for r in relevant)
        rel_text = ", ".join(f"{r} #{rank} ({sims[names.index(r)]:.2f})" for rank, r in rel)
        irrelevant = max(
            (sims[i], names[i]) for i in range(len(names)) if names[i] not in relevant
        )
        gap = min(sims[names.index(r)] for r in relevant) - irrelevant[0]
        print(
            f"| {query} | {rel_text} | {irrelevant[1]} ({irrelevant[0]:.2f}) | "
            f"{gap:+.2f} {'ok' if gap > 0 else 'FAIL'} |"
        )
    noise = max(float(similarities(embed, q, doc_vectors, glossary).max()) for q in NOISE)
    print(f"\nHighest similarity reached by a noise query: {noise:.2f}")


def main() -> None:
    local = local_embedder()
    run("local (all-MiniLM-L6-v2)", local, glossary=False)
    run("local + glossary", local, glossary=True)
    if os.environ.get("OPENAI_API_KEY"):
        run("openai text-embedding-3-small", openai_embedder("text-embedding-3-small"), False)
        run("openai text-embedding-3-large", openai_embedder("text-embedding-3-large"), False)
    else:
        print("\n(OPENAI_API_KEY not set: OpenAI modes skipped)")


if __name__ == "__main__":
    main()
