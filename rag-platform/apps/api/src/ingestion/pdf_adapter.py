from pathlib import Path

from langchain_core.documents import Document
from pypdf import PdfReader


class PDFAdapter:
    def load(self, pdf_path: str | Path) -> list[Document]:
        reader = PdfReader(str(pdf_path))
        documents: list[Document] = []

        for page_number, page in enumerate(reader.pages, start=1):
            text = page.extract_text() or ""
            if text.strip():
                documents.append(
                    Document(
                        page_content=text.strip(),
                        metadata={"source": str(pdf_path), "page": page_number},
                    )
                )

        return documents