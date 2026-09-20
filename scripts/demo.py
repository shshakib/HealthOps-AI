"""Exercise the running local API with clearly labeled synthetic smoke-test reviews.

Start `python -m healthops` first. Each run adds three screening snapshots and one
simulated review to the local demo ledger; it does not contact external services.
"""

import json
import os
from urllib.error import HTTPError, URLError
from urllib.request import Request

from healthops.cli_session import signed_in_opener

BASE_URL = os.environ.get("HEALTHOPS_API_URL", "http://127.0.0.1:8000")
opener = None
DISPLAY_BASE_URL = os.environ.get("HEALTHOPS_PUBLIC_URL", BASE_URL).rstrip("/")


def call(path: str, payload: dict | None = None) -> tuple[int, dict]:
    request = Request(
        BASE_URL + path,
        data=json.dumps(payload).encode() if payload is not None else None,
        headers={"Content-Type": "application/json", "X-HealthOps-Request": "1"},
    )
    try:
        with opener.open(request, timeout=30) as response:
            return response.status, json.load(response)
    except HTTPError as exc:
        return exc.code, json.load(exc)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def main() -> None:
    global opener
    opener = signed_in_opener(BASE_URL)
    status, health = call("/health")
    require(status == 200 and health.get("mode") == "synthetic_local_demo", "Wrong API mode.")
    scenarios = {
        "demo-001": "all_modeled_criteria_met",
        "demo-002": "insufficient_evidence",
        "demo-003": "criteria_not_met",
    }
    results = {}
    for patient_id, expected in scenarios.items():
        status, result = call(
            "/api/v1/screenings",
            {"patient_id": patient_id, "trial_id": "DEMO-T2D-001", "as_of": "2026-09-01"},
        )
        require(status == 201, f"Screening failed: {result}")
        require(result["outcome"] == expected, f"Unexpected outcome for {patient_id}.")
        require(result["review_status"] == "pending_review", "Screening advanced automatically.")
        results[patient_id] = result
        print(f"PASS {patient_id}: {expected}; pending human review")

    original = results["demo-002"]
    review_path = f"/api/v1/screenings/{original['id']}/reviews"
    review = {
        "reviewer": "Automated setup smoke test (synthetic)",
        "decision": "request_information",
        "reason": "Simulated review for setup verification: the fixture's lab result is stale.",
        "expected_revision": 0,
    }
    status, reviewed = call(review_path, review)
    require(status == 201, f"Simulated review failed: {reviewed}")
    require(reviewed["review_status"] == "request_information", "Review decision was not saved.")
    require(reviewed["source_snapshot"] == original["source_snapshot"], "Source snapshot changed.")
    print("PASS simulated review saved with original evidence")

    status, _ = call(review_path, review)
    require(status == 409, "A stale review submission was not rejected.")
    status, saved = call(f"/api/v1/screenings/{original['id']}")
    require(status == 200 and len(saved["reviews"]) == 1, "Unexpected review history.")
    print("PASS stale review rejected; earlier decision preserved")
    print(f"Review snapshot: {DISPLAY_BASE_URL}/api/v1/screenings/{original['id']}")
    print(f"Try your own review: {DISPLAY_BASE_URL}/docs")


if __name__ == "__main__":
    try:
        main()
    except (URLError, RuntimeError, KeyError, json.JSONDecodeError) as exc:
        raise SystemExit(f"Demo failed: {exc}. Ensure the HealthOps API is running.") from exc
