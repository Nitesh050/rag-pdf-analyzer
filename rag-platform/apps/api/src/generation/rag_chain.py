from .citation_mapper import cited_documents
from .ollama_client import OllamaClient
from .page_refs import parse_page_refs
from .prompt_templates import PromptBuilder

from .intent.router import IntentRouter
from .intent.intent import Intent

from ..dependencies import get_retrieval_manager
from ..retrieval.retrieval_manager import RetrievalManager


class RAGChain:
    """
    Orchestrates the complete Retrieval-Augmented Generation pipeline:
    intent routing -> hybrid retrieval (semantic + BM25 + RRF) ->
    cross-encoder reranking -> prompt building -> generation.
    """

    def __init__(self, retrieval_manager: RetrievalManager | None = None):
        self.retrieval_manager = retrieval_manager or get_retrieval_manager()
        self.vector_store = self.retrieval_manager.vector_store
        self.llm = OllamaClient()
        self.router = IntentRouter()

    def ask(self, question: str, k: int = 5, document_id: str | None = None) -> dict:

        # -------------------------------------------------
        # Step 1 : Detect User Intent
        # -------------------------------------------------

        intent = self.router.route(question)

        # When a document_id is given, every retrieval path below is
        # scoped to that document only, so chat never mixes chunks from
        # other uploads sitting in the same shared vector store.
        filters = {"document_id": document_id} if document_id else None

        # -------------------------------------------------
        # Step 2 : Retrieve Context
        #
        # A question naming pages ("what is on page 42?", "summarize
        # pages 10-12") gets exactly those pages, whatever its intent:
        # similarity search for the words "page 42" finds nothing useful.
        #
        # Otherwise every intent except SUMMARY goes through the
        # RetrievalManager (semantic + BM25 fused with RRF, optional
        # reranking). SUMMARY needs the whole document, not a
        # query-ranked subset.
        # -------------------------------------------------

        pages = parse_page_refs(question)
        page_documents = (
            self.vector_store.get_pages(pages, document_id) if pages else []
        )

        if page_documents:

            documents = page_documents

        elif intent == Intent.QA:

            documents = self.retrieval_manager.retrieve(
                query=question,
                top_k=k,
                filters=filters,
            )

        elif intent == Intent.EXPLANATION:

            # Retrieve more context for teaching/explanation
            documents = self.retrieval_manager.retrieve(
                query=question,
                top_k=12,
                filters=filters,
            )

        elif intent == Intent.SUMMARY:

            # Entire document will be used. Scoped to document_id when
            # given, otherwise falls back to the whole corpus.
            if document_id:
                documents = self.vector_store.get_document(document_id)
            else:
                documents = self.vector_store.get_all_documents()

        elif intent == Intent.COMPARISON:

            documents = self.retrieval_manager.retrieve(
                query=question,
                top_k=15,
                filters=filters,
            )

        elif intent == Intent.CHAPTER:

            documents = self.retrieval_manager.retrieve(
                query=question,
                top_k=8,
                filters=filters,
            )

        else:

            documents = self.retrieval_manager.retrieve(
                query=question,
                top_k=k,
                filters=filters,
            )

        # -------------------------------------------------
        # Step 3 : No documents found
        # -------------------------------------------------

        if not documents:

            return {
                "intent": intent.value,
                "answer": PromptBuilder.NO_ANSWER_PHRASE,
                "sources": [],
                "contexts": [],
            }

        # -------------------------------------------------
        # Step 4 : Build Prompt
        # -------------------------------------------------

        prompt = PromptBuilder.build(
            question=question,
            documents=documents,
        )

        # -------------------------------------------------
        # Step 5 : Generate Response
        # -------------------------------------------------

        answer = self.llm.generate(prompt)

        # -------------------------------------------------
        # Step 6 : Build Sources
        #
        # Show the chunks the answer actually cites. A "not found" reply
        # that cites nothing gets no sources, rather than listing pages
        # that back no claim. Uncited answers fall back to every chunk
        # the model saw.
        # -------------------------------------------------

        # The chunks the model actually saw, in "Source N" order, so callers
        # (e.g. evals) can check citations and groundedness against them.
        contexts = PromptBuilder.select_documents(documents)

        refused = PromptBuilder.is_no_answer(answer)
        source_documents = cited_documents(answer, contexts) or ([] if refused else contexts)

        sources = []

        seen = set()

        for doc in source_documents:

            source = {
                "page": doc.metadata.get("page"),
                "source": doc.metadata.get("source"),
            }

            key = (
                source["source"],
                source["page"],
            )

            if key not in seen:
                seen.add(key)
                sources.append(source)

        # -------------------------------------------------
        # Step 7 : Return
        # -------------------------------------------------

        return {
            "intent": intent.value,
            "answer": answer,
            "sources": sources,
            "contexts": contexts,
        }