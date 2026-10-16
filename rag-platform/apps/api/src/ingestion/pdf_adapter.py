import os
import re
from pathlib import Path

from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.document_converter import DocumentConverter, PdfFormatOption
from langchain_core.documents import Document


class PDFAdapter:
    """
    Loads a PDF into per-page LangChain Documents using Docling.

    Docling runs a layout-analysis model over each page, so it extracts
    tables as structured Markdown and preserves headings/lists instead
    of returning a flat text blob — a real step up from pypdf/PyMuPDF's
    plain-text extraction for documents with tabular or structured data.

    OCR reads text inside images (scanned pages, slides exported as
    pictures). It is on by default and configurable with PDF_OCR=false.
    Docling picks the engine: Apple Vision (ocrmac) on macOS, RapidOCR
    elsewhere.
    """

    def __init__(self, ocr: bool | None = None):
        if ocr is None:
            ocr = os.getenv("PDF_OCR", "true").lower() not in ("0", "false", "no")
        self.ocr = ocr

        pipeline_options = PdfPipelineOptions(
            do_ocr=ocr,
            do_table_structure=True,
        )
        self.converter = DocumentConverter(
            format_options={
                InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options),
            }
        )

    def load(self, pdf_path: str | Path) -> list[Document]:
        documents = []

        for document in self._convert(pdf_path):
            text = normalize_text(document.page_content)

            if text:
                document.page_content = text
                documents.append(document)

        return documents

    def _convert(self, pdf_path: str | Path) -> list[Document]:
        """Raw per-page Markdown from Docling, before normalisation."""

        result = self.converter.convert(str(pdf_path))
        doc = result.document

        documents: list[Document] = []

        for page_number in range(1, doc.num_pages() + 1):
            text = doc.export_to_markdown(page_no=page_number).strip()

            if not text:
                continue

            documents.append(
                Document(
                    page_content=text,
                    metadata={"source": str(pdf_path), "page": page_number},
                )
            )

        return documents


IMAGE_PLACEHOLDER = re.compile(r"^\s*<!-- image -->\s*$", re.MULTILINE)
TABLE_PADDING = re.compile(r" {2,}")


def normalize_text(text: str) -> str:
    """
    Clean Docling's Markdown so the splitter and BM25 see ordinary text.

    - Non-breaking spaces become spaces. Some PDFs use them for most word
      gaps, and the splitter only breaks on ". " / " ", so it would
      otherwise cut chunks mid-word.
    - Soft hyphens become "-": PDFs use them as visible dashes
      ("human\xadlike", "Part 1 \xad How").
    - "<!-- image -->" placeholders are dropped; they carry no content.
    - Runs of spaces padding Markdown table cells are collapsed. Only table
      rows are touched, so code indentation survives.
    """

    text = text.replace("\xa0", " ").replace("\xad", "-")
    text = IMAGE_PLACEHOLDER.sub("", text)

    lines = [
        TABLE_PADDING.sub(" ", line) if line.lstrip().startswith("|") else line
        for line in text.split("\n")
    ]

    text = "\n".join(lines)
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()
