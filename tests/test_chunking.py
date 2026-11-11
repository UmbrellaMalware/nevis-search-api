import pytest

from app.services.chunking import chunk_text


def _words(n: int) -> str:
    return " ".join(f"w{i}" for i in range(n))


def test_empty_and_blank_text_produce_no_chunks() -> None:
    assert chunk_text("") == []
    assert chunk_text("   \n\t ") == []


def test_short_text_is_a_single_normalised_chunk() -> None:
    assert chunk_text("  Utility   bill\nfor  March ") == ["Utility bill for March"]


def test_text_of_exactly_max_words_is_one_chunk() -> None:
    assert len(chunk_text(_words(10), max_words=10, overlap_words=2)) == 1


def test_long_text_is_split_with_overlap() -> None:
    chunks = chunk_text(_words(25), max_words=10, overlap_words=3)

    assert chunks == [
        "w0 w1 w2 w3 w4 w5 w6 w7 w8 w9",
        "w7 w8 w9 w10 w11 w12 w13 w14 w15 w16",
        "w14 w15 w16 w17 w18 w19 w20 w21 w22 w23",
        "w21 w22 w23 w24",
    ]


def test_every_word_is_covered_and_chunks_respect_limit() -> None:
    chunks = chunk_text(_words(1000), max_words=150, overlap_words=30)

    covered = {word for chunk in chunks for word in chunk.split()}
    assert covered == set(_words(1000).split())
    assert all(len(chunk.split()) <= 150 for chunk in chunks)


@pytest.mark.parametrize(("max_words", "overlap"), [(0, 0), (10, 10), (10, -1)])
def test_invalid_parameters_are_rejected(max_words: int, overlap: int) -> None:
    with pytest.raises(ValueError):
        chunk_text("some text", max_words=max_words, overlap_words=overlap)
