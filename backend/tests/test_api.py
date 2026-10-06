"""
Unit Tests — API Layer
======================
Integration tests using FastAPI's test client (httpx AsyncClient).
Uses the mock LLM provider so no API keys are required.
"""
from __future__ import annotations

import io
import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(monkeypatch):
    """
    Create a test client with a mock LLM provider.
    Monkeypatches settings so it uses 'mock' provider.
    """
    import backend.config as config_module
    monkeypatch.setattr(config_module.settings, "llm_provider", "mock")

    from backend.api.main import create_app
    app = create_app()

    # Use synchronous TestClient (FastAPI lifespan runs)
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c


class TestStatusEndpoint:

    def test_status_returns_200(self, client):
        response = client.get("/api/status")
        assert response.status_code == 200

    def test_status_schema(self, client):
        data = client.get("/api/status").json()
        assert "status" in data
        assert "components" in data
        assert "document_count" in data
        assert "kb_available" in data
        assert "embedding_model" in data


class TestDocumentsEndpoint:

    def test_list_documents_empty(self, client):
        response = client.get("/api/documents")
        assert response.status_code == 200
        data = response.json()
        assert "documents" in data
        assert "total" in data

    def test_get_nonexistent_document(self, client):
        response = client.get("/api/documents/nonexistent_id")
        assert response.status_code == 404


class TestUploadEndpoint:

    def test_upload_txt_document(self, client):
        content = (
            "Patient: John Doe, Age: 52\n"
            "Diagnosis: Type 2 Diabetes Mellitus, Essential Hypertension\n"
            "Medications: Metformin 500mg twice daily, Lisinopril 10mg daily\n"
            "Blood Pressure: 138/86 mmHg\n"
            "HbA1c: 7.8%\n"
            "Follow-up: 3 months\n"
        ) * 5  # Repeat to get enough text for chunking

        response = client.post(
            "/api/upload",
            files={"file": ("clinical_note.txt", io.BytesIO(content.encode()), "text/plain")},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ready"
        assert "doc_id" in data
        assert data["chunk_count"] > 0
        assert len(data["stages"]) > 0

    def test_upload_unsupported_type(self, client):
        response = client.post(
            "/api/upload",
            files={"file": ("data.csv", io.BytesIO(b"col1,col2\n1,2"), "text/csv")},
        )
        assert response.status_code == 415

    def test_upload_empty_file(self, client):
        response = client.post(
            "/api/upload",
            files={"file": ("empty.txt", io.BytesIO(b""), "text/plain")},
        )
        assert response.status_code == 400


class TestChatEndpoint:

    def _upload_doc(self, client) -> str:
        content = (
            "Patient has hypertension. Blood pressure is 145/92 mmHg. "
            "Prescribed lisinopril 10mg daily. Patient should reduce sodium intake. "
            "Follow-up in 6 weeks to reassess blood pressure control. "
            "HbA1c is 7.2%. Metformin 500mg prescribed for type 2 diabetes. "
        ) * 10
        r = client.post(
            "/api/upload",
            files={"file": ("note.txt", io.BytesIO(content.encode()), "text/plain")},
        )
        return r.json()["doc_id"]

    def test_chat_with_document(self, client):
        doc_id = self._upload_doc(client)
        response = client.post("/api/chat", json={
            "question": "What is the patient's blood pressure?",
            "session_id": "test_session_1",
            "doc_ids": [doc_id],
        })
        assert response.status_code == 200
        data = response.json()
        assert "answer" in data
        assert "sources" in data
        assert "retrieval_info" in data
        assert len(data["answer"]) > 0

    def test_chat_without_documents(self, client):
        response = client.post("/api/chat", json={
            "question": "What is hypertension?",
            "session_id": "test_session_2",
        })
        assert response.status_code == 200
        data = response.json()
        assert "answer" in data
        # Should gracefully handle no-document case

    def test_chat_history_stored(self, client):
        session = "test_history_session"
        client.post("/api/chat", json={
            "question": "First question",
            "session_id": session,
        })
        client.post("/api/chat", json={
            "question": "Second question",
            "session_id": session,
        })

        hist = client.get(f"/api/chat/history/{session}").json()
        assert hist["turn_count"] >= 2

    def test_chat_history_clear(self, client):
        session = "clear_test"
        client.post("/api/chat", json={"question": "test", "session_id": session})
        client.delete(f"/api/chat/history/{session}")
        hist = client.get(f"/api/chat/history/{session}").json()
        assert hist["turn_count"] == 0

    def test_chat_empty_question_rejected(self, client):
        response = client.post("/api/chat", json={
            "question": "",
            "session_id": "s1",
        })
        assert response.status_code == 422  # Pydantic validation error
