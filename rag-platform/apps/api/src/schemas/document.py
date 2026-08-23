from pydantic import BaseModel, HttpUrl


class UploadResponse(BaseModel):
    message: str
    document_id: str | None = None
    chunks: int = 0


class IngestURLRequest(BaseModel):
    url: HttpUrl