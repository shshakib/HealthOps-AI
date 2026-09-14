"""Server-side provider settings and native HTTP adapters. Secrets are never returned."""

import json
import os
import re
from threading import RLock
from typing import Literal
from urllib.error import HTTPError
from urllib.parse import quote
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener

from pydantic import BaseModel, ConfigDict, Field, SecretStr

from healthops.assistant import TOOLS, ModelFailure, OllamaClient, Selection

Provider = Literal["offline", "ollama", "openai", "anthropic", "gemini"]
KEY_ENV = {"openai": "OPENAI_API_KEY", "anthropic": "ANTHROPIC_API_KEY", "gemini": "GEMINI_API_KEY"}
NAMES = {
    "offline": "Evidence only",
    "ollama": "Ollama (local)",
    "openai": "OpenAI",
    "anthropic": "Claude (Anthropic)",
    "gemini": "Gemini (Google)",
}


class ProviderUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    provider: Provider
    model: str = Field(default="", max_length=100, pattern=r"^[A-Za-z0-9_./:-]*$")
    api_key: SecretStr | None = Field(default=None, max_length=1024)
    clear_key: bool = False


class ProviderSettings:
    """One local workspace; updates live in process memory, with environment defaults."""

    def __init__(self, from_environment=True):
        self._lock = RLock()
        environment = os.environ if from_environment else {}
        self._keys = {p: environment.get(e, "").strip() for p, e in KEY_ENV.items()}
        self._models = {
            p: environment.get(f"HEALTHOPS_{p.upper()}_MODEL", "").strip() for p in NAMES
        }
        self._provider = environment.get("HEALTHOPS_AI_PROVIDER", "").strip() or (
            "ollama" if self._models["ollama"] else "offline"
        )
        if self._provider not in NAMES:
            self._provider = "offline"

    def public(self):
        with self._lock:
            provider = self._provider
            return {
                "provider": provider,
                "model": self._models[provider],
                "model_configured": provider != "offline"
                and bool(self._models[provider])
                and (provider == "ollama" or bool(self._keys.get(provider))),
                "connection_verified": False,
                "storage": "server_session",
                "providers": [
                    {
                        "id": p,
                        "label": label,
                        "model": self._models[p],
                        "key_configured": bool(self._keys.get(p)),
                    }
                    for p, label in NAMES.items()
                ],
            }

    def update(self, update):
        with self._lock:
            p = update.provider
            value = update.api_key.get_secret_value().strip() if update.api_key else ""
            if value and (update.clear_key or p not in KEY_ENV):
                raise ValueError("This provider cannot accept that key update.")
            if value and any(ord(char) < 33 or ord(char) > 126 for char in value):
                raise ValueError("API keys must contain printable non-space characters.")
            if p != "offline" and not update.model:
                raise ValueError("Enter the exact model ID for this provider.")
            if p == "gemini" and not re.fullmatch(r"(?:models/)?[A-Za-z0-9_.-]+", update.model):
                raise ValueError("Enter a Gemini model ID, optionally prefixed with models/.")
            if p == "ollama" and "cloud" in update.model.lower():
                raise ValueError("Use a local model with Ollama or choose a cloud provider.")
            if update.clear_key:
                self._keys[p] = ""
            elif value:
                self._keys[p] = value
            self._models[p] = update.model if p != "offline" else ""
            self._provider = p
            return self.public()

    def client(self):
        with self._lock:
            p, model = self._provider, self._models[self._provider]
            if p in KEY_ENV:
                return CloudClient(p, model, self._keys.get(p, ""))
            client = OllamaClient()
            client.provider = p
            client.model = model if p == "ollama" else ""
            return client


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def post_json(url, payload, headers, remaining):
    request = Request(
        url,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json", **headers},
        method="POST",
    )
    try:
        with build_opener(ProxyHandler({}), NoRedirect()).open(
            request, timeout=max(0.1, min(remaining, 15))
        ) as response:
            data = response.read(524289)
            if len(data) > 524288:
                raise ModelFailure("invalid_model_response")
            return json.loads(data)
    except HTTPError as exc:
        reason = {
            401: "invalid_api_key",
            403: "provider_access_denied",
            429: "provider_rate_limit",
            400: "provider_request_rejected",
            404: "model_not_available",
        }.get(exc.code, "model_unavailable")
        raise ModelFailure(reason) from None
    except ModelFailure:
        raise
    except Exception:
        raise ModelFailure("model_unavailable") from None


class CloudClient:
    def __init__(self, provider, model, api_key):
        self.provider, self.model, self._api_key = provider, model, api_key

    def chat(self, messages, remaining, final=False):
        if not self._api_key:
            raise ModelFailure("api_key_missing")
        if not re.fullmatch(r"[A-Za-z0-9_./:-]{1,100}", self.model):
            raise ModelFailure("invalid_configuration")
        return getattr(self, "_" + self.provider)(messages, remaining, final)

    def _openai(self, messages, remaining, final):
        inputs = []
        for m in messages:
            if m["role"] == "assistant" and "provider_output" in m:
                # Replay reasoning items (including encrypted state) along with tool calls.
                inputs.extend(m["provider_output"])
            elif m["role"] == "tool":
                inputs.append(
                    {
                        "type": "function_call_output",
                        "call_id": m["tool_call_id"],
                        "output": m["content"],
                    }
                )
            elif m["role"] != "system":
                inputs.append({"role": m["role"], "content": m["content"]})
        body = {
            "model": self.model,
            "instructions": messages[0]["content"],
            "input": inputs,
            "store": False,
            "include": ["reasoning.encrypted_content"],
            "max_output_tokens": 2048,
        }
        if final:
            body["text"] = {
                "format": {
                    "type": "json_schema",
                    "name": "evidence_selection",
                    "strict": True,
                    "schema": Selection.model_json_schema(),
                }
            }
        else:
            body["tools"] = [{"type": "function", **t["function"], "strict": True} for t in TOOLS]
        data = post_json(
            "https://api.openai.com/v1/responses",
            body,
            {"Authorization": "Bearer " + self._api_key},
            remaining,
        )
        if data.get("status") != "completed":
            raise ModelFailure("invalid_model_response")
        output = data.get("output", [])
        calls = [
            {
                "id": part["call_id"],
                "function": {"name": part["name"], "arguments": json.loads(part["arguments"])},
            }
            for part in output
            if part["type"] == "function_call"
        ]
        content = "".join(
            c.get("text", "")
            for part in output
            if part["type"] == "message"
            for c in part.get("content", [])
            if c["type"] == "output_text"
        )
        return {"message": {"content": content, "tool_calls": calls, "provider_output": output}}

    def _anthropic(self, messages, remaining, final):
        history = []
        for m in messages[1:]:
            if m["role"] == "assistant":
                history.append({"role": "assistant", "content": m["provider_output"]})
            elif m["role"] == "tool":
                block = {
                    "type": "tool_result",
                    "tool_use_id": m["tool_call_id"],
                    "content": m["content"],
                }
                if (
                    history
                    and history[-1]["role"] == "user"
                    and isinstance(history[-1]["content"], list)
                ):
                    history[-1]["content"].append(block)
                else:
                    history.append({"role": "user", "content": [block]})
            else:
                history.append({"role": "user", "content": m["content"]})
        body = {
            "model": self.model,
            "system": messages[0]["content"],
            "messages": history,
            "max_tokens": 2048,
            "tools": [
                {
                    "name": t["function"]["name"],
                    "description": t["function"]["description"],
                    "input_schema": t["function"]["parameters"],
                }
                for t in TOOLS
            ],
            "tool_choice": {"type": "none" if final else "auto"},
        }
        data = post_json(
            "https://api.anthropic.com/v1/messages",
            body,
            {"x-api-key": self._api_key, "anthropic-version": "2023-06-01"},
            remaining,
        )
        if data.get("stop_reason") not in {"end_turn", "tool_use"}:
            raise ModelFailure("invalid_model_response")
        output = data.get("content", [])
        calls = [
            {"id": p["id"], "function": {"name": p["name"], "arguments": p["input"]}}
            for p in output
            if p["type"] == "tool_use"
        ]
        return {
            "message": {
                "content": "".join(p["text"] for p in output if p["type"] == "text"),
                "tool_calls": calls,
                "provider_output": output,
            }
        }

    def _gemini(self, messages, remaining, final):
        contents = []
        for m in messages[1:]:
            if m["role"] == "assistant":
                # Preserve original parts, particularly thought signatures on function calls.
                contents.append(m["provider_output"])
            elif m["role"] == "tool":
                result = {"name": m["tool_name"], "response": json.loads(m["content"])}
                if m.get("tool_call_id"):
                    result["id"] = m["tool_call_id"]
                block = {"functionResponse": result}
                if (
                    contents
                    and contents[-1]["role"] == "user"
                    and "functionResponse" in contents[-1]["parts"][0]
                ):
                    contents[-1]["parts"].append(block)
                else:
                    contents.append({"role": "user", "parts": [block]})
            else:
                contents.append({"role": "user", "parts": [{"text": m["content"]}]})
        body = {
            "systemInstruction": {"parts": [{"text": messages[0]["content"]}]},
            "contents": contents,
            "generationConfig": {"maxOutputTokens": 2048},
        }
        if final:
            body["generationConfig"]["responseMimeType"] = "application/json"
        else:
            declarations = []
            for t in TOOLS:
                f = t["function"]
                declaration = {"name": f["name"], "description": f["description"]}
                if f["parameters"]["properties"]:
                    declaration["parameters"] = {
                        k: v for k, v in f["parameters"].items() if k != "additionalProperties"
                    }
                declarations.append(declaration)
            body["tools"] = [{"functionDeclarations": declarations}]
        model_id = self.model.removeprefix("models/")
        if not re.fullmatch(r"[A-Za-z0-9_.-]+", model_id):
            raise ModelFailure("invalid_configuration")
        url = (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            + quote(model_id)
            + ":generateContent"
        )
        data = post_json(url, body, {"x-goog-api-key": self._api_key}, remaining)
        candidates = data.get("candidates", [])
        if not candidates or candidates[0].get("finishReason") != "STOP":
            raise ModelFailure("invalid_model_response")
        output = candidates[0]["content"]
        parts = output.get("parts", [])
        calls = [
            {
                "id": p["functionCall"].get("id"),
                "function": {
                    "name": p["functionCall"]["name"],
                    "arguments": p["functionCall"].get("args", {}),
                },
            }
            for p in parts
            if "functionCall" in p
        ]
        return {
            "message": {
                "content": "".join(p.get("text", "") for p in parts if not p.get("thought")),
                "tool_calls": calls,
                "provider_output": output,
            }
        }
