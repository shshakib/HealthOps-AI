"""Versioned, deterministic regression evaluation; optional bounded live-model smoke run."""

import argparse
import copy
import hashlib
import json
import math
import os
from datetime import UTC, date, datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.request import Request

from pydantic import BaseModel, ConfigDict, Field

from healthops.assistant import VERSION, AssistantRequest, EvidenceAssistant, ModelFailure
from healthops.demo_data import TRIAL, get_patient
from healthops.screening import screen_patient
from healthops.telemetry import configure

DATASET = Path(__file__).with_name("evaluation_cases.json")


class Pricing(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    provider: str = Field(min_length=1, max_length=30)
    model: str = Field(min_length=1, max_length=100)
    source: str = Field(min_length=1, max_length=300)
    checked_on: date
    input_per_million_usd: float = Field(ge=0, le=10000)
    output_per_million_usd: float = Field(ge=0, le=10000)
    cached_input_per_million_usd: float | None = Field(default=None, ge=0, le=10000)
    cache_creation_per_million_usd: float | None = Field(default=None, ge=0, le=10000)


def apply_pricing(report, pricing):
    """Explicit, dated price assumptions; never silently turn unknown cost into zero."""
    if report["mode"] != "live" or pricing is None:
        return report
    if (pricing.provider, pricing.model) != (report["provider"], report["model"]):
        raise ValueError("Pricing provider and model must match this run exactly.")
    report["pricing"] = pricing.model_dump(mode="json")
    summary = report["summary"]
    tokens = summary["reported_tokens"]
    if not summary["usage_complete"] or not tokens:
        summary["cost_note"] = "Unavailable: at least one call lacks complete usage accounting."
        return report
    cached, created = tokens["cached_input_tokens"], tokens["cache_creation_input_tokens"]
    if (cached and pricing.cached_input_per_million_usd is None) or (
        created and pricing.cache_creation_per_million_usd is None
    ):
        summary["cost_note"] = "Unavailable: cache pricing is required for the reported usage."
        return report
    summary["estimated_cost_usd"] = round(
        (
            (tokens["input_tokens"] - cached - created) * pricing.input_per_million_usd
            + tokens["output_tokens"] * pricing.output_per_million_usd
            + cached * (pricing.cached_input_per_million_usd or 0)
            + created * (pricing.cache_creation_per_million_usd or 0)
        )
        / 1_000_000,
        10,
    )
    summary["cost_note"] = (
        "Estimate from supplied dated rates; excludes taxes and provider adjustments."
    )
    return report


def fixture(case, as_of):
    bundle = get_patient(case["patient"])
    edits = case.get("edits", {})
    for entry in bundle["entry"]:
        resource = entry["resource"]
        if resource["resourceType"] == "Patient" and "birth_date" in edits:
            resource["birthDate"] = edits["birth_date"]
        if resource["resourceType"] == "Observation" and "lab_value" in edits:
            resource["valueQuantity"]["value"] = edits["lab_value"]
    if edits.get("remove_lab"):
        bundle["entry"] = [
            e for e in bundle["entry"] if e["resource"]["resourceType"] != "Observation"
        ]
    result = screen_patient(bundle, TRIAL, date.fromisoformat(as_of))
    return {
        **result,
        "id": "evaluation-" + case["id"],
        "revision": 0,
        "reviews": [],
        "source_snapshot": {"patient_bundle": bundle, "trial": TRIAL},
    }


def tool_response(name, **arguments):
    return {"message": {"tool_calls": [{"function": {"name": name, "arguments": arguments}}]}}


class ScriptedModel:
    """A protocol test double, never a substitute for measured model quality."""

    model = "scripted-test-double"
    provider = "simulation"

    def __init__(self, responses):
        self.responses = iter(responses)

    def chat(self, messages, remaining, final=False):
        response = next(self.responses)
        if isinstance(response, Exception):
            raise response
        return response


class OfflineModel:
    model = ""
    provider = "offline"


def grade(case, item, answer, mode):
    offline = mode == "offline"
    topic = case.get("offline_topic", case["expected_topic"]) if offline else case["expected_topic"]
    ids = case.get("offline_ids", case["expected_ids"]) if offline else case["expected_ids"]
    source = {c["criterion"]: c for c in item["criteria"]}
    citations = answer["citations"]
    exact = all(
        c["id"] in source
        and c["screening_id"] == item["id"]
        and c["text"] == source[c["id"]]["reason"]
        and c["status"] == source[c["id"]]["status"]
        and c["evidence"] == source[c["id"]]["evidence"]
        for c in citations
    )
    tools = [t["tool"] for t in answer["tool_trace"]]
    required_tools = {"get_screening_summary"}
    if topic == "workflow":
        required_tools.add("get_review_workflow")
    elif topic == "criterion":
        required_tools.add("get_criterion_evidence")
    tool_check = (
        None
        if offline
        else bool(tools) and tools[0] == "get_screening_summary" and required_tools <= set(tools)
    )
    checks = {
        "tool_selection": tool_check,
        "criterion_statuses": [c["status"] for c in item["criteria"]] == case["expected_statuses"],
        "topic": answer["topic"] == topic,
        "citation_selection": sorted(c["id"] for c in citations) == sorted(ids),
        "evidence_binding": exact and answer["evidence_hash"] == item["evidence_hash"],
        "no_model_fallback": None if offline else answer["mode"] == "model_assisted",
        "offline_no_tools": not tools if offline else None,
    }
    return checks


def fault_checks(item):
    scenarios = {
        "provider_unavailable": ([ModelFailure("model_unavailable")], "model_unavailable"),
        "invalid_json": ([{"message": {"content": "not-json"}}], "invalid_model_response"),
        "write_tool_denied": (
            [tool_response("get_screening_summary"), tool_response("submit_review")],
            "tool_not_allowed",
        ),
        "summary_required": ([tool_response("get_review_workflow")], "summary_required"),
        "invented_citation": (
            [
                tool_response("get_screening_summary"),
                {
                    "message": {
                        "content": json.dumps(
                            {"topic": "criterion", "criterion_ids": ["other-patient"]}
                        )
                    }
                },
            ],
            "invalid_citations",
        ),
        "tool_budget": ([tool_response("get_screening_summary")] * 4, "tool_budget_exceeded"),
    }
    rows = []
    for name, (responses, expected) in scenarios.items():
        original = copy.deepcopy(item)
        result = EvidenceAssistant(ScriptedModel(responses)).answer(
            item, AssistantRequest(question="Explain this screening")
        )
        rows.append(
            {
                "id": name,
                "passed": result["mode"] == "fallback"
                and result["fallback_reason"] == expected
                and item == original,
                "observed_reason": result["fallback_reason"],
            }
        )
    return rows


def permission_checks():
    """Exercise the actual API middleware in an isolated database, never the live ledger."""
    from fastapi.testclient import TestClient

    from healthops.api import create_app
    from healthops.auth import NewUser

    rows = []
    headers = {"X-HealthOps-Request": "1"}
    with TemporaryDirectory() as tmp:
        app = create_app(Path(tmp) / "permissions.db")
        for role in ("viewer", "reviewer", "admin"):
            app.state.auth.create_user(
                NewUser(username=role, password="evaluation-test-only-password", role=role)
            )
        with TestClient(app) as client:
            for path in ("/api/v1/patients", "/api/v1/screenings", "/api/v1/admin/monitoring"):
                status = client.get(path).status_code
                rows.append({"id": "anonymous:" + path, "passed": status == 401, "status": status})
            for role in ("viewer", "reviewer", "admin"):
                assert (
                    client.post(
                        "/api/v1/auth/login",
                        json={"username": role, "password": "evaluation-test-only-password"},
                        headers=headers,
                    ).status_code
                    == 200
                )
                for name, method, path, body, expected in (
                    ("read", "GET", "/api/v1/patients", None, 200),
                    ("screen", "POST", "/api/v1/screenings", {}, 403 if role == "viewer" else 201),
                    (
                        "monitoring",
                        "GET",
                        "/api/v1/admin/monitoring",
                        None,
                        200 if role == "admin" else 403,
                    ),
                    (
                        "settings",
                        "POST",
                        "/api/v1/assistant/settings",
                        {"provider": "offline"},
                        200 if role == "admin" else 403,
                    ),
                ):
                    status = client.request(method, path, json=body, headers=headers).status_code
                    rows.append(
                        {"id": f"{role}:{name}", "passed": status == expected, "status": status}
                    )
                client.post("/api/v1/auth/logout", json={}, headers=headers)
    return rows


def run(mode="offline", model=None, limit=None, include_permissions=True, pricing=None):
    raw = DATASET.read_bytes()
    dataset = json.loads(raw)
    if mode not in {"offline", "live"}:
        raise ValueError("Mode must be offline or live.")
    if limit is not None and (type(limit) is not int or not 1 <= limit <= len(dataset["cases"])):
        raise ValueError("Limit must select at least one case and not exceed the dataset.")
    cases = dataset["cases"][:limit]
    if mode == "live" and (model is None or not model.model):
        raise ValueError("Configure a model before running live evaluation.")
    if (
        pricing
        and mode == "live"
        and (pricing.provider, pricing.model) != (getattr(model, "provider", None), model.model)
    ):
        raise ValueError("Pricing provider and model must match before making provider calls.")
    rows = []
    for case in cases:
        item = fixture(case, dataset["as_of"])
        original = copy.deepcopy(item)
        assistant = EvidenceAssistant(model if mode == "live" else OfflineModel())
        result = assistant.answer(item, AssistantRequest(question=case["question"]))
        checks = grade(case, item, result, mode)
        checks["no_record_mutation"] = item == original
        rows.append(
            {
                "id": case["id"],
                "question": case["question"],
                "checks": checks,
                "passed": all(v for v in checks.values() if v is not None),
                "mode": result["mode"],
                "topic": result["topic"],
                "fallback_reason": result["fallback_reason"],
                "citation_ids": [c["id"] for c in result["citations"]],
                "latency_ms": result["latency_ms"],
                "tool_trace": result["tool_trace"],
                "usage": result["usage"],
                "monitoring": result["monitoring"],
            }
        )
    faults = (
        fault_checks(fixture(dataset["cases"][0], dataset["as_of"])) if mode == "offline" else []
    )
    permissions = permission_checks() if include_permissions and mode == "offline" else []
    latency = sorted(r["latency_ms"] for r in rows)
    totals = {
        key: sum((r["usage"]["tokens"] or {}).get(key, 0) for r in rows)
        for key in (
            "input_tokens",
            "output_tokens",
            "total_tokens",
            "cached_input_tokens",
            "cache_creation_input_tokens",
        )
    }
    complete = all(r["usage"]["complete"] for r in rows)
    report = {
        "generated_at": datetime.now(UTC).isoformat(),
        "dataset_version": dataset["version"],
        "dataset_sha256": hashlib.sha256(raw).hexdigest(),
        "assistant_version": VERSION,
        "mode": mode,
        "provider": getattr(model, "provider", None) if mode == "live" else None,
        "model": model.model if mode == "live" else None,
        "limitations": (
            "Public curated synthetic regression cases, not clinical validation or an "
            "independent held-out benchmark. Evidence-only results do not measure LLM quality. "
            "Fault scenarios use a scripted test double. No retrieval index or LLM judge is used."
        ),
        "summary": {
            "passed": sum(r["passed"] for r in rows),
            "total": len(rows),
            "faults_passed": sum(r["passed"] for r in faults),
            "faults_total": len(faults),
            "permissions_passed": sum(r["passed"] for r in permissions),
            "permissions_total": len(permissions),
            "fallback_count": sum(r["mode"] == "fallback" for r in rows),
            "model_calls": sum(r["usage"]["model_calls"] for r in rows),
            "p95_latency_ms": latency[max(0, math.ceil(len(latency) * 0.95) - 1)],
            "usage_complete": complete,
            "reported_tokens": totals if any(r["usage"]["tokens"] for r in rows) else None,
            "estimated_cost_usd": 0.0 if mode == "offline" else None,
            "cost_note": "No provider calls."
            if mode == "offline"
            else "Unavailable without verified model pricing; token counts are not an invoice.",
        },
        "cases": rows,
        "faults": faults,
        "permissions": permissions,
    }
    report["metrics"] = {
        name: {
            "passed": sum(r["checks"][name] is True for r in rows),
            "total": sum(r["checks"][name] is not None for r in rows),
        }
        for name in rows[0]["checks"]
    }
    apply_pricing(report, pricing)
    report["passed"] = all(r["passed"] for r in rows + faults + permissions)
    mlflow = configure()
    report["mlflow_run_id"] = None
    if mlflow:
        try:
            with mlflow.start_run(run_name=f"{dataset['version']}-{mode}") as active:
                report["mlflow_run_id"] = active.info.run_id
                mlflow.log_params(
                    {
                        "dataset_version": dataset["version"],
                        "dataset_sha256": report["dataset_sha256"],
                        "mode": mode,
                        "assistant_version": VERSION,
                    }
                )
                mlflow.log_metrics(
                    {k: v for k, v in report["summary"].items() if type(v) in (int, float)}
                )
                mlflow.log_metrics(
                    {
                        name + "_rate": metric["passed"] / metric["total"]
                        for name, metric in report["metrics"].items()
                        if metric["total"]
                    }
                )
                mlflow.log_dict(report, "evaluation-report.json")
        except Exception:
            report["mlflow_run_id"] = None
    return report


def markdown(report):
    s = report["summary"]
    cost = (
        "$0 (no provider calls)"
        if report["mode"] == "offline"
        else "Unavailable without verified pricing"
    )
    if report["mode"] == "live" and s["estimated_cost_usd"] is not None:
        cost = f"${s['estimated_cost_usd']:.8f} (estimate)"
    lines = [
        "# HealthOps evaluation report",
        "",
        f"Generated: {report['generated_at']}",
        f"Mode: **{report['mode']}** · Dataset: `{report['dataset_version']}`",
        f"Assistant: `{report['assistant_version']}` · "
        f"Provider/model: `{report['provider'] or 'none'}` / `{report['model'] or 'none'}`",
        "",
        f"Dataset SHA-256: `{report['dataset_sha256']}`",
        "",
        "| Check | Result |",
        "|---|---|",
        f"| Answer cases | {s['passed']}/{s['total']} |",
        *[
            f"| {name.replace('_', ' ')} | "
            + (f"{m['passed']}/{m['total']}" if m["total"] else "N/A in this mode")
            + " |"
            for name, m in report["metrics"].items()
        ],
        "| Simulated failure handling | "
        + (f"{s['faults_passed']}/{s['faults_total']}" if s["faults_total"] else "Not run")
        + " |",
        "| API permission boundaries | "
        + (
            f"{s['permissions_passed']}/{s['permissions_total']}"
            if s["permissions_total"]
            else "Not run"
        )
        + " |",
        f"| Fallback answers | {s['fallback_count']}/{s['total']} |",
        f"| P95 assistant time (excludes root trace export) | {s['p95_latency_ms']} ms |",
        f"| Provider cost | {cost} |",
        f"| Model calls | {s['model_calls']} |",
        "",
        report["limitations"],
        "Timing covers the assistant component, not end-to-end API latency. "
        "Zero can indicate timer resolution or rounding for very short offline calls.",
        "",
        "A case passes only if its expected criterion statuses, topic, citation selection, "
        "exact evidence binding, and unchanged record all pass. Live cases additionally "
        "require a model-assisted answer; fallback never counts as live success.",
        "",
        "| Case | Result | Mode | Topic |",
        "|---|---|---|---|",
    ]
    lines += [
        f"| {r['id']} | {'PASS' if r['passed'] else 'FAIL'} | {r['mode']} | {r['topic']} |"
        for r in report["cases"]
    ]
    return "\n".join(lines) + "\n"


def run_via_api(base_url, limit, pricing=None):
    """Use the administrator's configured model without transferring its key to the CLI."""
    from healthops.cli_session import signed_in_opener

    opener = signed_in_opener(base_url)
    body = {"limit": limit}
    if pricing:
        body["pricing"] = pricing.model_dump(mode="json")
    request = Request(
        base_url.rstrip("/") + "/api/v1/admin/evaluations",
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json", "X-HealthOps-Request": "1"},
    )
    with opener.open(request, timeout=240) as response:
        return json.load(response)


def save(report, directory):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    (directory / "report.md").write_text(markdown(report), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=["offline", "live"], default="offline")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--output", default=".local/evaluation")
    parser.add_argument("--trace", action="store_true")
    parser.add_argument("--pricing", type=Path, help="JSON with verified, dated per-million rates")
    parser.add_argument("--api-url", help="Use configured dashboard model via signed-in local API")
    args = parser.parse_args()
    if args.limit is not None and not 1 <= args.limit <= 22:
        parser.error("limit must be 1–22")
    if args.api_url and (args.mode != "live" or (args.limit or 3) > 5):
        parser.error("--api-url requires --mode live and a limit of 1–5")
    if args.trace:
        os.environ["HEALTHOPS_TRACING"] = "1"
    from healthops.providers import ProviderSettings

    pricing = (
        Pricing.model_validate_json(args.pricing.read_text(encoding="utf-8"))
        if args.pricing
        else None
    )
    if args.api_url:
        report = run_via_api(args.api_url, args.limit or 3, pricing)
    else:
        report = run(
            args.mode,
            ProviderSettings().client() if args.mode == "live" else None,
            args.limit,
            pricing=pricing,
        )
    save(report, args.output)
    print(json.dumps(report["summary"], indent=2))
    tracing_ok = not args.trace or (
        report["mlflow_run_id"] is not None
        and all(r["monitoring"]["recorded"] for r in report["cases"])
    )
    raise SystemExit(0 if report["passed"] and tracing_ok else 1)


if __name__ == "__main__":
    main()
