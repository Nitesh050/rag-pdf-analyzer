from generation.rag_chain import RAGChain


def test_rag_chain():

    rag = RAGChain()

    result = rag.ask(
        "summary of the whole document ",
    )

    print("\n")
    print("=" * 80)
    print(result["answer"])
    print("=" * 80)

    print("\nSources:")

    for source in result["sources"]:
        print(source.metadata)

    assert len(result["answer"]) > 0