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

    OCR is disabled by default: it roughly doubles conversion time and
    is a no-op for born-digital PDFs (the common case here), since it
    only matters for scanned/image-only pages with no text layer.
    """

    def __init__(self, ocr: bool = False):
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
