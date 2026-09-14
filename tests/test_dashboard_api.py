from fastapi.testclient import TestClient

from healthops.api import create_app


def test_history_is_compact_paginated_and_uses_latest_decision(tmp_path):
    with TestClient(create_app(tmp_path / "reviews.db")) as client:
        first = client.post("/api/v1/screenings", json={"patient_id": "demo-001"}).json()
        second = client.post("/api/v1/screenings", json={"patient_id": "demo-002"}).json()
        client.post(
            f"/api/v1/screenings/{first['id']}/reviews",
            json={
                "reviewer": "Test reviewer",
                "reason": "Additional patient evidence is needed.",
                "decision": "request_information",
                "expected_revision": 0,
            },
        )
        history = client.get("/api/v1/screenings?limit=1").json()
        assert history["total"] == 2 and history["pending_count"] == 1
        assert history["items"][0]["id"] == second["id"]
        assert "source_snapshot" not in history["items"][0]
        older = client.get("/api/v1/screenings?limit=1&offset=1").json()
        assert older["items"][0]["review_status"] == "request_information"
        assert client.get("/api/v1/screenings?limit=0").status_code == 422
        assert client.get("/api/v1/screenings?offset=-1").status_code == 422


def test_fixture_record_selection_is_explicit(tmp_path):
    with TestClient(create_app(tmp_path / "reviews.db")) as client:
        patients = client.get("/api/v1/patients?source=fixtures").json()
        assert patients[0]["name"] and patients[0]["birthDate"]
        record = client.get("/api/v1/patients/demo-001/record?source=fixtures")
        assert record.status_code == 200
        assert record.json()["entry"][0]["resource"]["id"] == "demo-001"
        assert client.get("/api/v1/patients/missing/record?source=fixtures").status_code == 404
