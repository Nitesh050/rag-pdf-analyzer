from langchain_core.documents import Document

from generation.citation_mapper import cited_documents

CONTEXTS = [Document(page_content=f"chunk {i}", metadata={"page": i}) for i in (10, 20, 30)]


def test_returns_cited_contexts_in_order_of_first_mention():
    answer = "Yes (Source 3, page 30). Also (Source 1, page 10) and again Source 3."

    assert [d.metadata["page"] for d in cited_documents(answer, CONTEXTS)] == [30, 10]


def test_ignores_out_of_range_and_missing_citations():
    assert cited_documents("See Source 7.", CONTEXTS) == []
    assert cited_documents("No citations here.", CONTEXTS) == []
