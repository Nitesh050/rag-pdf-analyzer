import hashlib
from pathlib import Path

from docling.exceptions import ConversionError
from fastapi import APIRouter, File, HTTPException, UploadFile
from requests.exceptions import RequestException

from ..dependencies import get_retrieval_manager
from ..ingestion.pipeline import IngestionPipeline
from ..schemas.document import IngestURLRequest, UploadResponse

router = APIRouter()

pipeline = IngestionPipeline(retrieval_manager=get_retrieval_manager())


@router.post("/upload", response_model=UploadResponse)
async def upload_pdf(file: UploadFile = File(...)):

    upload_dir = Path("uploads")
    upload_dir.mkdir(exist_ok=True)

    # Strip any directory components from the client-supplied filename
    # (e.g. "../../etc/passwd") so it can't escape upload_dir.
    filename = Path(file.filename or "").name
    if not filename:
        raise HTTPException(status_code=400, detail="Missing filename.")

    pdf_path = upload_dir / filename

    content = await file.read()
    content_hash = hashlib.sha256(content).hexdigest()

    with open(pdf_path, "wb") as f:
        f.write(content)

    try:
        result = pipeline.run(pdf_path, content_hash=content_hash)

    except ConversionError as exc:
        raise HTTPException(
            status_code=400,
            detail="Invalid or corrupted PDF file.",
        ) from exc

    return UploadResponse(
        message=result["message"],
        document_id=result.get("document_id"),
        chunks=result.get("chunks", 0),
    )


@router.post("/upload/url", response_model=UploadResponse)
async def upload_url(payload: IngestURLRequest):

    url = str(payload.url)
    # No file bytes to hash for a URL, so hash the URL itself — this
    # dedups repeated submissions of the same page the same way
    # content_hash dedups repeated uploads of the same PDF.
    content_hash = hashlib.sha256(url.encode()).hexdigest()

    try:
        result = pipeline.run_web(url, content_hash=content_hash)

    except RequestException as exc:
        raise HTTPException(
            status_code=400,
            detail="Could not fetch the given URL.",
        ) from exc

    return UploadResponse(
        message=result["message"],
        document_id=result.get("document_id"),
        chunks=result.get("chunks", 0),
    )