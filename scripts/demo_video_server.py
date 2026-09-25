"""Isolated recording workspace. Never loads real credentials or the live ledger.

Requires .local/video-one/synthea-snapshot.json, a read-only export from HAPI.
Run only on loopback. All accounts below are disposable demonstration accounts.
"""

import json
from pathlib import Path
from uuid import uuid4

from healthops.api import create_app as application
from healthops.auth import NewUser
from healthops.fhir import FhirError
from healthops.providers import ProviderSettings


class SnapshotFhir:
    """Serve actual exported Synthea records without mutating the source server."""

    def __init__(self):
        self.snapshot = json.loads(
            Path(".local/video-one/synthea-snapshot.json").read_text(encoding="utf-8-sig")
        )

    def patients(self):
        return self.snapshot["patients"]

    def record(self, patient_id):
        try:
            return self.snapshot["bundles"][patient_id]
        except KeyError as exc:
            raise FhirError("Patient not in the recording snapshot.", 404) from exc


def create_app():
    app = application(
        db_path=Path(".local/video-one") / f"recording-{uuid4().hex}.sqlite3",
        provider_settings=ProviderSettings(from_environment=False),
        fhir_client=SnapshotFhir(),
    )
    for role in ("admin", "reviewer", "viewer"):
        app.state.auth.create_user(
            NewUser(username=f"demo-{role}", password="isolated-video-demo-password", role=role)
        )
    return app
