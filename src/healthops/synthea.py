"""Generate a pinned local dataset and import validated transactions into HAPI."""

import argparse
import hashlib
import json
import shutil
import subprocess
from collections import Counter
from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path

from healthops.fhir import FHIR_ID, SYNTHEA_TAG, FhirClient, FhirError

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / ".local" / "synthea"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def generate() -> None:
    if (DATA / "fhir").exists():
        raise ValueError(
            "Output already exists. Use import to reuse it; archive it before regenerating."
        )
    DATA.mkdir(parents=True, exist_ok=True)
    command = ["docker", "compose", "-p", "healthops", "--profile", "data"]
    config = json.loads(subprocess.check_output(command + ["config", "--format", "json"], cwd=ROOT))
    subprocess.run(command + ["run", "--build", "--rm", "synthea"], cwd=ROOT, check=True)
    files = sorted((DATA / "fhir").glob("*.json"))
    if not files:
        raise ValueError("Synthea produced no FHIR JSON files.")
    manifest = {
        "source": "Synthea v4.0.0",
        "synthetic": True,
        "generated_at": datetime.now(UTC).isoformat(),
        "command": config["services"]["synthea"]["command"],
        "generator_dockerfile_sha256": digest(ROOT / "infrastructure" / "synthea.Dockerfile"),
        "files": {path.name: digest(path) for path in files},
    }
    save_json(DATA / "manifest.json", manifest)
    print(f"Generated {len(files)} FHIR files. Manifest: {DATA / 'manifest.json'}")


def prepare(bundles: list[dict]) -> list[dict]:
    """Use source IDs for repeatable PUTs; resolve UUID references without inventing data."""
    mapping, identities = {}, {}
    for bundle in bundles:
        if bundle.get("resourceType") != "Bundle" or not bundle.get("entry"):
            raise ValueError("Expected a nonempty FHIR Bundle.")
        for entry in bundle["entry"]:
            resource = entry.get("resource", {})
            kind, identifier = resource.get("resourceType", ""), resource.get("id", "")
            if not kind.isalpha() or not FHIR_ID.fullmatch(identifier):
                raise ValueError("Resource type or stable FHIR ID is missing/invalid.")
            target = f"{kind}/{identifier}"
            if target in identities and identities[target] != resource:
                raise ValueError(f"Conflicting duplicate source resource: {target}")
            identities[target] = resource
            for identifier in resource.get("identifier", []):
                if identifier.get("system") and identifier.get("value"):
                    alias = f"{kind}?identifier={identifier['system']}|{identifier['value']}"
                    if alias in mapping and mapping[alias] != target:
                        mapping[alias] = None
                    else:
                        mapping[alias] = target
            for alias in (entry.get("fullUrl"),):
                if alias:
                    if alias in mapping and mapping[alias] != target:
                        raise ValueError(f"Ambiguous source reference: {alias}")
                    mapping[alias] = target

    def resolve(value):
        if isinstance(value, list):
            return [resolve(item) for item in value]
        if isinstance(value, dict):
            result = {key: resolve(item) for key, item in value.items()}
            reference = result.get("reference")
            if reference:
                if reference in mapping:
                    if mapping[reference] is None:
                        raise ValueError(f"Ambiguous conditional reference: {reference}")
                    result["reference"] = mapping[reference]
                elif not reference.startswith("#") and reference not in identities:
                    raise ValueError(f"Unresolved reference: {reference}")
            return result
        return value

    transactions = []
    # Shared organizations/practitioners first, then whole patient transactions.
    ordered = sorted(
        bundles, key=lambda b: any(e["resource"]["resourceType"] == "Patient" for e in b["entry"])
    )
    for bundle in ordered:
        entries = []
        for entry in bundle["entry"]:
            resource = resolve(deepcopy(entry["resource"]))
            target = f"{resource['resourceType']}/{resource['id']}"
            tags = resource.setdefault("meta", {}).setdefault("tag", [])
            if SYNTHEA_TAG not in tags:
                tags.append(SYNTHEA_TAG)
            entries.append({"resource": resource, "request": {"method": "PUT", "url": target}})
        transactions.append({"resourceType": "Bundle", "type": "transaction", "entry": entries})
    return transactions


def import_data(directory: Path, client: FhirClient, dry_run: bool = False) -> dict:
    manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    files = sorted((directory / "fhir").glob("*.json"))
    if not files or {p.name: digest(p) for p in files} != manifest["files"]:
        raise ValueError("Generated files differ from the manifest. No data was imported.")
    bundles = []
    for path in files:
        try:
            bundles.append(json.loads(path.read_text(encoding="utf-8")))
        except ValueError:
            quarantine = directory / "quarantine"
            quarantine.mkdir(exist_ok=True)
            shutil.copy2(path, quarantine / path.name)
            raise ValueError(f"Malformed JSON copied to quarantine: {path.name}") from None
    try:
        transactions = prepare(bundles)
    except (ValueError, TypeError, KeyError, AttributeError) as exc:
        save_json(directory / "quarantine" / "validation-error.json", {"error": str(exc)})
        raise ValueError(f"Dataset validation failed before import: {exc}") from exc
    counts = Counter(e["resource"]["resourceType"] for b in transactions for e in b["entry"])
    report = {
        "source": manifest["source"],
        "started_at": datetime.now(UTC).isoformat(),
        "resource_counts": dict(counts),
        "transactions_completed": 0,
        "dry_run": dry_run,
        "status": "validated",
        "fhir_base_url": client.base,
    }
    if dry_run:
        return report
    report_path = directory / "import-report.json"
    save_json(report_path, report)
    try:
        for transaction in transactions:
            response = client.request("", transaction)
            responses = response.get("entry", [])
            if response.get("type") != "transaction-response" or len(responses) != len(
                transaction["entry"]
            ):
                raise FhirError("Incomplete FHIR transaction response.")
            if any(
                not str(e.get("response", {}).get("status", "")).startswith("2") for e in responses
            ):
                raise FhirError("A transaction entry failed.")
            report["transactions_completed"] += 1
            save_json(report_path, report)
    except FhirError as exc:
        report.update(status="failed", error=str(exc))
        save_json(report_path, report)
        raise
    report.update(status="completed", finished_at=datetime.now(UTC).isoformat())
    save_json(report_path, report)
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["generate", "import"])
    parser.add_argument("--directory", type=Path, default=DATA)
    parser.add_argument("--fhir-url", default="http://127.0.0.1:8080/fhir")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    try:
        if args.action == "generate":
            generate()
        else:
            print(
                json.dumps(
                    import_data(args.directory, FhirClient(args.fhir_url), args.dry_run), indent=2
                )
            )
    except (ValueError, FhirError, OSError, subprocess.CalledProcessError) as exc:
        raise SystemExit(f"Synthea pipeline failed: {exc}") from exc


if __name__ == "__main__":
    main()
