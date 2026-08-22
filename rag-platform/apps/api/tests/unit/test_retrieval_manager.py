import sys
from types import ModuleType, SimpleNamespace


def _insert_fake_modules():
    # fake hybrid_search module
    mod_hybrid = ModuleType("retrieval.hybrid_search")

    class FakeHybrid:
        def __init__(self):
            pass

        def retrieve(self, query, k=5, filter=None):
            return [
                SimpleNamespace(page_content=f"doc{i}", metadata={"document_id": str(i)})
                for i in range(k)
            ]

    mod_hybrid.HybridRetriever = FakeHybrid
    sys.modules["retrieval.hybrid_search"] = mod_hybrid

    # fake vector_store module
    mod_vs = ModuleType("retrieval.vector_store")

    class FakeVS:
        def __init__(self):
            pass

        def similarity_search(self, query, k=5, filter=None):
            return [
                SimpleNamespace(page_content=f"sem{i}", metadata={"document_id": f"sem{i}"})
                for i in range(k)
            ]

    mod_vs.VectorStore = FakeVS
    sys.modules["retrieval.vector_store"] = mod_vs

    # fake reranker module
    mod_rr = ModuleType("retrieval.reranker")

    class FakeReranker:
        def __init__(self, model_name=None):
            pass

        def rerank(self, query, documents, top_k=5):
            return list(reversed(documents))[:top_k]

    mod_rr.Reranker = FakeReranker
    sys.modules["retrieval.reranker"] = mod_rr


def test_retrieval_manager_hybrid_and_rerank(monkeypatch):
    _insert_fake_modules()

    # Import after fakes inserted
    from retrieval.retrieval_manager import RetrievalManager

    mgr = RetrievalManager(reranker_model="fake-model")

    results = mgr.retrieve(query="x", top_k=3, use_hybrid=True, rerank=True)

    # Reranking overfetches beyond top_k (max(top_k * 3, 20) = 20 here) so
    # the reranker has a real candidate pool to choose from, not just the
    # top_k documents already selected by fusion. Hybrid returns doc0..doc19;
    # reranker reverses and keeps the top 3: doc19, doc18, doc17.
    assert [r.page_content for r in results] == ["doc19", "doc18", "doc17"]


def test_retrieval_manager_semantic_only_no_rerank(monkeypatch):
    _insert_fake_modules()
    from retrieval.retrieval_manager import RetrievalManager

    mgr = RetrievalManager(reranker_model=None)

    results = mgr.retrieve(query="x", top_k=2, use_hybrid=False, rerank=False)

    assert [r.page_content for r in results] == ["sem0", "sem1"]
