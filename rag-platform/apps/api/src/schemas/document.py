from pydantic import BaseModel


class UploadResponse(BaseModel):
    message: str
    document_id: str | None = None
    chunks: int = 0