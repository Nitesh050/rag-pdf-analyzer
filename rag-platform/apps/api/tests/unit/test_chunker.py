from langchain_core.documents import Document

from ingestion.chunking.validator import ChunkValidator

BODY = "Sentence about inputs and weights in the network. " * 4


def chunk(text, page=1):
    return Document(page_content=text, metadata={"source": "book.pdf", "page": page})


def test_heading_is_merged_into_following_chunk():
    result = ChunkValidator().validate([chunk("## Preparing Data"), chunk(BODY)])

    assert len(result) == 1
    assert result[0].page_content.startswith("## Preparing Data\n\n")


def test_short_tail_is_merged_into_previous_chunk():
    result = ChunkValidator().validate([chunk(BODY), chunk("A short closing line.")])

    assert len(result) == 1
    assert result[0].page_content.endswith("A short closing line.")


def test_short_chunk_is_not_merged_across_pages():
    result = ChunkValidator().validate([chunk("## THANK YOU", page=24), chunk(BODY, page=25)])

    assert [c.metadata["page"] for c in result] == [25]


def test_overlapping_short_text_is_not_duplicated():
    result = ChunkValidator().validate([chunk("## Prologue"), chunk("## Prologue\n\n" + BODY)])

    assert result[0].page_content.count("## Prologue") == 1
