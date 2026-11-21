import uuid

import pytest
from fastapi import HTTPException

from src.triage import routes


def test_submit_job_returns_pending_job(monkeypatch):
    job_id = uuid.uuid4()

    def fake_create_job(ticket_text, idempotency_key):
        assert ticket_text == "Payment failed"
        assert idempotency_key == "test-key-001"
        return {"id": job_id, "status": "pending"}

    monkeypatch.setattr(routes, "create_job", fake_create_job)

    response = routes.submit_triage_job(
        routes.TriageRequest(text="Payment failed"),
        idempotency_key="test-key-001",
    )

    assert response["job_id"] == str(job_id)
    assert response["status"] == "pending"
    assert response["status_url"] == f"/triage/jobs/{job_id}"


def test_submit_job_rejects_idempotency_conflict(monkeypatch):
    def fake_create_job(ticket_text, idempotency_key):
        raise routes.IdempotencyConflict(
            "This idempotency key was already used."
        )

    monkeypatch.setattr(routes, "create_job", fake_create_job)

    with pytest.raises(HTTPException) as exc:
        routes.submit_triage_job(
            routes.TriageRequest(text="Different ticket"),
            idempotency_key="existing-key",
        )

    assert exc.value.status_code == 409


def test_get_job_returns_status(monkeypatch):
    job_id = str(uuid.uuid4())

    monkeypatch.setattr(
        routes,
        "get_job",
        lambda requested_id: {
            "id": requested_id,
            "status": "completed",
            "result": {"category": "billing"},
            "error": None,
            "attempts": 1,
            "max_attempts": 3,
            "created_at": "created",
            "updated_at": "updated",
            "completed_at": "completed",
        },
    )

    response = routes.get_triage_job(uuid.UUID(job_id))

    assert response["job_id"] == job_id
    assert response["status"] == "completed"
    assert response["result"]["category"] == "billing"


def test_get_job_returns_404_when_missing(monkeypatch):
    monkeypatch.setattr(routes, "get_job", lambda job_id: None)

    with pytest.raises(HTTPException) as exc:
        routes.get_triage_job(uuid.uuid4())

    assert exc.value.status_code == 404
