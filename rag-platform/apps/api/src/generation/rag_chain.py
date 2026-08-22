from .ollama_client import OllamaClient
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
        # Every intent except SUMMARY goes through the RetrievalManager,
        # which fuses semantic + BM25 results (RRF) and reranks them
        # with a cross-encoder. SUMMARY needs the full document instead
        # of a query-ranked subset, so it bypasses retrieval entirely.
        # -------------------------------------------------

        if intent == Intent.QA:

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
                "answer": "I couldn't find any relevant information.",
                "sources": [],
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
        # -------------------------------------------------

        sources = []

        seen = set()

        for doc in documents:

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
        }