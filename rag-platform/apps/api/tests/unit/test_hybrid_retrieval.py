from langchain_core.documents import Document

from retrieval.bm25 import BM25Retriever
from retrieval.fusion import ReciprocalRankFusion


def doc(name):
    return Document(page_content=name, metadata={"document_id": name, "page": 1})


def test_tokenize_drops_stopwords_and_stems():
    tokens = BM25Retriever().tokenize("What does it mean to saturate a network?")

    assert tokens == BM25Retriever().tokenize("meaning saturating networks")


def test_retrieve_skips_chunks_with_no_matching_terms():
    bm25 = BM25Retriever()
    bm25.build_index([
        doc("saturation of the activation function"),
        doc("matrix multiplication of weights"),
        doc("training data for the network"),
    ])

    results = bm25.retrieve("why does saturation happen", k=5)

    assert [r.page_content for r in results] == ["saturation of the activation function"]


def test_fusion_weights_scale_each_list():
    a, b = doc("a"), doc("b")
    fusion = ReciprocalRankFusion()

    assert fusion.fuse([[a, b], [b, a]], top_k=1, weights=[1.0, 0.5]) == [a]
    assert fusion.fuse([[a, b], [b, a]], top_k=1, weights=[0.5, 1.0]) == [b]
