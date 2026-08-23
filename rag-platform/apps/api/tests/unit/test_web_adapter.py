from unittest.mock import Mock, patch

from src.ingestion.web_adapter import WebAdapter

SAMPLE_HTML = """
<html>
<head><title>Sample Page</title></head>
<body>
<nav>Home | About</nav>
<script>console.log('noise')</script>
<article><h1>Hello</h1><p>This is the article body.</p></article>
<footer>Copyright 2026</footer>
</body>
</html>
"""


def _mock_response(html: str, status_ok: bool = True) -> Mock:
    response = Mock()
    response.text = html
    response.raise_for_status = Mock()
    if not status_ok:
        response.raise_for_status.side_effect = Exception("HTTP error")
    return response


@patch("src.ingestion.web_adapter.requests.get")
def test_web_adapter_extracts_clean_text_and_metadata(mock_get):
    mock_get.return_value = _mock_response(SAMPLE_HTML)

    adapter = WebAdapter()
    documents = adapter.load("https://example.com/page")

    assert len(documents) == 1

    document = documents[0]

    assert "Hello" in document.page_content
    assert "This is the article body." in document.page_content
    assert "Home | About" not in document.page_content
    assert "console.log" not in document.page_content
    assert "Copyright 2026" not in document.page_content

    assert document.metadata["source"] == "https://example.com/page"
    assert document.metadata["title"] == "Sample Page"


@patch("src.ingestion.web_adapter.requests.get")
def test_web_adapter_returns_empty_list_for_blank_page(mock_get):
    mock_get.return_value = _mock_response("<html><head></head><body></body></html>")

    adapter = WebAdapter()
    documents = adapter.load("https://example.com/blank")

    assert documents == []
