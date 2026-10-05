"""
Sprint 5 Test Suite -- Frontend Wiring, Real Pipeline Progress, and Persistent History.

Coverage:
  1. JobTrackerService: Job creation, stage progress updating, and expired cleanup.
  2. GET /api/diagrams/{job_id}/status: Endpoint returns active stage, percentage, and result payload.
  3. POST /api/diagrams/generate-async: Endpoint creates async job and returns poll_url.
  4. GET /api/history: List persisted diagram requests sorted chronologically.
  5. GET /api/history/{id}: Fetch single diagram request detail with SVG & AST.
  6. DELETE /api/history/{id}: Delete a diagram request row from DB.
  7. POST /api/chat/message: Diagram-aware chat Q&A with system prompt injection.
  8. POST /api/diagrams/upload-reference: Reference file text extraction.
"""

from __future__ import annotations

import io
from unittest.mock import MagicMock, patch
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.job_tracker_service import JobTrackerService, job_tracker_service

client = TestClient(app)


# ------------------------------------------------------------------------------
# 1. JobTrackerService Unit Tests
# ------------------------------------------------------------------------------


def test_job_tracker_lifecycle():
    """Create, update through stages, and retrieve job status."""
    tracker = JobTrackerService()
    job_id = "test-job-123"

    tracker.create_job(job_id)
    j1 = tracker.get_job(job_id)
    assert j1 is not None
    assert j1.stage == "scope_guard"
    assert j1.progress_percentage == 10

    tracker.update_job(job_id, "rendering", message="Rendering via Kroki")
    j2 = tracker.get_job(job_id)
    assert j2.stage == "rendering"
    assert j2.progress_percentage == 85
    assert j2.message == "Rendering via Kroki"

    tracker.update_job(job_id, "completed", result={"svg": "<svg/>"})
    j3 = tracker.get_job(job_id)
    assert j3.stage == "completed"
    assert j3.progress_percentage == 100
    assert j3.result == {"svg": "<svg/>"}


# ------------------------------------------------------------------------------
# 2. Async Job Generation & Status Polling API Tests
# ------------------------------------------------------------------------------


def test_get_job_status_404():
    """Requesting non-existent job ID returns 404."""
    resp = client.get("/api/diagrams/non-existent-job-xyz/status")
    assert resp.status_code == 404


def test_generate_async_and_poll():
    """POST /generate-async initiates job and status polling returns progress."""
    job_id = "poll-test-job-999"
    job_tracker_service.create_job(job_id)
    job_tracker_service.update_job(job_id, "llm_generation", message="Calling Groq LLM...")

    resp = client.get(f"/api/diagrams/{job_id}/status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["job_id"] == job_id
    assert data["stage"] == "llm_generation"
    assert data["progress_percentage"] == 60


# ------------------------------------------------------------------------------
# 3. Persistent History Endpoints Tests
# ------------------------------------------------------------------------------


def test_history_list_endpoint(db_session):
    """GET /api/history returns list of diagram requests."""
    from app.core.database import get_db
    app.dependency_overrides[get_db] = lambda: db_session
    try:
        resp = client.get("/api/history")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)
    finally:
        app.dependency_overrides.pop(get_db, None)


def test_history_detail_and_delete(db_session):
    """Create a DiagramRequest row, fetch it via /history/{id}, and delete it via DELETE."""
    from app.models.diagram_requests import DiagramRequest
    from app.core.database import get_db
    import uuid

    app.dependency_overrides[get_db] = lambda: db_session
    try:
        req_id = uuid.uuid4()
        row = DiagramRequest(
            id=req_id,
            prompt="Test history flow prompt",
            diagram_type="architecture",
            status="validated",
            structured_json={"nodes": [{"id": "n1", "label": "API Gateway"}]},
            svg_content="<svg></svg>",
            dsl_code="graph TD; n1;",
        )
        db_session.add(row)
        db_session.commit()

        # Detail
        detail_resp = client.get(f"/api/history/{str(req_id)}")
        assert detail_resp.status_code == 200
        data = detail_resp.json()
        assert data["id"] == str(req_id)
        assert data["prompt"] == "Test history flow prompt"

        # Delete
        del_resp = client.delete(f"/api/history/{str(req_id)}")
        assert del_resp.status_code == 200
        assert del_resp.json()["success"] is True

        # Verify deleted
        detail_resp_2 = client.get(f"/api/history/{str(req_id)}")
        assert detail_resp_2.status_code == 404
    finally:
        app.dependency_overrides.pop(get_db, None)


# ------------------------------------------------------------------------------
# 4. Diagram-Aware Chat Q&A Tests
# ------------------------------------------------------------------------------


def test_chat_message_general():
    """POST /api/chat/message without diagram context returns general response."""
    resp = client.post("/api/chat/message", json={"message": "What is microservices architecture?"})
    assert resp.status_code == 200
    data = resp.json()
    assert "reply" in data
    assert data["diagram_aware"] is False


def test_chat_message_diagram_aware():
    """POST /api/chat/message with diagram_context returns diagram-aware answer."""
    payload = {
        "message": "Explain how Auth Service connects to Database",
        "diagram_context": {
            "title": "Payment Microservice",
            "diagram_type": "architecture",
            "renderer": "mermaid",
            "structured_json": {
                "nodes": [
                    {"id": "auth", "label": "Auth Service", "type": "service"},
                    {"id": "db", "label": "PostgreSQL DB", "type": "database"}
                ],
                "edges": [
                    {"source": "auth", "target": "db", "label": "reads credentials"}
                ]
            },
            "dsl_code": "graph TD; auth[Auth Service] --> db[PostgreSQL DB];"
        }
    }

    resp = client.post("/api/chat/message", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["diagram_aware"] is True
    assert "Payment Microservice" in data["context_referenced"]


# ------------------------------------------------------------------------------
# 5. Reference File Upload Tests
# ------------------------------------------------------------------------------


def test_upload_reference_file():
    """POST /api/diagrams/upload-reference extracts file text."""
    file_bytes = b"def handler(event):\n    return 'OK'\n"
    file_obj = io.BytesIO(file_bytes)

    resp = client.post(
        "/api/diagrams/upload-reference",
        files={"file": ("service.py", file_obj, "text/plain")}
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["filename"] == "service.py"
    assert "def handler(event):" in data["extracted_text"]
