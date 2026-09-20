import copy
import json
from datetime import date
from urllib.error import HTTPError

import pytest
from auth_support import TestClient

from healthops import providers
from healthops.api import create_app
from healthops.assistant import AssistantRequest, EvidenceAssistant, ModelFailure
from healthops.demo_data import DEMO_AS_OF, TRIAL, get_patient
from healthops.providers import CloudClient, ProviderSettings, ProviderUpdate
from healthops.screening import screen_patient
from healthops.store import ReviewStore

SECRET = "fake-provider-key-for-tests-only"
HEADERS = {"x-healthops-request": "1"}


@pytest.fixture
def client(tmp_path):
    with TestClient(
        create_app(tmp_path / "test.db", provider_settings=ProviderSettings(False))
    ) as c:
        yield c


def test_settings_no_key_echo_and_blank_preserves_key(client):
    payload = {"provider": "openai", "model": "test-model", "api_key": SECRET}
    result = client.post("/api/v1/assistant/settings", json=payload, headers=HEADERS)
    assert result.status_code == 200 and SECRET not in result.text
    assert result.headers["cache-control"] == "no-store"
    assert result.json()["model_configured"]
    payload.pop("api_key")
    payload["model"] = "other-model"
    assert client.post("/api/v1/assistant/settings", json=payload, headers=HEADERS).json()[
        "model_configured"
    ]
    assert SECRET not in client.get("/api/v1/assistant/status").text
    payload["clear_key"] = True
    cleared = client.post("/api/v1/assistant/settings", json=payload, headers=HEADERS).json()
    assert not cleared["model_configured"]


@pytest.mark.parametrize(
    "payload",
    [
        {"provider": "invalid", "api_key": SECRET},
        {"provider": "openai", "model": "test", "api_key": SECRET * 60},
        {"provider": "openai", "model": "test", "api_key": {"secret": SECRET}},
        {"provider": "openai", "model": "test", "api_key": SECRET, "bad_field": SECRET},
    ],
)
def test_validation_errors_never_echo_keys(client, payload):
    response = client.post("/api/v1/assistant/settings", json=payload, headers=HEADERS)
    assert response.status_code == 422 and SECRET not in response.text


@pytest.mark.parametrize(
    "headers",
    [
        {},
        {**HEADERS, "origin": "https://other-site.example"},
        {**HEADERS, "host": "rebinding.example"},
        {**HEADERS, "origin": "null"},
    ],
)
def test_rejects_cross_site_and_unmarked_configuration(client, headers):
    response = client.post(
        "/api/v1/assistant/settings",
        headers=headers,
        json={"provider": "openai", "model": "test", "api_key": SECRET},
    )
    assert response.status_code == 403
    assert client.get("/api/v1/assistant/status").json()["provider"] == "offline"


def test_provider_switching_preserves_other_keys_and_memory_only():
    settings = ProviderSettings(False)
    settings.update(ProviderUpdate(provider="openai", model="a", api_key=SECRET))
    first = settings.client()
    settings.update(ProviderUpdate(provider="gemini", model="models/b", api_key="second-fake-key"))
    settings.update(ProviderUpdate(provider="openai", model="a"))
    assert settings.public()["model_configured"]
    assert first.provider == "openai" and first.model == "a"
    assert ProviderSettings(False).public()["provider"] == "offline"
    settings.update(ProviderUpdate(provider="offline"))
    assert not settings.client().model


def test_configured_cloud_requires_same_origin_header_and_can_bypass(client, monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("No provider call should occur")

    monkeypatch.setattr(providers, "post_json", forbidden)
    client.post(
        "/api/v1/assistant/settings",
        headers=HEADERS,
        json={"provider": "openai", "model": "test", "api_key": SECRET},
    )
    item = client.post("/api/v1/screenings", json={}).json()
    path = f"/api/v1/screenings/{item['id']}/assistant"
    assert (
        client.post(path, headers={}, json={"question": "Explain this screening"}).status_code
        == 403
    )
    result = client.post(path, json={"question": "Explain this screening", "use_model": False})
    assert result.status_code == 200 and result.json()["mode"] == "fallback"


def native(provider, calls=None, topic="workflow", ids=None):
    text = json.dumps({"topic": topic, "criterion_ids": ids or []})
    if provider == "openai":
        output = (
            (
                [
                    {
                        "type": "reasoning",
                        "id": "reason-1",
                        "summary": [],
                        "encrypted_content": "opaque-reasoning-state",
                    }
                ]
                + [
                    {
                        "type": "function_call",
                        "call_id": f"call-{i}",
                        "name": name,
                        "arguments": json.dumps(args),
                    }
                    for i, (name, args) in enumerate(calls)
                ]
            )
            if calls
            else [
                {
                    "type": "message",
                    "role": "assistant",
                    "content": [{"type": "output_text", "text": text}],
                }
            ]
        )
        return {"status": "completed", "output": output}
    if provider == "anthropic":
        content = (
            [
                {"type": "tool_use", "id": f"call-{i}", "name": name, "input": args}
                for i, (name, args) in enumerate(calls)
            ]
            if calls
            else [{"type": "text", "text": text}]
        )
        return {"stop_reason": "tool_use" if calls else "end_turn", "content": content}
    parts = (
        [
            {
                "functionCall": {"id": f"call-{i}", "name": name, "args": args},
                "thoughtSignature": "opaque-signature",
            }
            for i, (name, args) in enumerate(calls)
        ]
        if calls
        else [{"text": text}]
    )
    return {"candidates": [{"finishReason": "STOP", "content": {"role": "model", "parts": parts}}]}


@pytest.mark.parametrize("provider", ["openai", "anthropic", "gemini"])
def test_native_protocol_roundtrip_preserves_ids_and_provider_state(
    provider, monkeypatch, tmp_path
):
    calls = [("get_screening_summary", {}), ("get_review_workflow", {})]
    responses = iter([native(provider, calls), native(provider)])
    sent = []

    def transport(url, payload, headers, remaining):
        sent.append((url, copy.deepcopy(payload), headers))
        return next(responses)

    monkeypatch.setattr(providers, "post_json", transport)
    bundle = get_patient("demo-002")
    item = ReviewStore(tmp_path / "test.db").save_screening(
        screen_patient(bundle, TRIAL, date.fromisoformat(DEMO_AS_OF)), bundle, TRIAL
    )
    result = EvidenceAssistant(CloudClient(provider, "test-model", SECRET)).answer(
        item, AssistantRequest(question="What can a reviewer do next?")
    )
    assert result["mode"] == "model_assisted" and result["provider"] == provider
    assert SECRET not in json.dumps(result)
    assert len(sent) == 2 and SECRET not in sent[0][0]
    assert SECRET not in json.dumps(sent[0][1])
    followup = sent[1][1]
    if provider == "openai":
        assert sent[0][2]["Authorization"] == "Bearer " + SECRET
        assert followup["store"] is False
        assert followup["input"][1]["encrypted_content"] == "opaque-reasoning-state"
        assert [
            i["call_id"] for i in followup["input"] if i.get("type") == "function_call_output"
        ] == [
            "call-0",
            "call-1",
        ]
    elif provider == "anthropic":
        assert sent[0][2]["x-api-key"] == SECRET
        assert [b["tool_use_id"] for b in followup["messages"][-1]["content"]] == [
            "call-0",
            "call-1",
        ]
    else:
        assert sent[0][2]["x-goog-api-key"] == SECRET
        assert followup["contents"][1]["parts"][0]["thoughtSignature"] == "opaque-signature"
        assert [p["functionResponse"]["id"] for p in followup["contents"][-1]["parts"]] == [
            "call-0",
            "call-1",
        ]


@pytest.mark.parametrize(
    "code,reason",
    [
        (401, "invalid_api_key"),
        (429, "provider_rate_limit"),
        (404, "model_not_available"),
        (503, "model_unavailable"),
    ],
)
def test_provider_errors_are_sanitized(monkeypatch, code, reason):
    class Opener:
        def open(self, *args, **kwargs):
            raise HTTPError("https://example.com/" + SECRET, code, SECRET, {}, None)

    monkeypatch.setattr(providers, "build_opener", lambda *args: Opener())
    with pytest.raises(ModelFailure, match=reason) as error:
        providers.post_json("https://api.openai.com/v1/responses", {}, {}, 1)
    assert SECRET not in str(error.value)


@pytest.mark.parametrize("provider", ["openai", "anthropic", "gemini"])
def test_missing_key_never_calls_network(provider, monkeypatch):
    monkeypatch.setattr(
        providers, "post_json", lambda *args: pytest.fail("Unexpected network call")
    )
    with pytest.raises(ModelFailure, match="api_key_missing"):
        CloudClient(provider, "test-model", "").chat([], 1)
