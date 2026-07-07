from ingestion.pdf_adapter import PDFAdapter
from ingestion.chunker import DocumentChunker
from retrieval.vector_store import VectorStore


def test_ingest_pipeline():

    # ---------- Step 1: Load PDF ----------
    pdf_adapter = PDFAdapter()

    documents = pdf_adapter.load("tests/fixtures/sample.pdf")

    assert len(documents) > 0

    print(f"\nLoaded {len(documents)} pages")

    # ---------- Step 2: Chunk ----------
    chunker = DocumentChunker()

    chunks = chunker.split(documents)

    assert len(chunks) > 0

    print(f"Created {len(chunks)} chunks")

    # ---------- Step 3: Store in ChromaDB ----------
    vector_store = VectorStore()

    vector_store.add_documents(chunks)

    print("Chunks stored successfully!")

    # ---------- Step 4: Retrieve ----------
    results = vector_store.similarity_search(
        query="What is Artificial Intelligence?",
        k=3,
    )

    assert len(results) > 0

    print(f"Retrieved {len(results)} documents\n")

    # ---------- Step 5: Display ----------
    for index, document in enumerate(results, start=1):

        print("=" * 60)
        print(f"Result {index}")
        print("=" * 60)

        print(document.page_content[:300])

        print("\nMetadata:")
        print(document.metadata)

        print()