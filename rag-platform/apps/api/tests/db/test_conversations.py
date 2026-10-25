"""
Conversation memory through the real /chat endpoints and Postgres, with the
LLM and retrieval replaced by fakes. Needs TEST_DATABASE_URL (see README).
"""

import uuid

import pytest
from fastapi.testclient import TestClient
from langchain_core.documents import Document as Chunk
from sqlalchemy import select

from src.core.security import get_current_user, get_local_user
from src.db.session import get_db
from src.models.conversation import Conversation, Message
from src.models.document import Document
from src.models.user import User


class FakeLLM:
    model_name = "fake-model"

    def __init__(self):
        self.prompts = []

    def generate(self, prompt):
        self.prompts.append(prompt)
        return "How many neurons does a fruit fly have?"


class FakeRAG:
    """Stands in for RAGChain: records the questions it is asked."""

    def __init__(self, document_id):
        self.llm = FakeLLM()
        self.asked = []
        self.owner_ids = []
        self.document_id = document_id
        self.answer = "A nematode worm has 302 neurons (Source 1, page 42)."

    def ask(self, question, document_id=None, owner_id=None):
        self.asked.append((question, document_id))
        self.owner_ids.append(owner_id)
        contexts = [
            Chunk(page_content="neurons", metadata={"document_id": self.document_id, "page": 42}),
            Chunk(page_content="other", metadata={"document_id": self.document_id, "page": 43}),
        ]
        return {
            "answer": self.answer,
            "intent": "qa",
            "contexts": contexts,
            "sources": [{"page": 42, "source": "uploads/book.pdf"}],
        }


@pytest.fixture
def setup(db, monkeypatch):
    from src.main import app
    from src.routers import chat as chat_router

    owner = get_local_user(db)
    book = Document(owner_id=owner.id, source_type="pdf", filename="book.pdf",
                    storage_path="uploads/book.pdf", content_hash=f"h-{uuid.uuid4()}")
    db.add(book)
    db.flush()

    rag = FakeRAG(str(book.id))
    monkeypatch.setattr(chat_router, "get_rag_chain", lambda: rag)
    app.dependency_overrides[get_db] = lambda: db
    # Login itself is tested in test_auth.py; here every request is the owner.
    app.dependency_overrides[get_current_user] = lambda: owner
    yield TestClient(app), rag, book, db
    app.dependency_overrides.clear()


def ask(client, question, **extra):
    response = client.post("/chat", json={"question": question, **extra})
    assert response.status_code == 200, response.text
    return response.json()


def test_first_question_starts_a_conversation_without_rewriting(setup):
    client, rag, book, db = setup

    reply = ask(client, "How many neurons does a nematode worm have?", document_id=str(book.id))

    assert reply["conversation_id"]
    assert reply["standalone_question"] is None
    assert rag.llm.prompts == []  # no history, so no rewrite call
    assert rag.asked == [("How many neurons does a nematode worm have?", str(book.id))]

    conversation = db.get(Conversation, uuid.UUID(reply["conversation_id"]))
    assert conversation.document_id == book.id
    assert conversation.title == "How many neurons does a nematode worm have?"


def test_follow_up_is_rewritten_and_stays_on_the_document(setup):
    client, rag, book, _ = setup
    first = ask(client, "How many neurons does a nematode worm have?", document_id=str(book.id))

    reply = ask(client, "And a fruit fly?", conversation_id=first["conversation_id"])

    assert reply["conversation_id"] == first["conversation_id"]
    assert reply["standalone_question"] == "How many neurons does a fruit fly have?"
    assert "nematode worm" in rag.llm.prompts[0]  # the rewrite saw the history
    # Retrieval used the rewritten question and the conversation's document.
    assert rag.asked[-1] == ("How many neurons does a fruit fly have?", str(book.id))


def test_messages_and_cited_sources_are_saved_in_order(setup):
    client, _, book, db = setup
    first = ask(client, "How many neurons does a nematode worm have?", document_id=str(book.id))
    ask(client, "And a fruit fly?", conversation_id=first["conversation_id"])

    messages = db.scalars(
        select(Message)
        .where(Message.conversation_id == uuid.UUID(first["conversation_id"]))
        .order_by(Message.created_at)
    ).all()

    assert [m.role for m in messages] == ["user", "assistant", "user", "assistant"]
    answer = messages[3]
    assert answer.standalone_question == "How many neurons does a fruit fly have?"
    assert (answer.intent, answer.refused, answer.model) == ("qa", False, "fake-model")
    assert answer.latency_ms is not None
    assert [(s.source_number, s.page, s.cited, s.document_id) for s in answer.sources] == [
        (1, 42, True, book.id),
        (2, 43, False, book.id),
    ]


def test_refusal_is_recorded(setup):
    client, rag, book, db = setup
    rag.answer = "I couldn't find the answer in the provided document(s)."

    reply = ask(client, "Who is the author?", document_id=str(book.id))

    answer = db.scalars(select(Message).where(
        Message.conversation_id == uuid.UUID(reply["conversation_id"]), Message.role == "assistant",
    )).one()
    assert answer.refused is True
    assert not any(s.cited for s in answer.sources)


def test_conversations_can_be_listed_and_reloaded(setup):
    client, _, book, _ = setup
    first = ask(client, "How many neurons does a nematode worm have?", document_id=str(book.id))
    ask(client, "And a fruit fly?", conversation_id=first["conversation_id"])

    listed = client.get("/conversations").json()
    assert listed[0]["id"] == first["conversation_id"]

    detail = client.get(f"/conversations/{first['conversation_id']}").json()
    assert [m["role"] for m in detail["messages"]] == ["user", "assistant", "user", "assistant"]
    assert detail["messages"][1]["sources"] == [{"page": 42, "source": "uploads/book.pdf"}]
    assert detail["document_id"] == str(book.id)


@pytest.mark.parametrize("conversation_id", ["not-a-uuid", str(uuid.uuid4())])
def test_unknown_conversation_is_404(setup, conversation_id):
    client, _, _, _ = setup

    assert client.post("/chat", json={"question": "hi", "conversation_id": conversation_id}).status_code == 404
    assert client.get(f"/conversations/{conversation_id}").status_code == 404


def test_another_users_conversation_is_not_accessible(setup):
    client, _, _, db = setup
    stranger = User(email=f"{uuid.uuid4()}@example.com", password_hash="h")
    db.add(stranger)
    db.flush()
    theirs = Conversation(user_id=stranger.id, title="private")
    db.add(theirs)
    db.flush()

    assert client.get(f"/conversations/{theirs.id}").status_code == 404
    assert client.post("/chat", json={"question": "hi", "conversation_id": str(theirs.id)}).status_code == 404
    assert str(theirs.id) not in [c["id"] for c in client.get("/conversations").json()]
