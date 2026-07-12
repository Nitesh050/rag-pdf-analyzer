from .ollama_client import OllamaClient
from .prompt_templates import PromptBuilder

from .intent.router import IntentRouter
from .intent.intent import Intent

from ..retrieval.vector_store import VectorStore


class RAGChain:
    """
    Orchestrates the complete Retrieval-Augmented Generation pipeline.
    """

    def __init__(self):
        self.vector_store = VectorStore()
        self.llm = OllamaClient()
        self.router = IntentRouter()

    def ask(self, question: str, k: int = 5) -> dict:

        # -------------------------------------------------
        # Step 1 : Detect User Intent
        # -------------------------------------------------

        intent = self.router.route(question)

        # -------------------------------------------------
        # Step 2 : Retrieve Context
        # -------------------------------------------------

        if intent == Intent.QA:

            documents = self.vector_store.similarity_search(
                query=question,
                k=k,
            )

        elif intent == Intent.EXPLANATION:

            # Retrieve more context for teaching/explanation
            documents = self.vector_store.similarity_search(
                query=question,
                k=12,
            )

        elif intent == Intent.SUMMARY:

            # Entire document will be used
            documents = self.vector_store.get_all_documents()

        elif intent == Intent.COMPARISON:

            documents = self.vector_store.similarity_search(
                query=question,
                k=15,
            )

        elif intent == Intent.CHAPTER:

            documents = self.vector_store.similarity_search(
                query=question,
                k=8,
            )

        else:

            documents = self.vector_store.similarity_search(
                query=question,
                k=k,
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