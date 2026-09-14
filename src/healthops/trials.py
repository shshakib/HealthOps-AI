"""Versioned, offline ClinicalTrials.gov snapshots. No patient data is sent upstream."""

import argparse
import hashlib
import json
import os
import re
from datetime import UTC, datetime
from pathlib import Path
from urllib.request import Request, urlopen

NCT_ID = re.compile(r"NCT\d{8}\Z")
SNAPSHOT_ID = re.compile(r"[a-f0-9]{64}\Z")
DEFAULT_DIRECTORY = Path(__file__).resolve().parents[2] / "data" / "clinicaltrials"
CURATED = {
    "NCT07247084": "Negative example: a diabetes search result that excludes diabetes.",
    "NCT06591286": "T2D study with dated HbA1c and treatment requirements needing review.",
    "NCT06750497": "Mixed healthy/T2D cohort; ambiguous source BMI wording remains manual.",
}


class TrialCatalog:
    def __init__(self, directory: Path | None = None):
        self.directory = directory or Path(os.getenv("HEALTHOPS_TRIAL_DIR", DEFAULT_DIRECTORY))

    def snapshot(self, nct_id: str, snapshot_id: str | None = None) -> dict:
        if not NCT_ID.fullmatch(nct_id):
            raise KeyError("Invalid study ID.")
        root = self.directory / nct_id
        try:
            if snapshot_id is None:
                snapshot_id = json.loads((root / "latest.json").read_text())["snapshot_id"]
            if not SNAPSHOT_ID.fullmatch(snapshot_id):
                raise KeyError("Invalid snapshot ID.")
            raw = (root / snapshot_id / "study.json").read_bytes()
            meta = json.loads((root / snapshot_id / "snapshot.json").read_text())
        except FileNotFoundError as exc:
            raise KeyError("Study snapshot not found; import it first.") from exc
        if hashlib.sha256(raw).hexdigest() != snapshot_id or meta["snapshot_id"] != snapshot_id:
            raise ValueError("Stored study snapshot failed its integrity check.")
        study = json.loads(raw)
        if study["protocolSection"]["identificationModule"]["nctId"] != nct_id:
            raise ValueError("Stored study identity mismatch.")
        return {**meta, "study": study}

    def summary(self, nct_id: str) -> dict:
        snapshot = self.snapshot(nct_id)
        protocol = snapshot["study"]["protocolSection"]
        status = protocol["statusModule"]
        retrieved = datetime.fromisoformat(snapshot["retrieved_at"])
        return {
            "id": nct_id,
            "fictional": False,
            "source": "ClinicalTrials.gov snapshot",
            "title": protocol["identificationModule"]["briefTitle"],
            "snapshot_id": snapshot["snapshot_id"],
            "source_url": snapshot["source_url"],
            "retrieved_at": snapshot["retrieved_at"],
            "snapshot_age_days": max(0, (datetime.now(UTC) - retrieved).days),
            "registry_last_update": status.get("lastUpdatePostDateStruct", {}).get("date"),
            "recruitment_status_at_snapshot": status.get("overallStatus", "UNKNOWN"),
            "conditions": protocol.get("conditionsModule", {}).get("conditions", []),
            "selection_reason": snapshot.get("selection_reason"),
            "notice": "Saved registry information, not confirmation of current site recruitment. "
            "Search relevance does not establish eligibility. Rule approval is separate.",
        }

    def list(self) -> list[dict]:
        if not self.directory.exists():
            return []
        return [
            self.summary(path.name)
            for path in sorted(self.directory.iterdir())
            if path.is_dir() and NCT_ID.fullmatch(path.name)
        ]

    def import_study(self, nct_id: str) -> dict:
        if not NCT_ID.fullmatch(nct_id):
            raise ValueError("Expected an NCT identifier with eight digits.")
        url = f"https://clinicaltrials.gov/api/v2/studies/{nct_id}"
        request = Request(
            url, headers={"Accept": "application/json", "User-Agent": "HealthOps-portfolio/0.1"}
        )
        with urlopen(request, timeout=60) as response:
            raw = response.read()
        study = json.loads(raw)
        protocol = study["protocolSection"]
        if protocol["identificationModule"]["nctId"] != nct_id:
            raise ValueError("Registry returned a different study ID.")
        if not protocol.get("eligibilityModule", {}).get("eligibilityCriteria"):
            raise ValueError("Study has no eligibility text; manual selection required.")
        snapshot_id = hashlib.sha256(raw).hexdigest()
        root = self.directory / nct_id
        destination = root / snapshot_id
        if not all((destination / name).exists() for name in ("study.json", "snapshot.json")):
            destination.mkdir(parents=True, exist_ok=True)
            (destination / "study.json").write_bytes(raw)
            meta = {
                "id": nct_id,
                "snapshot_id": snapshot_id,
                "retrieved_at": datetime.now(UTC).isoformat(),
                "api_url": url,
                "source_url": f"https://clinicaltrials.gov/study/{nct_id}",
                "selection_reason": CURATED.get(nct_id, "Manually selected study ID."),
            }
            (destination / "snapshot.json").write_text(
                json.dumps(meta, indent=2) + "\n", encoding="utf-8"
            )
        # Only advertise a snapshot after its content has been validated and saved.
        self.snapshot(nct_id, snapshot_id)
        temporary = root / "latest.tmp"
        temporary.write_text(json.dumps({"snapshot_id": snapshot_id}) + "\n", encoding="utf-8")
        temporary.replace(root / "latest.json")
        return self.summary(nct_id)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["import", "list"])
    parser.add_argument("--ids", nargs="+", default=list(CURATED))
    parser.add_argument("--directory", type=Path, default=DEFAULT_DIRECTORY)
    args = parser.parse_args()
    catalog = TrialCatalog(args.directory)
    if args.action == "import":
        for nct_id in args.ids:
            result = catalog.import_study(nct_id)
            print(
                f"Saved {nct_id}: {result['snapshot_id']} "
                f"({result['recruitment_status_at_snapshot']})"
            )
    else:
        print(json.dumps(catalog.list(), indent=2))


if __name__ == "__main__":
    main()
