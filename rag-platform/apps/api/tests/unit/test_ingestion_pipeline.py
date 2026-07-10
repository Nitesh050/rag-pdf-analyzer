from src.ingestion.pipeline import IngestionPipeline


def test_ingestion_pipeline_adds_metadata_to_chunks():
    pipeline = IngestionPipeline()

    result = pipeline.run("tests/fixtures/sample.pdf")

    assert isinstance(result, list)
    assert len(result) > 0

    for chunk in result:
        assert chunk.metadata.get("document_id")
        assert chunk.metadata.get("filename") == "sample.pdf"
