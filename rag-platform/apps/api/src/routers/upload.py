from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile
from pypdf.errors import PdfReadError

from ..ingestion.pipeline import IngestionPipeline
from ..schemas.document import UploadResponse

router = APIRouter()

pipeline = IngestionPipeline()


@router.post("/upload", response_model=UploadResponse)
async def upload_pdf(file: UploadFile = File(...)):

    upload_dir = Path("uploads")
    upload_dir.mkdir(exist_ok=True)

    pdf_path = upload_dir / file.filename

    with open(pdf_path, "wb") as f:
        f.write(await file.read())

    try:
        pipeline.run(pdf_path)
    except (PdfReadError, ValueError, Exception) as exc:
        raise HTTPException(status_code=400, detail=f"Invalid PDF file: {exc}") from exc

    return UploadResponse(
        message="PDF uploaded successfully."
    )