"""Isolated browser-test API. Shares read-only FHIR inputs, never the live review ledger."""

import os
from pathlib import Path
from uuid import uuid4

from healthops.api import create_app as application
from healthops.auth import NewUser
from healthops.demo_data import PATIENTS, SYNTHEA_TRIAL, get_patient
from healthops.fhir import FhirError
from healthops.providers import ProviderSettings


class FixtureFhir:
    """CI-only stand-in for the FHIR boundary; these records are handcrafted, not Synthea."""

    def patients(self):
        return [get_patient(identifier)["entry"][0]["resource"] for identifier in PATIENTS]

    def record(self, patient_id):
        if patient_id not in PATIENTS:
            raise FhirError("CI fixture patient not found.", 404)
        bundle = get_patient(patient_id)
        for entry in bundle["entry"]:
            resource = entry["resource"]
            prefix = {"Condition": "condition", "Observation": "lab"}.get(resource["resourceType"])
            if prefix:
                resource["code"]["coding"] = [
                    {
                        "system": SYNTHEA_TRIAL[f"{prefix}_system"],
                        "code": SYNTHEA_TRIAL[f"{prefix}_code"],
                    }
                ]
        return bundle


def create_app():
    # UI tests never inherit real model credentials from the user's environment.
    app = application(
        Path(".local") / f"dashboard-test-{uuid4().hex}.sqlite3",
        provider_settings=ProviderSettings(from_environment=False),
        fhir_client=FixtureFhir() if os.environ.get("HEALTHOPS_UI_FIXTURES") == "1" else None,
    )
    for role in ("admin", "reviewer", "viewer"):
        app.state.auth.create_user(
            NewUser(username=f"ui-{role}", password="isolated-browser-test-password", role=role)
        )
    return app
