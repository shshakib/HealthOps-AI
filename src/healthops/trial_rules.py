"""Partial trial interpretation: explicit source evidence, approval, conservative findings."""

import json
import re
from datetime import date
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from healthops.screening import _date, _has_code, _hash


class RuleBase(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    id: str = Field(pattern=r"^[a-z][a-z0-9_]{0,49}$")
    label: str = Field(min_length=5, max_length=300)
    direction: Literal["inclusion", "exclusion"]
    source_text: str = Field(min_length=3, max_length=10000)


class AgeRule(RuleBase):
    kind: Literal["age"]
    minimum_years: int | None = Field(default=None, ge=0, le=150)
    maximum_years: int | None = Field(default=None, ge=0, le=150)

    @model_validator(mode="after")
    def ordered_range(self):
        if self.minimum_years is None and self.maximum_years is None:
            raise ValueError("At least one age bound is required.")
        if (
            self.minimum_years is not None
            and self.maximum_years is not None
            and self.minimum_years > self.maximum_years
        ):
            raise ValueError("Age bounds are reversed.")
        return self


class ConditionRule(RuleBase):
    kind: Literal["condition"]
    system: Literal["http://snomed.info/sct"] = "http://snomed.info/sct"
    code: str = Field(pattern=r"^[0-9]{6,18}$")


Rule = Annotated[AgeRule | ConditionRule, Field(discriminator="kind")]


class RuleProposal(BaseModel):
    model_config = ConfigDict(extra="forbid")
    snapshot_id: str = Field(pattern=r"^[a-f0-9]{64}$")
    rules: list[Rule] = Field(min_length=1, max_length=30)


class RuleReview(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    reviewer: str | None = Field(default=None, min_length=2, max_length=100)
    decision: Literal["approve", "reject"]
    reason: str = Field(min_length=10, max_length=2000)
    expected_rules_hash: str = Field(pattern=r"^[a-f0-9]{64}$")


def age_source(eligibility: dict) -> str:
    return json.dumps(
        {key: eligibility.get(key) for key in ("minimumAge", "maximumAge")}, sort_keys=True
    )


def years(value: str | None) -> int | None:
    match = re.fullmatch(r"(\d+) Years", value or "")
    return int(match[1]) if match else None


def validate_proposal(snapshot: dict, proposal: RuleProposal) -> dict:
    if proposal.snapshot_id != snapshot["snapshot_id"]:
        raise ValueError("Snapshot changed. Reload the study and create a new interpretation.")
    eligibility = snapshot["study"]["protocolSection"]["eligibilityModule"]
    identifiers = [r.id for r in proposal.rules]
    if len(set(identifiers)) != len(identifiers) or "full_eligibility_review" in identifiers:
        raise ValueError("Rule IDs must be unique and cannot use the reserved manual-review ID.")
    for rule in proposal.rules:
        if isinstance(rule, AgeRule) and rule.source_text == age_source(eligibility):
            if (
                rule.direction != "inclusion"
                or rule.minimum_years != years(eligibility.get("minimumAge"))
                or rule.maximum_years != years(eligibility.get("maximumAge"))
            ):
                raise ValueError("Age bounds do not match the cited structured registry fields.")
            # Do not silently turn unsupported units into open bounds.
            for key in ("minimumAge", "maximumAge"):
                if eligibility.get(key) not in (None, "N/A") and years(eligibility[key]) is None:
                    raise ValueError("Only whole-year age bounds are supported; review manually.")
        elif rule.source_text not in eligibility["eligibilityCriteria"]:
            raise ValueError("Each rule must cite exact text from this registry snapshot.")
    return {
        "trial_id": snapshot["id"],
        "snapshot_id": snapshot["snapshot_id"],
        "rules": [r.model_dump() for r in proposal.rules],
        "coverage": "partial",
        "interpreter_version": "registry-partial-v1",
        "manual_review_required": True,
        "notice": "Approval covers only these partial interpretations. The complete registry "
        "criteria still require manual assessment; this is not clinical validation.",
    }


def draft_proposal(snapshot: dict) -> RuleProposal:
    eligibility = snapshot["study"]["protocolSection"]["eligibilityModule"]
    rules = []
    bounds = [eligibility.get(key) for key in ("minimumAge", "maximumAge")]
    if all(v in (None, "N/A") or years(v) is not None for v in bounds) and any(
        years(v) is not None for v in bounds
    ):
        rules.append(
            {
                "id": "structured_age",
                "kind": "age",
                "direction": "inclusion",
                "label": "Structured registry age range; consent timing remains manual",
                "source_text": age_source(eligibility),
                "minimum_years": years(bounds[0]),
                "maximum_years": years(bounds[1]),
            }
        )
    # Deliberate, narrowly scoped draft mappings; never interpret search keywords as rules.
    mappings = {
        "NCT07247084": (
            "exclusion",
            "Have type 1 diabetes, type 2 diabetes, or any other types of diabetes",
            "Documented active T2D exclusion component; other diabetes types remain manual",
        ),
        "NCT06591286": (
            "inclusion",
            "Type 2 diabetes admitted to Department of Endocrinology and Metabolism.",
            "Documented active T2D component; admission and treatment context remain manual",
        ),
    }
    mapping = mappings.get(snapshot["id"])
    if mapping and mapping[1] in eligibility["eligibilityCriteria"]:
        rules.append(
            {
                "id": "documented_t2d",
                "kind": "condition",
                "direction": mapping[0],
                "source_text": mapping[1],
                "label": mapping[2],
                "code": "44054006",
            }
        )
    if not rules:
        raise ValueError(
            "No supported automatic draft. Submit a sourced proposal for human review."
        )
    return RuleProposal(snapshot_id=snapshot["snapshot_id"], rules=rules)


def screen_registry(bundle: dict, snapshot: dict, rule_set: dict, as_of: date) -> dict:
    if rule_set["status"] != "approved":
        raise ValueError("The rule set needs explicit human approval before screening.")
    document = rule_set["document"]
    if document["snapshot_id"] != snapshot["snapshot_id"] or document["trial_id"] != snapshot["id"]:
        raise ValueError("Approved interpretation belongs to a different study snapshot.")
    resources = [entry["resource"] for entry in bundle["entry"]]
    patients = [r for r in resources if r["resourceType"] == "Patient"]
    if len(patients) != 1:
        raise ValueError("Exactly one patient is required.")
    patient = patients[0]
    findings = []
    for rule in document["rules"]:
        predicate, evidence = None, []
        if rule["kind"] == "age":
            born = _date(patient.get("birthDate"))
            if born is not None and born <= as_of:
                age = as_of.year - born.year - ((as_of.month, as_of.day) < (born.month, born.day))
                predicate = (rule["minimum_years"] is None or age >= rule["minimum_years"]) and (
                    rule["maximum_years"] is None or age <= rule["maximum_years"]
                )
                evidence = [f"Patient/{patient['id']}"]
                reason = f"Age {age} at the patient assessment date {as_of}."
            else:
                reason = "A complete, valid birth date is missing."
        else:
            matches = [
                r
                for r in resources
                if r["resourceType"] == "Condition"
                and r.get("subject", {}).get("reference") == f"Patient/{patient['id']}"
                and _has_code(r, rule["code"], rule["system"])
                and any(
                    c.get("code") == "active"
                    and c.get("system")
                    == "http://terminology.hl7.org/CodeSystem/condition-clinical"
                    for c in r.get("clinicalStatus", {}).get("coding", [])
                )
                and any(
                    c.get("code") == "confirmed"
                    and c.get("system")
                    == "http://terminology.hl7.org/CodeSystem/condition-ver-status"
                    for c in r.get("verificationStatus", {}).get("coding", [])
                )
                and (recorded := _date(r.get("recordedDate"))) is not None
                and recorded <= as_of
                and not any(key.startswith("abatement") for key in r)
            ]
            if matches:
                predicate = True
                evidence = [f"Condition/{r['id']}" for r in matches]
                reason = "Dated, active, confirmed documentation matches the exact condition code."
            else:
                reason = (
                    "No usable matching documentation. Absence of a condition is not established."
                )
        status = "unknown"
        if predicate is not None:
            passes = predicate if rule["direction"] == "inclusion" else not predicate
            status = "met" if passes else "not_met"
        findings.append(
            {
                "criterion": rule["id"],
                "label": rule["label"],
                "direction": rule["direction"],
                "status": status,
                "reason": reason,
                "evidence": evidence,
                "source_text": rule["source_text"],
            }
        )
    findings.append(
        {
            "criterion": "full_eligibility_review",
            "direction": "manual",
            "status": "unknown",
            "reason": "Full inclusion/exclusion criteria, context, "
            "and site requirements remain for human assessment.",
            "evidence": [],
            "source_text": snapshot["study"]["protocolSection"]["eligibilityModule"][
                "eligibilityCriteria"
            ],
        }
    )
    return {
        "patient_id": patient["id"],
        "trial_id": snapshot["id"],
        "as_of": as_of.isoformat(),
        "rules_version": rule_set["id"],
        "rules_hash": rule_set["rules_hash"],
        "evidence_hash": _hash(bundle),
        "registry_snapshot_id": snapshot["snapshot_id"],
        "outcome": "criteria_not_met"
        if any(f["status"] == "not_met" for f in findings)
        else "insufficient_evidence",
        "criteria": findings,
        "review_status": "pending_review",
        "data_source": "hapi",
        "notice": "Synthetic retrospective assessment using saved registry criteria. "
        "Partial rule review is not clinical validation. No eligibility or enrollment decision.",
    }
