import time

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from src.core.security import get_current_user
from src.db.conversations import get_conversation, history, list_conversations, save_turn, start_conversation
from src.db.session import get_db
from src.dependencies import get_rag_chain
from src.generation.followup import rewrite_followup
from src.models.conversation import Conversation
from src.models.document import Document
from src.models.user import User
from src.schemas.chat import (
    ChatRequest,
    ChatResponse,
    ConversationDetail,
    ConversationMessage,
    ConversationSummary,
    Source,
)

router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
def chat(
    request: ChatRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if request.conversation_id:
        conversation = get_conversation(db, user, request.conversation_id)
        if conversation is None:
            raise HTTPException(status_code=404, detail="Conversation not found.")
    else:
        conversation = start_conversation(db, user, request.document_id, request.question)

    # A follow-up stays on the conversation's document unless one is given.
    document_id = request.document_id or (
        str(conversation.document_id) if conversation.document_id else None
    )

    rag = get_rag_chain()
    started = time.perf_counter()

    standalone = rewrite_followup(request.question, history(conversation), rag.llm)
    result = rag.ask(standalone, document_id=document_id)

    save_turn(
        db, conversation,
        question=request.question,
        standalone_question=standalone,
        result=result,
        model=rag.llm.model_name,
        latency_ms=int((time.perf_counter() - started) * 1000),
    )

    return ChatResponse(
        answer=result["answer"],
        sources=result["sources"],
        conversation_id=str(conversation.id),
        standalone_question=standalone if standalone != request.question else None,
    )


@router.get("/conversations", response_model=list[ConversationSummary])
def conversations(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return [_summary(c) for c in list_conversations(db, user)]


@router.get("/conversations/{conversation_id}", response_model=ConversationDetail)
def conversation_detail(
    conversation_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    conversation = get_conversation(db, user, conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found.")

    # Same "uploads/<file>" label the live /chat response uses.
    document_ids = {s.document_id for m in conversation.messages for s in m.sources if s.document_id}
    labels = {
        d.id: d.storage_path or d.source_url or d.filename
        for d in (db.get(Document, i) for i in document_ids) if d
    }

    return ConversationDetail(
        **_summary(conversation).model_dump(),
        messages=[
            ConversationMessage(
                role=m.role,
                content=m.content,
                created_at=m.created_at,
                sources=[Source(page=s.page, source=labels.get(s.document_id)) for s in m.sources if s.cited],
            )
            for m in conversation.messages
        ],
    )


def _summary(conversation: Conversation) -> ConversationSummary:
    return ConversationSummary(
        id=str(conversation.id),
        title=conversation.title,
        document_id=str(conversation.document_id) if conversation.document_id else None,
        updated_at=conversation.updated_at,
    )
