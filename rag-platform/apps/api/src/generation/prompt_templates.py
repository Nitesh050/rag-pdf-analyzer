from langchain_core.documents import Document


class PromptBuilder:
    """
    Builds prompts for Retrieval-Augmented Generation (RAG).
    """

    @staticmethod
    def build(
        question: str,
        documents: list[Document],
    ) -> str:

        context = "\n\n".join(
            document.page_content
            for document in documents
        )

        prompt = f"""
You are an AI assistant that answers questions ONLY using the provided context.

Rules:
1. Use ONLY the information in the context.
2. Do not make up facts.
3. If the answer is not present, reply:
   "I couldn't find the answer in the provided document."
4. Answer clearly and concisely.

==================== CONTEXT ====================

{context}

=================================================

Question:
{question}

Answer:
"""

        return prompt