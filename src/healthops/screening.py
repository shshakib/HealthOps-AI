"""Deterministic comparison of a deliberately limited set of fictional criteria."""

import hashlib
import json
import math
from datetime import date

from healthops.demo_data import CODE_SYSTEM


def _hash(value: dict) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def _date(value: str | None) -> date | None:
    try:
        return date.fromisoformat((value or "")[:10])
    except (ValueError, TypeError):
        return None


def _has_code(resource: dict, code: str, system: str = CODE_SYSTEM) -> bool:
    return any(
        item.get("code") == code and item.get("system") == system
        for item in resource.get("code", {}).get("coding", [])
    )


def _result(criterion: str, status: str, reason: str, resources: list[dict]) -> dict:
    return {
        "criterion": criterion,
        "status": status,
        "reason": reason,
        "evidence": [f"{r['resourceType']}/{r['id']}" for r in resources],
    }


def screen_patient(bundle: dict, trial: dict, as_of: date) -> dict:
    resources = [entry["resource"] for entry in bundle["entry"]]
    patients = [r for r in resources if r["resourceType"] == "Patient"]
    if len(patients) != 1:
        raise ValueError("A demo bundle must contain exactly one Patient.")
    patient = patients[0]
    patient_ref = f"Patient/{patient['id']}"
    linked = [r for r in resources if r.get("subject", {}).get("reference") == patient_ref]

    birth = _date(patient.get("birthDate"))
    if birth is None or birth > as_of:
        age_result = _result("age", "unknown", "A valid birth date is missing.", [patient])
    else:
        age = as_of.year - birth.year - ((as_of.month, as_of.day) < (birth.month, birth.day))
        status = "met" if trial["age_min"] <= age <= trial["age_max"] else "not_met"
        age_result = _result("age", status, f"Age is {age} on {as_of.isoformat()}.", [patient])

    conditions = [
        r
        for r in linked
        if r["resourceType"] == "Condition"
        and _has_code(r, trial["condition_code"], trial.get("condition_system", CODE_SYSTEM))
        and any(c.get("code") == "active" for c in r.get("clinicalStatus", {}).get("coding", []))
        and any(
            c.get("code") == "confirmed" for c in r.get("verificationStatus", {}).get("coding", [])
        )
        and (recorded := _date(r.get("recordedDate"))) is not None
        and recorded <= as_of
    ]
    condition_result = _result(
        "documented_condition",
        "met" if conditions else "unknown",
        "An active confirmed demo condition is documented."
        if conditions
        else "No usable documentation establishes the condition; absence is not inferred.",
        conditions,
    )

    labs = [
        r
        for r in linked
        if r["resourceType"] == "Observation"
        and _has_code(r, trial["lab_code"], trial.get("lab_system", CODE_SYSTEM))
        and r.get("status") in {"final", "amended", "corrected"}
        and (observed := _date(r.get("effectiveDateTime"))) is not None
        and observed <= as_of
    ]
    lab_result = _result("recent_lab_in_range", "unknown", "No usable dated result exists.", [])
    if labs:
        latest_date = max(_date(r["effectiveDateTime"]) for r in labs)
        latest = [r for r in labs if _date(r["effectiveDateTime"]) == latest_date]
        quantities = {json.dumps(r.get("valueQuantity"), sort_keys=True) for r in latest}
        quantity = latest[0].get("valueQuantity") or {}
        value = quantity.get("value")
        if (as_of - latest_date).days > trial["lab_max_age_days"]:
            reason = "The latest result is older than the fictional trial's evidence window."
            status = "unknown"
        elif len(quantities) > 1:
            reason, status = "Conflicting results on the latest date need review.", "unknown"
        elif (
            type(value) not in (int, float)
            or not math.isfinite(value)
            or quantity.get("code") != trial["lab_unit"]
            or quantity.get("system") != "http://unitsofmeasure.org"
        ):
            reason, status = "The latest value or unit is unsupported or missing.", "unknown"
        else:
            status = "met" if trial["lab_min"] <= value <= trial["lab_max"] else "not_met"
            reason = f"Latest result is {value} {trial['lab_unit']} dated {latest_date}."
        lab_result = _result("recent_lab_in_range", status, reason, latest)

    criteria = [age_result, condition_result, lab_result]
    statuses = {item["status"] for item in criteria}
    outcome = "all_modeled_criteria_met"
    if "not_met" in statuses:
        outcome = "criteria_not_met"
    elif "unknown" in statuses:
        outcome = "insufficient_evidence"
    return {
        "patient_id": patient["id"],
        "trial_id": trial["id"],
        "as_of": as_of.isoformat(),
        "rules_version": trial["version"],
        "rules_hash": _hash(trial),
        "evidence_hash": _hash(bundle),
        "outcome": outcome,
        "criteria": criteria,
        "review_status": "pending_review",
        "notice": "Fictional criteria and synthetic data. No eligibility or enrollment decision.",
    }
