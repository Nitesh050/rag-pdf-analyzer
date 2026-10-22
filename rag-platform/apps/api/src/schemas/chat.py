from datetime import datetime

from pydantic import BaseModel


class ChatRequest(BaseModel):
    question: str
    document_id: str | None = None
    # Omit to start a new conversation; send the returned id for follow-ups.
    conversation_id: str | None = None


class Source(BaseModel):
    page: int | None = None
    source: str | None = None


class ChatResponse(BaseModel):
    answer: str
    sources: list[Source]
    conversation_id: str
    # The follow-up as rewritten for search, when it differed from the question.
    standalone_question: str | None = None


class ConversationSummary(BaseModel):
    id: str
    title: str | None
    document_id: str | None
    updated_at: datetime


class ConversationMessage(BaseModel):
    role: str
    content: str
    sources: list[Source] = []
    created_at: datetime


class ConversationDetail(ConversationSummary):
    messages: list[ConversationMessage]
