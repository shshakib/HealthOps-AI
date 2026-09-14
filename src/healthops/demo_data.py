"""Handcrafted FHIR-shaped fixtures, not Synthea output or clinical recommendations.

The fictional code system and trial thresholds exist only to test program behavior.
Full FHIR profile/terminology validation and actual registry imports are later milestones.
"""

from copy import deepcopy

DEMO_AS_OF = "2026-09-01"
CODE_SYSTEM = "urn:healthops:fictional-demo"
TRIAL = {
    "id": "DEMO-T2D-001",
    "title": "Fictional diabetes screening exercise",
    "version": "demo-rules-v1",
    "fictional": True,
    "source": "Bundled fictional rules, not a registered clinical trial",
    "age_min": 40,
    "age_max": 75,
    "condition_code": "demo-type-2-diabetes",
    "lab_code": "demo-hba1c",
    "lab_min": 7.0,
    "lab_max": 10.0,
    "lab_unit": "%",
    "lab_max_age_days": 90,
}

# Real terminology identifiers with deliberately fictional thresholds.
SYNTHEA_TRIAL = {
    **TRIAL,
    "id": "DEMO-SYNTHEA-T2D-001",
    "title": "Fictional screening exercise using Synthea records",
    "version": "synthea-demo-rules-v1",
    "condition_system": "http://snomed.info/sct",
    "condition_code": "44054006",
    "lab_system": "http://loinc.org",
    "lab_code": "4548-4",
}


def _bundle(patient_id: str, *, observed: str, value: float) -> dict:
    patient_ref = f"Patient/{patient_id}"
    resources = [
        {
            "resourceType": "Patient",
            "id": patient_id,
            "meta": {"versionId": "1"},
            "name": [{"text": f"Synthetic {patient_id}"}],
            "birthDate": "1968-04-01",
        },
        {
            "resourceType": "Condition",
            "id": f"{patient_id}-condition",
            "subject": {"reference": patient_ref},
            "clinicalStatus": {"coding": [{"code": "active"}]},
            "verificationStatus": {"coding": [{"code": "confirmed"}]},
            "code": {"coding": [{"system": CODE_SYSTEM, "code": "demo-type-2-diabetes"}]},
            "recordedDate": "2025-01-01",
        },
        {
            "resourceType": "Observation",
            "id": f"{patient_id}-lab",
            "subject": {"reference": patient_ref},
            "status": "final",
            "code": {"coding": [{"system": CODE_SYSTEM, "code": "demo-hba1c"}]},
            "effectiveDateTime": observed,
            "valueQuantity": {
                "value": value,
                "unit": "%",
                "system": "http://unitsofmeasure.org",
                "code": "%",
            },
        },
    ]
    return {
        "resourceType": "Bundle",
        "type": "collection",
        "id": f"demo-{patient_id}",
        "entry": [{"resource": resource} for resource in resources],
    }


PATIENTS = {
    "demo-001": _bundle("demo-001", observed="2026-08-15", value=8.2),
    "demo-002": _bundle("demo-002", observed="2025-08-15", value=8.2),
    "demo-003": _bundle("demo-003", observed="2026-08-15", value=11.2),
}


def get_patient(patient_id: str) -> dict:
    """Return isolated input so callers cannot mutate the bundled fixture."""
    return deepcopy(PATIENTS[patient_id])
