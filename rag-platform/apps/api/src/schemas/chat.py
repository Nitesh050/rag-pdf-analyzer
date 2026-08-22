from pydantic import BaseModel


class ChatRequest(BaseModel):
    question: str
    document_id: str | None = None


class Source(BaseModel):
    page:int | None=None
    source: str| None=None

class ChatResponse(BaseModel):
    answer:str
    sources: list[Source]