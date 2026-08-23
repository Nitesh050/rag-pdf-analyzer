import requests
from bs4 import BeautifulSoup
from langchain_core.documents import Document

# Tags that only add page chrome (navigation, scripts, ads) rather than
# readable content, and would otherwise pollute the extracted text.
NOISE_TAGS = ["script", "style", "nav", "footer", "header", "noscript", "aside", "form"]


class WebAdapter:
    """
    Loads a web page into a single LangChain Document.

    Fetches the raw HTML and strips non-content chrome (nav/footer/
    scripts/etc.) so only the readable text reaches the chunker, similar
    to what PDFAdapter does for PDFs.
    """

    def __init__(self, timeout: int = 15):
        self.timeout = timeout

    def load(self, url: str) -> list[Document]:
        # A default User-Agent is rejected by some sites (e.g. via WAFs
        # that block obvious script traffic), so identify as a browser.
        response = requests.get(
            url,
            timeout=self.timeout,
            headers={"User-Agent": "Mozilla/5.0 (compatible; RAGPlatformBot/1.0)"},
        )
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")

        for tag in soup(NOISE_TAGS):
            tag.decompose()

        title = soup.title.get_text(strip=True) if soup.title else url

        text = soup.get_text(separator="\n", strip=True)

        if not text:
            return []

        return [
            Document(
                page_content=text,
                metadata={"source": url, "title": title},
            )
        ]
