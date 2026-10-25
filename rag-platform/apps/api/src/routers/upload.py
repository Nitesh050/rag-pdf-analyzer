import hashlib
from pathlib import Path

from docling.exceptions import ConversionError
from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile
from requests.exceptions import RequestException
from sqlalchemy.orm import Session

from ..core.security import get_current_user
from ..db.documents import record_document
from ..db.session import get_db
from ..dependencies import get_rag_chain, get_retrieval_manager
from ..ingestion.pipeline import INGESTION_VERSION, IngestionPipeline
from ..models.user import User
from ..schemas.document import IngestURLRequest, UploadResponse

router = APIRouter()

pipeline = IngestionPipeline(retrieval_manager=get_retrieval_manager())


@router.post("/upload", response_model=UploadResponse)
async def upload_pdf(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):

    # One folder per user, so two users' "report.pdf" don't overwrite each other.
    upload_dir = Path("uploads") / str(user.id)
    upload_dir.mkdir(parents=True, exist_ok=True)

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
        result = pipeline.run(pdf_path, content_hash=content_hash, owner_id=str(user.id))

    except ConversionError as exc:
        raise HTTPException(
            status_code=400,
            detail="Invalid or corrupted PDF file.",
        ) from exc

    if result.get("document_id"):
        record_document(
            db, user,
            document_id=result["document_id"],
            content_hash=content_hash,
            chunk_count=result.get("chunks", 0),
            ingestion_version=INGESTION_VERSION,
            filename=filename,
            storage_path=pdf_path,
        )

    _schedule_summary(background_tasks, result)

    return UploadResponse(
        message=result["message"],
        document_id=result.get("document_id"),
        chunks=result.get("chunks", 0),
    )


@router.post("/upload/url", response_model=UploadResponse)
async def upload_url(
    payload: IngestURLRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):

    url = str(payload.url)
    # No file bytes to hash for a URL, so hash the URL itself — this
    # dedups repeated submissions of the same page the same way
    # content_hash dedups repeated uploads of the same PDF.
    content_hash = hashlib.sha256(url.encode()).hexdigest()

    try:
        result = pipeline.run_web(url, content_hash=content_hash, owner_id=str(user.id))

    except RequestException as exc:
        raise HTTPException(
            status_code=400,
            detail="Could not fetch the given URL.",
        ) from exc

    if result.get("document_id"):
        record_document(
            db, user,
            document_id=result["document_id"],
            content_hash=content_hash,
            chunk_count=result.get("chunks", 0),
            ingestion_version=INGESTION_VERSION,
            source_url=url,
        )

    _schedule_summary(background_tasks, result)

    return UploadResponse(
        message=result["message"],
        document_id=result.get("document_id"),
        chunks=result.get("chunks", 0),
    )


def _schedule_summary(background_tasks: BackgroundTasks, result: dict) -> None:
    """
    Precompute section summaries after the response is sent, so the first
    "summarize this" question on a long document is answered quickly.
    """
    if result.get("document_id") and result.get("chunks"):
        background_tasks.add_task(get_rag_chain().prepare_summary, result["document_id"])
