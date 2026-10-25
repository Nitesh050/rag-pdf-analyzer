"""
Every account sees only its own documents and conversations: the API needs a
login, and chat and upload are scoped to the logged-in user. Uses real
tokens; the RAG chain and ingestion pipeline are fakes. Needs
TEST_DATABASE_URL (see README).
"""

import io
import uuid

import pytest
from fastapi.testclient import TestClient

from src.db.session import get_db
from src.models.document import Document
from src.models.user import User


class FakeLLM:
    model_name = "fake-model"

    def generate(self, prompt):
        return "unused"


class FakeRAG:
    def __init__(self):
        self.llm = FakeLLM()
        self.calls = []

    def ask(self, question, document_id=None, owner_id=None):
        self.calls.append({"document_id": document_id, "owner_id": owner_id})
        return {"answer": "An answer.", "sources": [], "contexts": [], "intent": "qa", "refused": False}


class FakePipeline:
    def __init__(self):
        self.runs = []

    def run(self, pdf_path, content_hash=None, owner_id=None):
        self.runs.append({"path": pdf_path, "owner_id": owner_id})
        return {"message": "PDF indexed successfully.", "document_id": str(uuid.uuid4()), "chunks": 1}


@pytest.fixture
def setup(db, monkeypatch, tmp_path):
    from src.main import app
    from src.routers import chat as chat_router
    from src.routers import upload as upload_router

    rag, pipeline = FakeRAG(), FakePipeline()
    monkeypatch.setattr(chat_router, "get_rag_chain", lambda: rag)
    monkeypatch.setattr(upload_router, "pipeline", pipeline)
    monkeypatch.setattr(upload_router, "_schedule_summary", lambda *args: None)
    monkeypatch.chdir(tmp_path)  # uploads/ is relative to the working directory
    app.dependency_overrides[get_db] = lambda: db
    yield TestClient(app), rag, pipeline, db
    app.dependency_overrides.clear()


def account(client, db, email):
    """Sign up and log in; returns (auth headers, User)."""
    client.post("/auth/signup", json={"email": email, "password": "correct horse"})
    token = client.post("/auth/login", json={"email": email, "password": "correct horse"}).json()["access_token"]
    user = db.query(User).filter_by(email=email).one()
    return {"Authorization": f"Bearer {token}"}, user


def own_document(db, user):
    document = Document(owner_id=user.id, source_type="pdf", filename="book.pdf", content_hash=f"h-{uuid.uuid4()}")
    db.add(document)
    db.flush()
    return document


@pytest.mark.parametrize("method, path, body", [
    ("post", "/chat", {"question": "hi"}),
    ("get", "/conversations", None),
    ("post", "/upload/url", {"url": "https://example.com"}),
])
def test_api_requires_login(setup, method, path, body):
    client, rag, _, _ = setup

    response = getattr(client, method)(path, **({"json": body} if body else {}))

    assert response.status_code == 401
    assert rag.calls == []


def test_chat_without_a_document_searches_only_your_documents(setup):
    client, rag, _, db = setup
    ada, ada_user = account(client, db, "ada@example.com")

    response = client.post("/chat", json={"question": "hi"}, headers=ada)

    assert response.status_code == 200, response.text
    assert rag.calls == [{"document_id": None, "owner_id": str(ada_user.id)}]


def test_chat_with_your_document_is_allowed(setup):
    client, rag, _, db = setup
    ada, ada_user = account(client, db, "ada@example.com")
    book = own_document(db, ada_user)

    response = client.post("/chat", json={"question": "hi", "document_id": str(book.id)}, headers=ada)

    assert response.status_code == 200, response.text
    assert rag.calls[0]["document_id"] == str(book.id)


@pytest.mark.parametrize("document_id", ["someone-elses", str(uuid.uuid4()), "not-a-uuid"])
def test_chat_with_a_document_you_dont_own_is_not_found(setup, document_id):
    client, rag, _, db = setup
    ada, ada_user = account(client, db, "ada@example.com")
    bob, _ = account(client, db, "bob@example.com")
    if document_id == "someone-elses":
        document_id = str(own_document(db, ada_user).id)

    response = client.post("/chat", json={"question": "hi", "document_id": document_id}, headers=bob)

    assert response.status_code == 404
    assert rag.calls == []


def test_conversations_are_private(setup):
    client, _, _, db = setup
    ada, _ = account(client, db, "ada@example.com")
    bob, _ = account(client, db, "bob@example.com")
    conversation_id = client.post("/chat", json={"question": "hi"}, headers=ada).json()["conversation_id"]

    assert client.get("/conversations", headers=bob).json() == []
    assert client.get(f"/conversations/{conversation_id}", headers=bob).status_code == 404
    assert client.post("/chat", json={"question": "and?", "conversation_id": conversation_id},
                       headers=bob).status_code == 404


def test_uploads_go_to_a_folder_per_user_and_are_tagged_with_the_owner(setup):
    client, _, pipeline, db = setup
    ada, ada_user = account(client, db, "ada@example.com")
    bob, bob_user = account(client, db, "bob@example.com")

    for headers in (ada, bob):
        file = {"file": ("report.pdf", io.BytesIO(b"%PDF same bytes"), "application/pdf")}
        assert client.post("/upload", files=file, headers=headers).status_code == 200

    assert [str(r["path"]) for r in pipeline.runs] == [
        f"uploads/{ada_user.id}/report.pdf",
        f"uploads/{bob_user.id}/report.pdf",
    ]
    assert [r["owner_id"] for r in pipeline.runs] == [str(ada_user.id), str(bob_user.id)]
