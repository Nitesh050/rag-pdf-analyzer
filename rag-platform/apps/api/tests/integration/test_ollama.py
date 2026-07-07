from generation.ollama_client import OllamaClient


def test_ollama():

    llm = OllamaClient()

    response = llm.generate(
        "Explain Artificial Intelligence in two sentences."
    )

    print(response)

    assert len(response) > 0