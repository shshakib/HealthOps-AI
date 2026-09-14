"""Read-only connectivity check, run inside the HealthOps Compose container."""

import json
import os
from urllib.error import URLError
from urllib.request import Request, urlopen


def read_json(url: str) -> dict:
    request = Request(url, headers={"Accept": "application/fhir+json, application/json"})
    with urlopen(request, timeout=20) as response:
        return json.load(response)


def main() -> None:
    health = read_json("http://127.0.0.1:8000/health")
    if health.get("status") != "ok":
        raise RuntimeError("HealthOps health check failed.")
    print("PASS HealthOps API is responding")

    base = os.environ.get("FHIR_BASE_URL", "http://hapi:8080/fhir").rstrip("/")
    metadata = read_json(f"{base}/metadata")
    if metadata.get("resourceType") != "CapabilityStatement":
        raise RuntimeError("The FHIR endpoint did not return a CapabilityStatement.")
    if metadata.get("fhirVersion") != "4.0.1":
        raise RuntimeError(f"Expected FHIR R4, received {metadata.get('fhirVersion')}.")
    print("PASS HealthOps container can reach HAPI FHIR R4")

    patients = read_json(f"{base}/Patient?_summary=count")
    if patients.get("resourceType") != "Bundle" or not isinstance(patients.get("total"), int):
        raise RuntimeError("HAPI patient search did not return a count Bundle.")
    print(f"PASS HAPI patient search works; stored patients: {patients['total']}")
    print("Use source=hapi for imported Synthea patients; source=fixtures keeps the original demo.")


if __name__ == "__main__":
    try:
        main()
    except (URLError, RuntimeError, json.JSONDecodeError) as exc:
        raise SystemExit(f"Stack check failed: {exc}") from exc
