import pytest
from auth_support import TestClient

from healthops.api import create_app


@pytest.fixture
def client(tmp_path):
    with TestClient(create_app(tmp_path / "reviews.sqlite3")) as client:
        yield client


def new_screening(client):
    response = client.post("/api/v1/screenings", json={"patient_id": "demo-001"})
    assert response.status_code == 201
    return response.json()


def review_request(**overrides):
    return {
        "reviewer": "Demo coordinator",
        "decision": "advance_for_screening",
        "reason": "Reviewed sources; advance for further human screening.",
        "expected_revision": 0,
        **overrides,
    }


def test_human_review_preserves_snapshot_and_prior_reviews(client):
    original = new_screening(client)
    url = f"/api/v1/screenings/{original['id']}/reviews"
    assert original["review_status"] == "pending_review"
    first = client.post(url, json=review_request())
    assert first.status_code == 201
    reviewed = first.json()
    assert reviewed["review_status"] == "advance_for_screening"
    assert reviewed["source_snapshot"] == original["source_snapshot"]
    assert reviewed["reviews"][0]["evidence_hash"] == original["evidence_hash"]
    assert reviewed["reviews"][0]["rules_hash"] == original["rules_hash"]
    assert reviewed["reviews"][0]["identity_verification"] == "authenticated_local_account"
    second = client.post(
        url, json=review_request(expected_revision=1, decision="request_information")
    )
    assert second.status_code == 201
    history = client.get(f"/api/v1/screenings/{original['id']}").json()
    assert history["revision"] == 2
    assert history["review_status"] == "request_information"
    assert history["reviews"][0] == reviewed["reviews"][0]
    assert history["outcome"] == original["outcome"]


def test_stale_review_is_rejected_without_overwriting_history(client):
    original = new_screening(client)
    url = f"/api/v1/screenings/{original['id']}/reviews"
    assert client.post(url, json=review_request()).status_code == 201
    assert client.post(url, json=review_request(decision="dismiss")).status_code == 409
    assert len(client.get(f"/api/v1/screenings/{original['id']}").json()["reviews"]) == 1


@pytest.mark.parametrize(
    "changes",
    [{"reason": "   "}, {"reviewer": " "}, {"decision": "enroll"}, {"expected_revision": -1}],
)
def test_review_requires_reason_label_and_supported_decision(client, changes):
    original = new_screening(client)
    response = client.post(
        f"/api/v1/screenings/{original['id']}/reviews", json=review_request(**changes)
    )
    assert response.status_code == 422


def test_unknown_resources_return_404(client):
    assert client.post("/api/v1/screenings", json={"patient_id": "missing"}).status_code == 404
    assert client.get("/api/v1/screenings/missing").status_code == 404
    assert (
        client.post("/api/v1/screenings/missing/reviews", json=review_request()).status_code == 404
    )


def test_review_survives_app_restart(tmp_path):
    path = tmp_path / "reviews.sqlite3"
    with TestClient(create_app(path)) as client:
        original = new_screening(client)
        client.post(f"/api/v1/screenings/{original['id']}/reviews", json=review_request())
    with TestClient(create_app(path)) as restarted:
        result = restarted.get(f"/api/v1/screenings/{original['id']}").json()
        assert result["revision"] == 1
        assert result["review_status"] == "advance_for_screening"


def test_environment_database_path_persists_across_app_instances(tmp_path, monkeypatch):
    path = tmp_path / "volume" / "reviews.sqlite3"
    monkeypatch.setenv("HEALTHOPS_DB_PATH", str(path))
    with TestClient(create_app()) as client:
        original = new_screening(client)
        client.post(f"/api/v1/screenings/{original['id']}/reviews", json=review_request())
    assert path.is_file()
    with TestClient(create_app()) as restarted:
        result = restarted.get(f"/api/v1/screenings/{original['id']}").json()
        assert result["revision"] == 1
        assert result["review_status"] == "advance_for_screening"


def test_explicit_database_path_overrides_environment(tmp_path, monkeypatch):
    unused = tmp_path / "unused.sqlite3"
    explicit = tmp_path / "explicit.sqlite3"
    monkeypatch.setenv("HEALTHOPS_DB_PATH", str(unused))
    with TestClient(create_app(explicit)) as client:
        new_screening(client)
    assert explicit.is_file()
    assert not unused.exists()
