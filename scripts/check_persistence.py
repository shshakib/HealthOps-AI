"""Seed or verify labeled synthetic records across a Compose down/up cycle.

Run inside the HealthOps container. The seed action creates a FHIR test patient
and a simulated review, then saves their IDs in the review volume.
"""

import argparse
import json
import os
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request, urlopen
from uuid import uuid4

HEALTHOPS = "http://127.0.0.1:8000"


def request_json(url: str, data: dict | None = None, method: str | None = None) -> dict:
    request = Request(
        url,
        data=json.dumps(data).encode() if data is not None else None,
        method=method,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
    )
    with urlopen(request, timeout=30) as response:
        return json.load(response)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["seed", "verify"])
    args = parser.parse_args()
    fhir = os.environ.get("FHIR_BASE_URL", "http://hapi:8080/fhir").rstrip("/")
    database = Path(os.environ.get("HEALTHOPS_DB_PATH", ".local/healthops.sqlite3"))
    state_path = database.parent / "docker-persistence-check.json"

    if args.action == "seed":
        patient_id = f"healthops-smoke-{uuid4().hex}"
        identifier = [{"system": "urn:healthops:docker-smoke", "value": patient_id}]
        request_json(
            f"{fhir}/Patient/{patient_id}",
            {
                "resourceType": "Patient",
                "id": patient_id,
                "identifier": identifier,
                "name": [{"text": "Synthetic Docker Persistence Test"}],
                "active": True,
            },
            method="PUT",
        )
        screening = request_json(f"{HEALTHOPS}/api/v1/screenings", {"patient_id": "demo-002"})
        reviewed = request_json(
            f"{HEALTHOPS}/api/v1/screenings/{screening['id']}/reviews",
            {
                "reviewer": "Automated Docker persistence test (synthetic)",
                "decision": "request_information",
                "reason": "Simulated review for testing persistent Docker storage.",
                "expected_revision": 0,
            },
        )
        state_path.write_text(
            json.dumps(
                {
                    "patient_id": patient_id,
                    "identifier": identifier,
                    "screening_id": screening["id"],
                    "review_id": reviewed["reviews"][0]["id"],
                    "evidence_hash": screening["evidence_hash"],
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        print("Created labeled synthetic FHIR patient and simulated review.")
        print("Run compose down/up without --volumes, then run this script with verify.")
        return

    state = json.loads(state_path.read_text(encoding="utf-8"))
    patient = request_json(f"{fhir}/Patient/{state['patient_id']}")
    if patient.get("identifier") != state["identifier"]:
        raise RuntimeError("FHIR patient did not retain its original identifier.")
    reviewed = request_json(f"{HEALTHOPS}/api/v1/screenings/{state['screening_id']}")
    if reviewed.get("evidence_hash") != state["evidence_hash"]:
        raise RuntimeError("Screening evidence changed across the restart.")
    if not any(event["id"] == state["review_id"] for event in reviewed.get("reviews", [])):
        raise RuntimeError("The original review event is missing.")
    print("PASS FHIR patient persisted in PostgreSQL")
    print("PASS screening snapshot and review event persisted in the HealthOps volume")


if __name__ == "__main__":
    try:
        main()
    except (URLError, OSError, RuntimeError, KeyError, json.JSONDecodeError) as exc:
        raise SystemExit(f"Persistence check failed: {exc}") from exc
