"""Live check: repeat import, all resource counts, HealthOps retrieval and human review.

Run from the host's project venv. Creates one simulated screening/review.
"""

import argparse
import json
from datetime import UTC, datetime
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from healthops.fhir import SYNTHEA_TAG, FhirClient
from healthops.synthea import DATA, import_data, save_json


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api-url", default="http://127.0.0.1:18000")
    parser.add_argument("--fhir-url", default="http://127.0.0.1:8080/fhir")
    args = parser.parse_args()
    fhir = FhirClient(args.fhir_url)
    expected = import_data(DATA, fhir, dry_run=True)["resource_counts"]

    def counts():
        params = urlencode(
            {"_summary": "count", "_tag": f"{SYNTHEA_TAG['system']}|{SYNTHEA_TAG['code']}"}
        )
        return {kind: fhir.request(f"{kind}?{params}")["total"] for kind in expected}

    before = counts()
    import_data(DATA, fhir)
    after = counts()
    if before != after or after != expected:
        raise RuntimeError(
            f"Resource count mismatch: expected={expected}, before={before}, after={after}"
        )
    print(f"PASS repeat import: {sum(after.values())} resources, {len(after)} types, no duplicates")

    def api(path, body=None):
        request = Request(
            args.api_url.rstrip("/") + path,
            data=json.dumps(body).encode() if body is not None else None,
            headers={"Content-Type": "application/json"},
        )
        with urlopen(request, timeout=120) as response:
            return json.load(response)

    patients = api("/api/v1/patients?source=hapi")
    if len(patients) != expected["Patient"]:
        raise RuntimeError("HealthOps did not list all imported patients.")
    resource_counts = {}
    for patient in patients:
        patient_id = patient["id"]
        record = api(f"/api/v1/patients/{patient_id}/record")
        patient_resources = [
            e["resource"] for e in record["entry"] if e["resource"]["resourceType"] == "Patient"
        ]
        if len(patient_resources) != 1 or patient_resources[0]["id"] != patient_id:
            raise RuntimeError("Patient identity mismatch in retrieved evidence.")
        resource_counts[patient_id] = len(record["entry"])
    print(f"PASS HealthOps retrieves all {len(patients)} Synthea patients and their evidence")
    screening = api(
        "/api/v1/screenings",
        {
            "source": "hapi",
            "patient_id": patients[0]["id"],
            "trial_id": "DEMO-SYNTHEA-T2D-001",
            "as_of": "2026-09-01",
        },
    )
    if screening["review_status"] != "pending_review" or screening["data_source"] != "hapi":
        raise RuntimeError("Screening source or human-review gate failed.")
    reviewed = api(
        f"/api/v1/screenings/{screening['id']}/reviews",
        {
            "reviewer": "Simulated Synthea smoke test",
            "decision": "request_information",
            "reason": "Synthetic integration test: fictional criteria need human review.",
            "expected_revision": 0,
        },
    )
    saved = api(f"/api/v1/screenings/{screening['id']}")
    if (
        saved["review_status"] != "request_information"
        or saved["source_snapshot"] != screening["source_snapshot"]
        or saved["reviews"] != reviewed["reviews"]
    ):
        raise RuntimeError("Review or source snapshot was not preserved.")
    print("PASS HAPI evidence -> fictional screening -> persisted simulated human review")
    report = {
        "verified_at": datetime.now(UTC).isoformat(),
        "resource_counts": after,
        "patient_evidence_counts": resource_counts,
        "repeat_import": "passed",
        "screening_id": screening["id"],
        "outcome": screening["outcome"],
        "review_status": saved["review_status"],
    }
    save_json(DATA / "verification.json", report)
    print(f"Review: {args.api_url}/api/v1/screenings/{screening['id']}")


if __name__ == "__main__":
    main()
