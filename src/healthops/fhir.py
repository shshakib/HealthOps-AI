"""Small FHIR R4 client for the private synthetic-data HAPI instance."""

import json
import os
import re
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urljoin, urlsplit
from urllib.request import Request, urlopen

SYNTHEA_TAG = {"system": "urn:healthops:data-source", "code": "synthea"}
FHIR_ID = re.compile(r"[A-Za-z0-9\-.]{1,64}\Z")


class FhirError(Exception):
    def __init__(self, message: str, status: int = 502):
        super().__init__(message)
        self.status = status


class FhirClient:
    def __init__(self, base_url: str | None = None):
        self.base = (base_url or os.getenv("FHIR_BASE_URL", "http://127.0.0.1:8080/fhir")).rstrip(
            "/"
        )

    def request(self, path: str, body: dict | None = None) -> dict:
        url = urljoin(self.base + "/", path)
        base, target = urlsplit(self.base), urlsplit(url)
        if (target.scheme, target.netloc) != (base.scheme, base.netloc) or not (
            target.path == base.path or target.path.startswith(base.path + "/")
        ):
            raise FhirError("FHIR pagination left the configured server.")
        request = Request(
            url,
            data=json.dumps(body).encode() if body is not None else None,
            headers={"Accept": "application/fhir+json", "Content-Type": "application/fhir+json"},
        )
        try:
            with urlopen(request, timeout=120) as response:
                result = json.load(response)
            if not isinstance(result, dict) or result.get("resourceType") == "OperationOutcome":
                raise FhirError("FHIR returned an unexpected response.")
            return result
        except HTTPError as exc:
            raise FhirError(
                "FHIR resource not found."
                if exc.code == 404
                else f"FHIR request failed (HTTP {exc.code}).",
                404 if exc.code == 404 else 502,
            ) from exc
        except (URLError, TimeoutError, ValueError) as exc:
            raise FhirError("FHIR server unavailable or returned invalid JSON.") from exc

    def search(self, resource_type: str, **params: str) -> list[dict]:
        path = resource_type + "?" + urlencode({"_count": "100", **params})
        resources, seen = [], set()
        for _ in range(1000):
            if path in seen:
                raise FhirError("FHIR pagination loop; incomplete data was discarded.")
            seen.add(path)
            page = self.request(path)
            if page.get("resourceType") != "Bundle" or page.get("type") != "searchset":
                raise FhirError("Expected a FHIR search Bundle.")
            for entry in page.get("entry", []):
                resource = entry.get("resource", {})
                if resource.get("resourceType") != resource_type:
                    raise FhirError("Unexpected resource in FHIR search results.")
                resources.append(resource)
            path = next(
                (link["url"] for link in page.get("link", []) if link.get("relation") == "next"),
                None,
            )
            if not path:
                return resources
        raise FhirError("FHIR page limit exceeded; incomplete data was discarded.")

    def patients(self) -> list[dict]:
        return self.search("Patient", _tag=f"{SYNTHEA_TAG['system']}|{SYNTHEA_TAG['code']}")

    def patient(self, patient_id: str) -> dict:
        if not FHIR_ID.fullmatch(patient_id):
            raise FhirError("Invalid FHIR patient ID.", 422)
        patient = self.request(f"Patient/{patient_id}")
        if patient.get("resourceType") != "Patient" or patient.get("id") != patient_id:
            raise FhirError("FHIR patient identity mismatch.")
        if SYNTHEA_TAG not in patient.get("meta", {}).get("tag", []):
            raise FhirError("Patient is outside the imported Synthea demo dataset.", 404)
        return patient

    def record(self, patient_id: str) -> dict:
        patient = self.patient(patient_id)
        reference = f"Patient/{patient_id}"
        resources = [patient]
        for kind in ("Condition", "Observation"):
            for resource in self.search(kind, patient=patient_id):
                if resource.get("subject", {}).get("reference") != reference:
                    raise FhirError("Patient reference mismatch; incomplete data was discarded.")
                resources.append(resource)
        return {
            "resourceType": "Bundle",
            "type": "collection",
            "entry": [{"resource": item} for item in resources],
        }
