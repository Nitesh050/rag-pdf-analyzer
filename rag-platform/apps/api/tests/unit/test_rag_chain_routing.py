from langchain_core.documents import Document

from src.generation.intent.router import IntentRouter
from src.generation.prompt_templates import PromptBuilder
from src.generation.rag_chain import RAGChain
from src.generation.summarizer import group_sections


def doc(page, text="text " * 50, **meta):
    return Document(page_content=text, metadata={"page": page, "document_id": "d", **meta})


class FakeStore:
    def __init__(self, chunks):
        self.chunks = chunks
        self.page_requests = []

    def get_pages(self, pages, document_id=None, owner_id=None):
        self.page_requests.append(pages)
        return [c for c in self.chunks if c.metadata["page"] in pages]

    def get_document(self, document_id):
        return self.chunks


class FakeRetrieval:
    def __init__(self):
        self.calls = 0

    def retrieve(self, **kwargs):
        self.calls += 1
        return [doc(99)]


class FakeLLM:
    def generate(self, prompt):
        return "Answer (Source 1, page 42)."


class FakeSummarizer:
    def section_summaries(self, document_id, llm):
        return [doc(1, "summary of part one", page_end=100)]


def chain(chunks):
    rag = RAGChain.__new__(RAGChain)
    rag.vector_store = FakeStore(chunks)
    rag.retrieval_manager = FakeRetrieval()
    rag.llm = FakeLLM()
    rag.router = IntentRouter()
    rag.summarizer = FakeSummarizer()
    return rag


def test_page_question_fetches_the_page_instead_of_searching():
    rag = chain([doc(41), doc(42), doc(43)])

    result = rag.ask("What is on page 42?", document_id="d")

    assert rag.vector_store.page_requests == [[42]]
    assert rag.retrieval_manager.calls == 0
    assert [c.metadata["page"] for c in result["contexts"]] == [42]


def test_missing_page_falls_back_to_search():
    rag = chain([doc(1)])

    rag.ask("What is on page 500?", document_id="d")

    assert rag.retrieval_manager.calls == 1


def test_summary_of_short_document_uses_every_chunk():
    rag = chain([doc(1), doc(2)])

    result = rag.ask("Summarize this document", document_id="d")

    assert [c.metadata["page"] for c in result["contexts"]] == [1, 2]


def test_summary_of_long_document_uses_section_summaries():
    rag = chain([doc(p, "word " * 400) for p in range(1, 101)])

    result = rag.ask("Summarize this document", document_id="d")

    assert [c.page_content for c in result["contexts"]] == ["summary of part one"]


def test_group_sections_respects_size_limit():
    chunks = [doc(p, "x" * 400) for p in range(1, 6)]

    assert [len(s) for s in group_sections(chunks, max_chars=1000)] == [2, 2, 1]


def test_section_label_shows_page_range():
    label = PromptBuilder._format_chunk(0, doc(10, "s", page_end=25, source="book.pdf"))

    assert label.startswith("[Source 1: book.pdf, pages 10-25]")


from src.generation.summarizer import DocumentSummarizer


def test_document_just_over_budget_still_gets_several_sections():
    summarizer = DocumentSummarizer(vector_store=None, cache_dir="/tmp/unused")
    medium = [doc(p, "x" * 1000) for p in range(15)]      # 15k chars
    large = [doc(p, "x" * 1000) for p in range(300)]      # 300k chars

    assert len(group_sections(medium, summarizer._section_chars(medium))) >= 3
    assert summarizer._section_chars(large) == DocumentSummarizer.SECTION_CHARS
