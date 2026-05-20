from __future__ import annotations

import os
from pathlib import Path

from fastapi.testclient import TestClient

os.environ["API_KEY"] = "test-key"
os.environ["DATABASE_PATH"] = str(Path(__file__).resolve().parents[1] / "data" / "test_app.db")

from app.main import app  # noqa: E402
from app.storage import init_db, seed_demo_calls  # noqa: E402
from app.services.load_service import load_lookup  # noqa: E402

init_db()
seed_demo_calls(load_lookup())

client = TestClient(app)
headers = {"X-API-Key": "test-key"}


def test_auth_required() -> None:
    resp = client.get("/health")
    assert resp.status_code == 401


def test_verify_mock_carrier() -> None:
    resp = client.post("/api/carriers/verify", json={"mc_number": "123456"}, headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["eligible"] is True
    assert body["source"] in {"mock", "fallback", "fmcsa"}


def test_search_loads() -> None:
    resp = client.post(
        "/api/loads/search",
        json={"origin": "Chicago", "destination": "Dallas", "equipment_type": "dry van", "max_results": 3},
        headers=headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["count"] >= 1
    assert body["loads"][0]["load_id"] == "ACME-1001"


def test_evaluate_counter_then_accept() -> None:
    first = client.post(
        "/api/offers/evaluate",
        json={"load_id": "ACME-1001", "mc_number": "123456", "proposed_rate": 2700, "negotiation_round": 1},
        headers=headers,
    )
    assert first.status_code == 200
    assert first.json()["decision"] in {"counter", "accept"}

    second = client.post(
        "/api/offers/evaluate",
        json={"load_id": "ACME-1001", "mc_number": "123456", "proposed_rate": 2525, "negotiation_round": 2},
        headers=headers,
    )
    assert second.status_code == 200
    assert second.json()["decision"] == "accept"


def test_log_and_metrics() -> None:
    resp = client.post(
        "/api/calls/log",
        json={
            "run_id": "pytest-001",
            "mc_number": "123456",
            "carrier_name": "Prairie Star Transport LLC",
            "load_id": "ACME-1001",
            "outcome": "booked_transfer_mocked",
            "sentiment": "positive",
            "initial_offer": 2700,
            "final_offer": 2525,
            "negotiation_rounds": 2,
            "extracted_data": {"summary": "pytest call"},
        },
        headers=headers,
    )
    assert resp.status_code == 200
    metrics = client.get("/api/metrics", headers=headers)
    assert metrics.status_code == 200
    assert metrics.json()["total_calls"] >= 1
