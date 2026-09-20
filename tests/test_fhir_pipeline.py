from copy import deepcopy

import pytest
from auth_support import TestClient

from healthops.api import create_app
from healthops.demo_data import SYNTHEA_TRIAL, get_patient
from healthops.fhir import SYNTHEA_TAG, FhirClient, FhirError
from healthops.synthea import prepare


def source_bundle():
    bundle = get_patient("demo-001")
    patient = bundle["entry"][0]["resource"]
    patient["meta"]["tag"] = [SYNTHEA_TAG]
    condition = bundle["entry"][1]["resource"]
    condition["code"]["coding"] = [{"system": "http://snomed.info/sct", "code": "44054006"}]
    lab = bundle["entry"][2]["resource"]
    lab["code"]["coding"] = [{"system": "http://loinc.org", "code": "4548-4"}]
    return bundle


def test_transaction_preserves_ids_resolves_references_and_leaves_raw_unchanged():
    bundle = source_bundle()
    bundle["entry"][0]["fullUrl"] = "urn:uuid:demo-001"
    bundle["entry"][1]["resource"]["subject"]["reference"] = "urn:uuid:demo-001"
    original = deepcopy(bundle)
    transaction = prepare([bundle])[0]
    assert transaction["entry"][0]["request"] == {"method": "PUT", "url": "Patient/demo-001"}
    assert transaction["entry"][1]["resource"]["subject"]["reference"] == "Patient/demo-001"
    assert transaction == prepare([bundle])[0]
    assert bundle == original


def test_unresolved_reference_fails_before_any_import():
    bundle = source_bundle()
    bundle["entry"][1]["resource"]["subject"]["reference"] = "urn:uuid:missing"
    with pytest.raises(ValueError, match="Unresolved"):
        prepare([bundle])


def test_conflicting_duplicate_ids_fail():
    first, second = source_bundle(), source_bundle()
    second["entry"][0]["resource"]["birthDate"] = "2000-01-01"
    with pytest.raises(ValueError, match="Conflicting"):
        prepare([first, second])


def test_conditional_provider_reference_resolves_to_imported_id():
    bundle = source_bundle()
    bundle["entry"].append(
        {
            "resource": {
                "resourceType": "Practitioner",
                "id": "doctor",
                "identifier": [{"system": "urn:npi", "value": "123"}],
            }
        }
    )
    bundle["entry"][1]["resource"]["asserter"] = {
        "reference": "Practitioner?identifier=urn:npi|123"
    }
    transaction = prepare([bundle])[0]
    assert transaction["entry"][1]["resource"]["asserter"]["reference"] == "Practitioner/doctor"


def test_import_rejects_changed_files_without_network(tmp_path):
    from healthops.synthea import import_data, save_json

    save_json(tmp_path / "manifest.json", {"files": {"patient.json": "wrong-hash"}})
    save_json(tmp_path / "fhir" / "patient.json", source_bundle())
    with pytest.raises(ValueError, match="manifest"):
        import_data(tmp_path, FhirClient())


def test_import_records_partial_failure_and_does_not_report_success(tmp_path, monkeypatch):
    from healthops.synthea import digest, import_data, save_json

    path = tmp_path / "fhir" / "patient.json"
    save_json(path, source_bundle())
    save_json(tmp_path / "manifest.json", {"source": "test", "files": {path.name: digest(path)}})
    fhir = FhirClient()
    monkeypatch.setattr(
        fhir,
        "request",
        lambda *args: {"resourceType": "Bundle", "type": "transaction-response", "entry": []},
    )
    with pytest.raises(FhirError, match="Incomplete"):
        import_data(tmp_path, fhir)
    import json

    report = json.loads((tmp_path / "import-report.json").read_text())
    assert report["status"] == "failed"
    assert report["transactions_completed"] == 0


def page(resources, next_url=None):
    return {
        "resourceType": "Bundle",
        "type": "searchset",
        "entry": [{"resource": r} for r in resources],
        "link": [{"relation": "next", "url": next_url}] if next_url else [],
    }


def test_search_follows_all_pages(monkeypatch):
    client = FhirClient()
    pages = iter(
        [
            page([{"resourceType": "Patient", "id": "a"}], "next"),
            page([{"resourceType": "Patient", "id": "b"}]),
        ]
    )
    monkeypatch.setattr(client, "request", lambda path: next(pages))
    assert [p["id"] for p in client.patients()] == ["a", "b"]


def test_search_rejects_loops(monkeypatch):
    client = FhirClient()
    monkeypatch.setattr(client, "request", lambda path: page([], "next"))
    with pytest.raises(FhirError, match="loop"):
        client.patients()


def test_pagination_cannot_access_another_server():
    with pytest.raises(FhirError, match="configured server"):
        FhirClient().request("https://example.com/private")


def test_record_rejects_wrong_patient_evidence(monkeypatch):
    client = FhirClient()
    monkeypatch.setattr(client, "patient", lambda pid: source_bundle()["entry"][0]["resource"])
    monkeypatch.setattr(
        client,
        "search",
        lambda *a, **kw: [
            {"resourceType": "Condition", "subject": {"reference": "Patient/somebody-else"}}
        ],
    )
    with pytest.raises(FhirError, match="reference mismatch"):
        client.record("demo-001")


def test_hapi_screening_and_human_review_use_imported_snapshot(tmp_path, monkeypatch):
    fhir = FhirClient()
    monkeypatch.setattr(fhir, "record", lambda pid: source_bundle())
    with TestClient(create_app(tmp_path / "reviews.db", fhir)) as client:
        created = client.post(
            "/api/v1/screenings",
            json={"source": "hapi", "patient_id": "demo-001", "trial_id": SYNTHEA_TRIAL["id"]},
        )
        assert created.status_code == 201
        screening = created.json()
        assert screening["outcome"] == "all_modeled_criteria_met"
        assert screening["data_source"] == "hapi"
        assert screening["review_status"] == "pending_review"
        response = client.post(
            f"/api/v1/screenings/{screening['id']}/reviews",
            json={
                "reviewer": "Integration test",
                "decision": "request_information",
                "reason": "Fictional criteria still need human interpretation.",
                "expected_revision": 0,
            },
        )
        assert response.status_code == 201
        assert response.json()["source_snapshot"] == screening["source_snapshot"]


def test_hapi_failure_does_not_fall_back_to_fixtures(tmp_path, monkeypatch):
    fhir = FhirClient()

    def unavailable(pid):
        raise FhirError("Unavailable")

    monkeypatch.setattr(fhir, "record", unavailable)
    with TestClient(create_app(tmp_path / "reviews.db", fhir)) as client:
        response = client.post(
            "/api/v1/screenings",
            json={"source": "hapi", "patient_id": "demo-001", "trial_id": SYNTHEA_TRIAL["id"]},
        )
        assert response.status_code == 502


def test_wrong_code_system_does_not_match():
    from datetime import date

    from healthops.screening import screen_patient

    bundle = source_bundle()
    bundle["entry"][2]["resource"]["code"]["coding"][0]["system"] = "urn:wrong-system"
    result = screen_patient(bundle, SYNTHEA_TRIAL, date(2026, 9, 1))
    assert result["criteria"][2]["status"] == "unknown"
