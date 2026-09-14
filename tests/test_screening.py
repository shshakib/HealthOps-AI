from copy import deepcopy
from datetime import date

import pytest

from healthops.demo_data import TRIAL, get_patient
from healthops.screening import screen_patient

AS_OF = date(2026, 9, 1)


def evaluate(bundle: dict) -> dict:
    return screen_patient(bundle, TRIAL, AS_OF)


@pytest.mark.parametrize(
    ("patient_id", "outcome", "lab_status"),
    [
        ("demo-001", "all_modeled_criteria_met", "met"),
        ("demo-002", "insufficient_evidence", "unknown"),
        ("demo-003", "criteria_not_met", "not_met"),
    ],
)
def test_demo_outcomes_always_await_human_review(patient_id, outcome, lab_status):
    result = evaluate(get_patient(patient_id))
    assert result["outcome"] == outcome
    assert result["criteria"][2]["status"] == lab_status
    assert result["review_status"] == "pending_review"


def test_missing_condition_is_unknown_not_proof_of_absence():
    bundle = get_patient("demo-001")
    bundle["entry"] = [e for e in bundle["entry"] if e["resource"]["resourceType"] != "Condition"]
    result = evaluate(bundle)
    assert result["criteria"][1]["status"] == "unknown"
    assert result["outcome"] == "insufficient_evidence"


def test_other_patients_lab_cannot_satisfy_criterion():
    bundle = get_patient("demo-001")
    bundle["entry"][2]["resource"]["subject"]["reference"] = "Patient/someone-else"
    assert evaluate(bundle)["criteria"][2]["status"] == "unknown"


@pytest.mark.parametrize("value", [None, True, float("nan"), float("inf"), "8.2"])
def test_invalid_numeric_lab_is_unknown(value):
    bundle = get_patient("demo-001")
    bundle["entry"][2]["resource"]["valueQuantity"]["value"] = value
    assert evaluate(bundle)["criteria"][2]["status"] == "unknown"


def test_unsupported_units_are_not_silently_compared():
    bundle = get_patient("demo-001")
    bundle["entry"][2]["resource"]["valueQuantity"]["code"] = "mmol/mol"
    assert evaluate(bundle)["criteria"][2]["status"] == "unknown"


def test_future_observation_cannot_satisfy_criterion():
    bundle = get_patient("demo-001")
    bundle["entry"][2]["resource"]["effectiveDateTime"] = "2027-01-01"
    assert evaluate(bundle)["criteria"][2]["status"] == "unknown"


def test_newer_failed_lab_takes_precedence_over_older_passing_lab():
    bundle = get_patient("demo-001")
    newer = deepcopy(bundle["entry"][2])
    newer["resource"]["id"] = "newer-result"
    newer["resource"]["effectiveDateTime"] = "2026-08-20"
    newer["resource"]["valueQuantity"]["value"] = 12.0
    bundle["entry"].append(newer)
    result = evaluate(bundle)["criteria"][2]
    assert result["status"] == "not_met"
    assert result["evidence"] == ["Observation/newer-result"]


def test_same_date_conflict_requires_review():
    bundle = get_patient("demo-001")
    conflict = deepcopy(bundle["entry"][2])
    conflict["resource"]["id"] = "conflicting-result"
    conflict["resource"]["valueQuantity"]["value"] = 12.0
    bundle["entry"].append(conflict)
    assert evaluate(bundle)["criteria"][2]["status"] == "unknown"


def test_birthday_boundary_is_respected():
    bundle = get_patient("demo-001")
    bundle["entry"][0]["resource"]["birthDate"] = "1986-09-02"
    assert evaluate(bundle)["criteria"][0]["status"] == "not_met"
    bundle["entry"][0]["resource"]["birthDate"] = "1986-09-01"
    assert evaluate(bundle)["criteria"][0]["status"] == "met"


def test_evidence_hash_changes_when_a_source_changes():
    bundle = get_patient("demo-001")
    before = evaluate(bundle)
    bundle["entry"][2]["resource"]["valueQuantity"]["value"] = 8.3
    after = evaluate(bundle)
    assert before["evidence_hash"] != after["evidence_hash"]
    assert before["rules_hash"] == after["rules_hash"]
