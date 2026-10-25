from langchain_core.documents import Document

from src.ingestion.pipeline import INGESTION_VERSION, IngestionPipeline


class FakeVectorStore:
    def __init__(self, stored_version):
        self.chunk = Document(page_content="x", metadata={
            "document_id": "doc-1",
            "content_hash": "abc",
            "owner_id": "user-1",
            "ingestion_version": stored_version,
        })
        self.deleted = []

    def get_by_content_hash(self, content_hash, owner_id=None):
        meta = self.chunk.metadata
        same_owner = owner_id is None or meta["owner_id"] == owner_id
        return [self.chunk] if content_hash == meta["content_hash"] and same_owner else []

    def delete_by_document_id(self, document_id):
        self.deleted.append(document_id)


def pipeline_with(store):
    pipeline = IngestionPipeline.__new__(IngestionPipeline)
    pipeline.vector_store = store
    return pipeline


def test_current_version_is_reported_as_already_indexed():
    store = FakeVectorStore(INGESTION_VERSION)

    assert pipeline_with(store)._existing_document("abc") == ("doc-1", True)
    assert store.deleted == []


def test_stale_version_is_deleted_and_keeps_its_document_id():
    store = FakeVectorStore(INGESTION_VERSION - 1)

    assert pipeline_with(store)._existing_document("abc") == ("doc-1", False)
    assert store.deleted == ["doc-1"]


def test_unknown_content_is_new():
    store = FakeVectorStore(INGESTION_VERSION)

    assert pipeline_with(store)._existing_document("other") == (None, False)
    assert pipeline_with(store)._existing_document(None) == (None, False)


def test_same_content_from_another_owner_is_new():
    store = FakeVectorStore(INGESTION_VERSION)

    assert pipeline_with(store)._existing_document("abc", "user-1") == ("doc-1", True)
    assert pipeline_with(store)._existing_document("abc", "user-2") == (None, False)
    assert store.deleted == []
