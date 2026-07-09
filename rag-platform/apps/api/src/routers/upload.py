from pathlib import Path

from fastapi import APIRouter, File, UploadFile

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

    pipeline.run(pdf_path)

    return UploadResponse(
        message="PDF uploaded successfully."
    )