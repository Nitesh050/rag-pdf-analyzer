import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from ..generation.citation_mapper import cited_documents
from ..generation.prompt_templates import PromptBuilder
from ..models.conversation import Conversation, Message, MessageSource
from ..models.document import Document
from ..models.user import User
from .documents import parse_document_id

TITLE_CHARS = 80


def get_conversation(db: Session, user: User, conversation_id: str) -> Conversation | None:
    """The user's conversation with this id, or None (unknown, malformed, or someone else's)."""
    try:
        key = uuid.UUID(conversation_id)
    except (TypeError, ValueError):
        return None

    return db.scalar(
        select(Conversation)
        .where(Conversation.id == key, Conversation.user_id == user.id, Conversation.archived_at.is_(None))
        .options(selectinload(Conversation.messages).selectinload(Message.sources))
    )


def start_conversation(db: Session, user: User, document_id: str | None, first_question: str) -> Conversation:
    document_key = parse_document_id(document_id)
    # Only link documents that exist in Postgres (the FK requires it).
    if document_key and db.get(Document, document_key) is None:
        document_key = None

    title = " ".join(first_question.split())
    conversation = Conversation(
        user_id=user.id,
        document_id=document_key,
        title=title if len(title) <= TITLE_CHARS else title[: TITLE_CHARS - 3] + "...",
    )
    db.add(conversation)
    db.flush()
    return conversation


def history(conversation: Conversation) -> list[tuple[str, str]]:
    """Earlier (role, content) pairs, oldest first, skipping failed answers."""
    return [(m.role, m.content) for m in conversation.messages if m.status == "ok"]


def save_turn(
    db: Session,
    conversation: Conversation,
    question: str,
    standalone_question: str,
    result: dict,
    model: str | None,
    latency_ms: int,
) -> Message:
    """Store the question and the answer, with the context the answer was built from."""
    answer = result["answer"]
    contexts = result.get("contexts", [])
    cited = {id(doc) for doc in cited_documents(answer, contexts)}
    known_documents: dict[uuid.UUID, bool] = {}

    db.add(Message(conversation_id=conversation.id, role="user", content=question))

    reply = Message(
        conversation_id=conversation.id,
        role="assistant",
        content=answer,
        standalone_question=standalone_question if standalone_question != question else None,
        intent=result.get("intent"),
        refused=PromptBuilder.is_no_answer(answer),
        model=model,
        latency_ms=latency_ms,
    )

    for number, doc in enumerate(contexts, start=1):
        document_key = parse_document_id(doc.metadata.get("document_id"))
        if document_key is not None and document_key not in known_documents:
            known_documents[document_key] = db.get(Document, document_key) is not None

        reply.sources.append(MessageSource(
            source_number=number,
            document_id=document_key if known_documents.get(document_key) else None,
            chunk_id=None,  # chunks aren't stored in Postgres yet
            page=doc.metadata.get("page"),
            page_end=doc.metadata.get("page_end"),
            cited=id(doc) in cited,
        ))

    db.add(reply)
    conversation.updated_at = func.now()
    db.commit()
    return reply


def list_conversations(db: Session, user: User, limit: int = 50) -> list[Conversation]:
    return list(db.scalars(
        select(Conversation)
        .where(Conversation.user_id == user.id, Conversation.archived_at.is_(None))
        .order_by(Conversation.updated_at.desc())
        .limit(limit)
    ))
