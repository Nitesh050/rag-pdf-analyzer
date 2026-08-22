from pathlib import Path

import pymupdf
from langchain_core.documents import Document


class PDFAdapter:
    """
    Loads a PDF into per-page LangChain Documents using PyMuPDF.

    PyMuPDF extracts text in correct reading order for multi-column
    and complex layouts (unlike pypdf's naive stream-order extraction),
    and exposes document-level metadata (title/author/etc.) that pypdf
    does not reliably surface.
    """

    def load(self, pdf_path: str | Path) -> list[Document]:
        documents: list[Document] = []

        with pymupdf.open(str(pdf_path)) as pdf:
            raw_meta = pdf.metadata or {}
            doc_meta = {
                key: value
                for key, value in {
                    "title": raw_meta.get("title") or None,
                    "author": raw_meta.get("author") or None,
                }.items()
                if value
            }

            for page_number in range(1, pdf.page_count + 1):
                page = pdf[page_number - 1]
                # sort=True reconstructs reading order from raw text
                # fragments, which keeps multi-column pages and
                # sidebars/callouts from interleaving mid-sentence.
                text = str(page.get_text("text", sort=True)).strip()

                if not text:
                    continue

                documents.append(
                    Document(
                        page_content=text,
                        metadata={
                            "source": str(pdf_path),
                            "page": page_number,
                            **doc_meta,
                        },
                    )
                )

        return documents
