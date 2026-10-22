import os

from langchain_ollama import ChatOllama

# qwen2.5:14b scored 0.955 answer correctness vs 0.911 for qwen2.5:7b on
# the generation eval, at ~13 s vs ~8 s per answer. Set LLM_MODEL to trade
# quality for speed.
DEFAULT_MODEL = "qwen2.5:14b"


class OllamaClient:

    def __init__(
        self,
        model: str | None = None,
        temperature: float = 0.2,
        num_ctx: int = 8192,
    ):

        # Ollama's default context window is 2048 tokens and it silently
        # drops whatever doesn't fit. RAG prompts carry up to 12k chars of
        # context plus instructions (~4k tokens), so set it explicitly.
        self.llm = ChatOllama(
            model=model or os.getenv("LLM_MODEL", DEFAULT_MODEL),
            temperature=temperature,
            num_ctx=num_ctx,
        )

    @property
    def model_name(self) -> str:
        return self.llm.model

    def generate(self, prompt: str) -> str:

        response = self.llm.invoke(prompt)

        return response.content