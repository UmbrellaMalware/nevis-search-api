"""Split document text into overlapping word windows for embedding.

all-MiniLM-L6-v2 truncates input at 256 word-piece tokens. 150 words is ~200 tokens for
typical English text, which leaves room for the document title that is prepended to each chunk.
The overlap keeps a phrase that straddles a boundary intact in at least one chunk.
"""

DEFAULT_MAX_WORDS = 150
DEFAULT_OVERLAP_WORDS = 30


def chunk_text(
    text: str,
    max_words: int = DEFAULT_MAX_WORDS,
    overlap_words: int = DEFAULT_OVERLAP_WORDS,
) -> list[str]:
    if max_words <= 0:
        raise ValueError("max_words must be positive")
    if not 0 <= overlap_words < max_words:
        raise ValueError("overlap_words must be in [0, max_words)")

    words = text.split()
    if not words:
        return []

    step = max_words - overlap_words
    chunks: list[str] = []
    for start in range(0, len(words), step):
        chunks.append(" ".join(words[start : start + max_words]))
        if start + max_words >= len(words):
            break
    return chunks
