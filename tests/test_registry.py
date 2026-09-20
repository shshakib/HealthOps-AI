import hashlib
import json
from copy import deepcopy
from datetime import date
from io import BytesIO

import pytest
from auth_support import TestClient

from healthops.api import create_app
from healthops.demo_data import get_patient
from healthops.fhir import FhirClient
from healthops.store import ReviewStore
from healthops.trial_rules import RuleProposal, draft_proposal, screen_registry, validate_proposal
from healthops.trials import TrialCatalog

NCT = "NCT01234567"
TEXT = "Inclusion: Documented type 2 diabetes. Exclusion: Documented type 2 diabetes."


def write_snapshot(root, *, title="Fictional registry test fixture", minimum="18 Years"):
    study = {
        "protocolSection": {
            "identificationModule": {"nctId": NCT, "briefTitle": title},
            "statusModule": {
                "overallStatus": "RECRUITING",
                "lastUpdatePostDateStruct": {"date": "2025-01-01"},
            },
            "eligibilityModule": {
                "eligibilityCriteria": TEXT,
                "minimumAge": minimum,
                "maximumAge": "80 Years",
                "sex": "ALL",
            },
        }
    }
    raw = json.dumps(study).encode()
    identifier = hashlib.sha256(raw).hexdigest()
    directory = root / NCT / identifier
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "study.json").write_bytes(raw)
    meta = {
        "id": NCT,
        "snapshot_id": identifier,
        "retrieved_at": "2026-09-01T00:00:00+00:00",
        "source_url": f"https://clinicaltrials.gov/study/{NCT}",
    }
    (directory / "snapshot.json").write_text(json.dumps(meta))
    (root / NCT / "latest.json").write_text(json.dumps({"snapshot_id": identifier}))
    return TrialCatalog(root)


@pytest.fixture
def catalog(tmp_path):
    return write_snapshot(tmp_path / "registry")


def proposal(catalog, direction="inclusion"):
    return RuleProposal(
        snapshot_id=catalog.snapshot(NCT)["snapshot_id"],
        rules=[
            {
                "id": "condition",
                "kind": "condition",
                "direction": direction,
                "label": "Test condition component",
                "source_text": "Documented type 2 diabetes.",
                "code": "44054006",
            }
        ],
    )


def patient_bundle():
    bundle = get_patient("demo-001")
    condition = bundle["entry"][1]["resource"]
    condition["code"]["coding"] = [{"system": "http://snomed.info/sct", "code": "44054006"}]
    condition["clinicalStatus"]["coding"][0]["system"] = (
        "http://terminology.hl7.org/CodeSystem/condition-clinical"
    )
    condition["verificationStatus"]["coding"][0]["system"] = (
        "http://terminology.hl7.org/CodeSystem/condition-ver-status"
    )
    return bundle


def approval(rules, **changes):
    return {
        "reviewer": "Simulated test reviewer",
        "decision": "approve",
        "reason": "Test-only review of the partial interpretation.",
        "expected_rules_hash": rules["rules_hash"],
        **changes,
    }


def approved_rules(catalog, path, direction="inclusion"):
    store = ReviewStore(path)
    draft = store.save_rule_set(
        validate_proposal(catalog.snapshot(NCT), proposal(catalog, direction))
    )
    return store.review_rule_set(draft["id"], approval(draft))


@pytest.mark.parametrize("direction,expected", [("inclusion", "met"), ("exclusion", "not_met")])
def test_documented_condition_has_explicit_direction(catalog, tmp_path, direction, expected):
    rules = approved_rules(catalog, tmp_path / "reviews.db", direction)
    result = screen_registry(patient_bundle(), catalog.snapshot(NCT), rules, date(2026, 9, 1))
    assert result["criteria"][0]["status"] == expected
    assert result["criteria"][0]["direction"] == direction
    assert result["criteria"][-1]["status"] == "unknown"
    assert result["outcome"] != "all_modeled_criteria_met"


@pytest.mark.parametrize("direction", ["inclusion", "exclusion"])
@pytest.mark.parametrize(
    "change", ["missing", "wrong_patient", "future", "unconfirmed", "wrong_system", "abated"]
)
def test_unusable_condition_never_establishes_absence(catalog, tmp_path, direction, change):
    bundle = patient_bundle()
    condition = bundle["entry"][1]["resource"]
    if change == "missing":
        bundle["entry"].pop(1)
    elif change == "wrong_patient":
        condition["subject"]["reference"] = "Patient/another-person"
    elif change == "future":
        condition["recordedDate"] = "2030-01-01"
    elif change == "unconfirmed":
        condition.pop("verificationStatus")
    elif change == "wrong_system":
        condition["code"]["coding"][0]["system"] = "urn:wrong"
    else:
        condition["abatementDateTime"] = "2025-02-01"
    rules = approved_rules(catalog, tmp_path / "reviews.db", direction)
    result = screen_registry(bundle, catalog.snapshot(NCT), rules, date(2026, 9, 1))
    assert result["criteria"][0]["status"] == "unknown"


def test_rule_approval_required_and_versioned_snapshot_retained(catalog, tmp_path, monkeypatch):
    fhir = FhirClient()
    monkeypatch.setattr(fhir, "record", lambda pid: patient_bundle())
    with TestClient(create_app(tmp_path / "reviews.db", fhir, catalog)) as client:
        draft = client.post(
            f"/api/v1/trials/{NCT}/rule-sets", json=proposal(catalog).model_dump()
        ).json()
        request = {
            "source": "hapi",
            "patient_id": "demo-001",
            "trial_id": NCT,
            "as_of": "2026-09-01",
            "rule_set_id": draft["id"],
        }
        assert client.post("/api/v1/screenings", json=request).status_code == 409
        url = f"/api/v1/rule-sets/{draft['id']}/reviews"
        assert (
            client.post(url, json=approval(draft, expected_rules_hash="0" * 64)).status_code == 409
        )
        assert client.post(url, json=approval(draft)).status_code == 201
        assert client.post(url, json=approval(draft)).status_code == 409
        created = client.post("/api/v1/screenings", json=request)
        assert created.status_code == 201
        screening = created.json()
        assert screening["review_status"] == "pending_review"
        assert (
            screening["source_snapshot"]["trial"]["registry"]["snapshot_id"]
            == draft["document"]["snapshot_id"]
        )
        write_snapshot(catalog.directory, title="Changed registry version")
        assert client.post("/api/v1/screenings", json=request).status_code == 409
        saved = client.get(f"/api/v1/screenings/{screening['id']}").json()
        assert saved["source_snapshot"] == screening["source_snapshot"]
        assert (
            catalog.snapshot(NCT, draft["document"]["snapshot_id"])["study"]["protocolSection"][
                "identificationModule"
            ]["briefTitle"]
            == "Fictional registry test fixture"
        )


def test_rejected_interpretation_cannot_screen(catalog, tmp_path):
    store = ReviewStore(tmp_path / "reviews.db")
    draft = store.save_rule_set(validate_proposal(catalog.snapshot(NCT), proposal(catalog)))
    rejected = store.review_rule_set(draft["id"], approval(draft, decision="reject"))
    with pytest.raises(ValueError, match="approval"):
        screen_registry(patient_bundle(), catalog.snapshot(NCT), rejected, date(2026, 9, 1))


def test_source_citation_and_age_bounds_checked(catalog):
    snapshot = catalog.snapshot(NCT)
    bad = proposal(catalog).model_dump()
    bad["rules"][0]["source_text"] = "Invented requirement not in registry"
    with pytest.raises(ValueError, match="exact text"):
        validate_proposal(snapshot, RuleProposal(**bad))
    age = draft_proposal(snapshot).model_dump()
    age["rules"][0]["minimum_years"] = 99
    age["rules"][0]["maximum_years"] = 100
    with pytest.raises(ValueError, match="Age bounds"):
        validate_proposal(snapshot, RuleProposal(**age))


def test_unsupported_age_units_do_not_become_open_bounds(tmp_path):
    catalog = write_snapshot(tmp_path / "registry", minimum="6 Months")
    with pytest.raises(ValueError, match="No supported"):
        draft_proposal(catalog.snapshot(NCT))


def test_registry_read_is_offline_and_reports_age(catalog, monkeypatch):
    monkeypatch.setattr(
        "healthops.trials.urlopen", lambda *args, **kwargs: pytest.fail("Network read")
    )
    result = catalog.list()[0]
    assert result["fictional"] is False
    assert result["snapshot_age_days"] >= 0
    assert result["registry_last_update"] == "2025-01-01"
    assert "not confirmation" in result["notice"]


def test_same_snapshot_import_is_idempotent(catalog, monkeypatch):
    current = catalog.snapshot(NCT)
    raw = (catalog.directory / NCT / current["snapshot_id"] / "study.json").read_bytes()
    monkeypatch.setattr("healthops.trials.urlopen", lambda *args, **kwargs: BytesIO(raw))
    first = catalog.import_study(NCT)
    second = catalog.import_study(NCT)
    assert first == second
    assert catalog.snapshot(NCT) == current


def test_tampered_snapshot_is_rejected(catalog):
    current = catalog.snapshot(NCT)
    path = catalog.directory / NCT / current["snapshot_id"] / "study.json"
    path.write_bytes(path.read_bytes() + b" ")
    with pytest.raises(ValueError, match="integrity"):
        catalog.snapshot(NCT)


def test_identical_draft_does_not_create_duplicate_or_reset_approval(catalog, tmp_path):
    store = ReviewStore(tmp_path / "reviews.db")
    document = validate_proposal(catalog.snapshot(NCT), proposal(catalog))
    first = store.save_rule_set(document)
    store.review_rule_set(first["id"], approval(first))
    assert store.save_rule_set(deepcopy(document))["status"] == "approved"
    assert len(store.list_rule_sets(NCT)) == 1


@pytest.mark.parametrize(
    "born,predicate",
    [
        ("2008-09-02", False),
        ("2008-09-01", True),
        ("1946-09-01", True),
        ("1945-09-01", False),
        ("1980", None),
    ],
)
@pytest.mark.parametrize("direction", ["inclusion", "exclusion"])
def test_age_boundaries_direction_and_incomplete_dates(
    catalog, tmp_path, born, predicate, direction
):
    document = validate_proposal(catalog.snapshot(NCT), draft_proposal(catalog.snapshot(NCT)))
    # Engine-level exclusion range exercise; not an approved interpretation of the source fixture.
    document["rules"][0]["direction"] = direction
    store = ReviewStore(tmp_path / "reviews.db")
    draft = store.save_rule_set(document)
    rules = store.review_rule_set(draft["id"], approval(draft))
    bundle = patient_bundle()
    bundle["entry"][0]["resource"]["birthDate"] = born
    result = screen_registry(bundle, catalog.snapshot(NCT), rules, date(2026, 9, 1))
    expected = (
        "unknown"
        if predicate is None
        else ("met" if (predicate if direction == "inclusion" else not predicate) else "not_met")
    )
    assert result["criteria"][0]["status"] == expected
