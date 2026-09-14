"""Verify local registry snapshots and prepare drafts without approving them."""

import argparse
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api-url", default="http://127.0.0.1:18000")
    args = parser.parse_args()

    def api(path, body=None):
        request = Request(
            args.api_url.rstrip("/") + path,
            data=json.dumps(body).encode() if body is not None else None,
            headers={"Content-Type": "application/json"},
        )
        with urlopen(request, timeout=60) as response:
            return json.load(response)

    trials = api("/api/v1/trials?source=registry")
    if len(trials) < 3:
        raise RuntimeError("Expected the three curated registry snapshots.")
    patient = api("/api/v1/patients?source=hapi")[0]
    results = []
    for trial in trials:
        snapshot = api(f"/api/v1/trials/{trial['id']}/snapshot")
        if snapshot["snapshot_id"] != trial["snapshot_id"] or not trial["retrieved_at"]:
            raise RuntimeError("Registry source attribution missing or inconsistent.")
        draft = api(f"/api/v1/trials/{trial['id']}/rule-sets/draft", {})
        expected_hash = hashlib.sha256(
            json.dumps(draft["document"], sort_keys=True).encode()
        ).hexdigest()
        if expected_hash != draft["rules_hash"]:
            raise RuntimeError("Interpretation hash mismatch.")
        gate = "already_reviewed_not_modified"
        if draft["status"] != "approved":
            try:
                api(
                    "/api/v1/screenings",
                    {
                        "source": "hapi",
                        "patient_id": patient["id"],
                        "trial_id": trial["id"],
                        "rule_set_id": draft["id"],
                        "as_of": "2026-09-01",
                    },
                )
            except HTTPError as exc:
                if exc.code != 409:
                    raise
                gate = "unapproved_screening_blocked"
            else:
                raise RuntimeError("Unapproved rules were incorrectly allowed to screen.")
        results.append(
            {
                "trial_id": trial["id"],
                "rule_set_id": draft["id"],
                "rules_hash": draft["rules_hash"],
                "status": draft["status"],
                "gate": gate,
            }
        )
        print(f"PASS {trial['id']}: saved snapshot, sourced draft, {gate}")
    path = Path(".local/trials-verification.json")
    path.parent.mkdir(exist_ok=True)
    path.write_text(
        json.dumps({"verified_at": datetime.now(UTC).isoformat(), "studies": results}, indent=2)
        + "\n",
        encoding="utf-8",
    )
    print("No rule approvals or participant decisions were submitted.")


if __name__ == "__main__":
    main()
