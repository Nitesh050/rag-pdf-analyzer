from langchain_ollama import ChatOllama


class OllamaClient:

    def __init__(
        self,
        model: str = "qwen2.5:7b",
        temperature: float = 0.2,
        num_ctx: int = 8192,
    ):

        # Ollama's default context window is 2048 tokens and it silently
        # drops whatever doesn't fit. RAG prompts carry up to 12k chars of
        # context plus instructions (~4k tokens), so set it explicitly.
        self.llm = ChatOllama(
            model=model,
            temperature=temperature,
            num_ctx=num_ctx,
        )

    def generate(self, prompt: str) -> str:

        response = self.llm.invoke(prompt)

        return response.content