from .ollama_client import OllamaClient
from .prompt_templates import PromptBuilder
from ..retrieval.vector_store import VectorStore


class RAGChain:
    """
    Orchestrates the complete Retrieval-Augmented Generation pipeline.
    """

    def __init__(self):
        self.vector_store = VectorStore()
        self.llm = OllamaClient()

    def ask(self, question: str, k: int = 5) -> dict:

        # Step 1: Retrieve relevant chunks
        documents = self.vector_store.similarity_search(
            query=question,
            k=1,
        )

        # Step 2: If nothing is found
        if not documents:
            return {
                "answer": "I couldn't find any relevant information.",
                "sources": [],
            }

        # Step 3: Build prompt
        prompt = PromptBuilder.build(
            question=question,
            documents=documents,
        )

        # Step 4: Generate answer
        answer = self.llm.generate(prompt)

        # Step 5: Return answer + sources
        sources = []

        for doc in documents:
            sources.append(
                {
                    "page": doc.metadata.get("page"),
                    "source": doc.metadata.get("source"),
                }
            )

        return {
            "answer": answer,
            "sources": sources,
        }