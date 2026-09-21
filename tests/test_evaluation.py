import copy
import json

import pytest
from auth_support import TestClient

from healthops.api import create_app
from healthops.assistant import AssistantRequest, EvidenceAssistant
from healthops.evaluation import (
    DATASET,
    OfflineModel,
    Pricing,
    ScriptedModel,
    apply_pricing,
    fixture,
    grade,
    run,
    tool_response,
)
from healthops.telemetry import normalize_usage


def test_versioned_cases_and_simulated_faults_pass_offline(monkeypatch):
    monkeypatch.delenv("HEALTHOPS_TRACING", raising=False)
    result = run(include_permissions=False)
    assert result["passed"]
    assert result["summary"]["total"] == 22
    assert result["summary"]["faults_total"] == 6
    assert result["summary"]["fallback_count"] == 22
    assert result["summary"]["estimated_cost_usd"] == 0
    assert result["summary"]["reported_tokens"] is None
    assert result["metrics"]["no_model_fallback"]["total"] == 0
    assert result["metrics"]["tool_selection"]["total"] == 0


def test_grader_catches_wrong_routing_status_citation_and_fake_live_success():
    dataset = json.loads(DATASET.read_text())
    case = dataset["cases"][0]
    item = fixture(case, dataset["as_of"])
    answer = EvidenceAssistant(OfflineModel()).answer(
        item, AssistantRequest(question=case["question"])
    )
    assert all(v for v in grade(case, item, answer, "offline").values() if v is not None)
    assert not grade(case, item, answer, "live")["no_model_fallback"]
    broken = copy.deepcopy(answer)
    broken["topic"] = "unsupported"
    broken["citations"][0]["screening_id"] = "another-patient"
    assert not grade(case, item, broken, "offline")["evidence_binding"]
    assert not grade(case, item, broken, "offline")["topic"]
    broken["citations"] = []
    assert not grade(case, item, broken, "offline")["citation_selection"]
    item["criteria"][0]["status"] = "unknown"
    assert not grade(case, item, answer, "offline")["criterion_statuses"]


@pytest.mark.parametrize(
    "provider,raw,expected",
    [
        (
            "openai",
            {
                "usage": {
                    "input_tokens": 12,
                    "output_tokens": 3,
                    "input_tokens_details": {"cached_tokens": 2},
                }
            },
            (12, 3, 2, 0),
        ),
        (
            "anthropic",
            {
                "usage": {
                    "input_tokens": 12,
                    "output_tokens": 3,
                    "cache_read_input_tokens": 2,
                    "cache_creation_input_tokens": 4,
                }
            },
            (18, 3, 2, 4),
        ),
        (
            "gemini",
            {
                "usageMetadata": {
                    "promptTokenCount": 12,
                    "candidatesTokenCount": 3,
                    "thoughtsTokenCount": 5,
                    "cachedContentTokenCount": 2,
                }
            },
            (12, 8, 2, 0),
        ),
        ("ollama", {"prompt_eval_count": 12, "eval_count": 3}, (12, 3, 0, 0)),
    ],
)
def test_usage_is_provider_reported_and_includes_cached_and_reasoning_tokens(
    provider, raw, expected
):
    usage = normalize_usage(provider, raw)
    assert (
        tuple(
            usage[k]
            for k in (
                "input_tokens",
                "output_tokens",
                "cached_input_tokens",
                "cache_creation_input_tokens",
            )
        )
        == expected
    )
    assert usage["total_tokens"] == expected[0] + expected[1]
    assert normalize_usage(provider, {}) is None


def test_no_fabricated_usage_and_price_requires_complete_matching_inputs():
    assert normalize_usage("openai", {"usage": {"input_tokens": -1, "output_tokens": 3}}) is None
    pricing = Pricing(
        provider="test",
        model="test-model",
        source="test rates, not market prices",
        checked_on="2026-09-20",
        input_per_million_usd=2,
        output_per_million_usd=4,
    )
    report = {
        "mode": "live",
        "provider": "test",
        "model": "test-model",
        "summary": {
            "usage_complete": True,
            "estimated_cost_usd": None,
            "reported_tokens": {
                "input_tokens": 1000,
                "output_tokens": 100,
                "cached_input_tokens": 0,
                "cache_creation_input_tokens": 0,
            },
        },
    }
    assert apply_pricing(copy.deepcopy(report), pricing)["summary"]["estimated_cost_usd"] == 0.0024
    report["summary"]["usage_complete"] = False
    assert apply_pricing(copy.deepcopy(report), pricing)["summary"]["estimated_cost_usd"] is None
    report["summary"]["usage_complete"] = True
    report["summary"]["reported_tokens"]["cached_input_tokens"] = 100
    assert apply_pricing(copy.deepcopy(report), pricing)["summary"]["estimated_cost_usd"] is None
    with pytest.raises(ValueError):
        apply_pricing(report, pricing.model_copy(update={"model": "wrong-model"}))


def test_live_without_configuration_is_blocked_before_calls(tmp_path):
    from healthops.providers import ProviderSettings

    with TestClient(
        create_app(tmp_path / "api.db", provider_settings=ProviderSettings(False))
    ) as client:
        assert client.get("/api/v1/admin/monitoring").status_code == 200
        assert client.post("/api/v1/admin/evaluations", json={}).status_code == 409
        assert client.post("/api/v1/admin/evaluations", json={"limit": 6}).status_code == 422


def test_live_fallback_cannot_pass_as_model_quality():
    model = ScriptedModel([{"message": {"content": "not-json"}}])
    report = run("live", model, limit=1, include_permissions=False)
    assert not report["passed"]
    assert report["summary"]["fallback_count"] == 1
    assert report["summary"]["estimated_cost_usd"] is None
    assert not report["summary"]["usage_complete"]


def test_cli_forwards_dashboard_and_pricing_options(tmp_path, monkeypatch):
    from healthops import evaluation

    rates = {
        "provider": "test",
        "model": "test-model",
        "source": "test-only",
        "checked_on": "2026-09-21",
        "input_per_million_usd": 2,
        "output_per_million_usd": 4,
    }
    path = tmp_path / "rates.json"
    path.write_text(json.dumps(rates), encoding="utf-8")
    captured = {}

    def fake_api(url, limit, pricing):
        captured.update(url=url, limit=limit, pricing=pricing.model_dump(mode="json"))
        return {"passed": True, "summary": {}}

    monkeypatch.setattr(evaluation, "run_via_api", fake_api)
    monkeypatch.setattr(evaluation, "save", lambda *args: None)
    monkeypatch.setattr(
        "sys.argv",
        [
            "evaluation",
            "--mode",
            "live",
            "--api-url",
            "http://127.0.0.1:18000",
            "--limit",
            "2",
            "--pricing",
            str(path),
        ],
    )
    with pytest.raises(SystemExit) as ended:
        evaluation.main()
    assert ended.value.code == 0
    assert captured["limit"] == 2
    assert captured["pricing"]["model"] == "test-model"
    assert captured["url"] == "http://127.0.0.1:18000"


@pytest.mark.parametrize("role", ["viewer", "reviewer"])
def test_non_admin_cannot_trigger_billable_evaluation(tmp_path, role):
    from fastapi.testclient import TestClient as RawClient

    from healthops.auth import NewUser

    app = create_app(tmp_path / "roles.db")
    app.state.auth.create_user(NewUser(username=role, password="isolated-test-password", role=role))
    with RawClient(app) as client:
        headers = {"X-HealthOps-Request": "1"}
        assert (
            client.post(
                "/api/v1/auth/login",
                json={"username": role, "password": "isolated-test-password"},
                headers=headers,
            ).status_code
            == 200
        )
        assert client.post("/api/v1/admin/evaluations", json={}, headers=headers).status_code == 403


def test_mlflow_round_trip_excludes_sensitive_inputs_and_keeps_tool_spans(tmp_path, monkeypatch):
    mlflow = pytest.importorskip("mlflow")
    from healthops import telemetry

    monkeypatch.setenv("HEALTHOPS_TRACING", "1")
    monkeypatch.setenv("HEALTHOPS_MLFLOW_DIR", str(tmp_path / "mlflow"))
    monkeypatch.setattr(telemetry, "_configured", None)
    dataset = json.loads(DATASET.read_text())
    case = dataset["cases"][0]
    item = fixture(case, dataset["as_of"])
    secret = "PRIVATE-QUESTION-AND-CREDENTIAL-CANARY"
    model = ScriptedModel(
        [
            tool_response("get_screening_summary"),
            {
                "message": {
                    "content": json.dumps(
                        {"topic": "summary", "criterion_ids": case["expected_ids"]}
                    )
                }
            },
        ]
    )
    answer = EvidenceAssistant(model).answer(item, AssistantRequest(question=secret))
    assert answer["monitoring"]["recorded"]
    trace = mlflow.get_trace(answer["monitoring"]["trace_id"])
    assert trace is not None
    serialized = trace.to_json()
    assert secret not in serialized
    assert (
        item["source_snapshot"]["patient_bundle"]["entry"][0]["resource"]["name"][0]["text"]
        not in serialized
    )
    names = [s.name for s in trace.data.spans]
    assert names.count("model_call") == 2
    assert "evidence_tool" in names and "evidence_assistant" in names


def test_telemetry_failure_does_not_break_answer(monkeypatch):
    from healthops import telemetry

    class Broken:
        def start_span(self, **kwargs):
            raise RuntimeError("sensitive internal failure")

    monkeypatch.setattr(telemetry, "configure", lambda: Broken())
    dataset = json.loads(DATASET.read_text())
    answer = EvidenceAssistant(OfflineModel()).answer(
        fixture(dataset["cases"][0], dataset["as_of"]),
        AssistantRequest(question="Explain this screening"),
    )
    assert answer["topic"] == "summary"
    assert not answer["monitoring"]["recorded"]
    assert "sensitive internal failure" not in json.dumps(answer)
