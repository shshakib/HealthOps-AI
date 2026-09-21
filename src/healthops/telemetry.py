"""Opt-in local MLflow traces containing operational metadata, never clinical text."""

import os
from contextlib import contextmanager
from pathlib import Path
from threading import RLock

_lock = RLock()
_configured = None
_error = None


def configure():
    global _configured, _error
    if os.environ.get("HEALTHOPS_TRACING") != "1":
        return None
    directory = Path(os.environ.get("HEALTHOPS_MLFLOW_DIR", ".local/mlflow")).resolve()
    with _lock:
        try:
            # Disable MLflow's own usage telemetry; this workspace is local by default.
            os.environ["MLFLOW_DISABLE_TELEMETRY"] = "true"
            os.environ["MLFLOW_ENABLE_ASYNC_TRACE_LOGGING"] = "false"
            import mlflow

            if _configured != directory:
                directory.mkdir(parents=True, exist_ok=True)
                mlflow.set_tracking_uri("sqlite:///" + (directory / "tracking.db").as_posix())
                client = mlflow.MlflowClient()
                if client.get_experiment_by_name("HealthOps evidence assistant") is None:
                    client.create_experiment(
                        "HealthOps evidence assistant",
                        artifact_location=(directory / "artifacts").as_uri(),
                    )
                mlflow.set_experiment("HealthOps evidence assistant")
                _configured = directory
                _error = None
            return mlflow
        except Exception:
            _error = "tracing_unavailable"
            return None


class SafeSpan:
    def __init__(self, span=None):
        self.span = span
        self.trace_id = getattr(span, "trace_id", None)
        self.recorded = False

    def attributes(self, values):
        if self.span:
            try:
                self.span.set_attributes(values)
            except Exception:
                pass

    def outputs(self, values):
        if self.span:
            try:
                self.span.set_outputs(values)
            except Exception:
                pass


@contextmanager
def span(name, kind="CHAIN", attributes=None):
    """Explicit fields only. Never pass model arguments, result text, or exception messages."""
    global _error
    context, wrapper = None, SafeSpan()
    mlflow = configure()
    if mlflow:
        try:
            context = mlflow.start_span(name=name, span_type=kind)
            wrapper = SafeSpan(context.__enter__())
            wrapper.attributes(attributes or {})
        except Exception:
            _error = "tracing_unavailable"
            context = None
    try:
        yield wrapper
    except BaseException:
        if wrapper.span:
            try:
                wrapper.span.set_status("ERROR")
            except Exception:
                pass
        raise
    finally:
        if context:
            try:
                # Avoid MLflow automatically capturing potentially sensitive exception text.
                context.__exit__(None, None, None)
                wrapper.recorded = True
                _error = None
            except Exception:
                _error = "tracing_unavailable"


def status():
    enabled = os.environ.get("HEALTHOPS_TRACING") == "1"
    available = bool(configure()) if enabled else False
    return {
        "enabled": enabled,
        "ready": available and _error is None,
        "error": _error if enabled else None,
        "capture": "operational_metadata_only",
    }


def normalize_usage(provider, data):
    """Provider-reported tokens only. Missing/invalid accounting remains unavailable."""
    if provider == "openai":
        raw = data.get("usage") or {}
        inputs, outputs = raw.get("input_tokens"), raw.get("output_tokens")
        cached = (raw.get("input_tokens_details") or {}).get("cached_tokens", 0)
        created = 0
    elif provider == "anthropic":
        raw = data.get("usage") or {}
        cached, created = (
            raw.get("cache_read_input_tokens", 0),
            raw.get("cache_creation_input_tokens", 0),
        )
        inputs, outputs = raw.get("input_tokens"), raw.get("output_tokens")
        if all(type(v) is int for v in (inputs, cached, created)):
            inputs += cached + created
    elif provider == "gemini":
        raw = data.get("usageMetadata") or {}
        inputs = raw.get("promptTokenCount")
        outputs = raw.get("candidatesTokenCount")
        thoughts = raw.get("thoughtsTokenCount", 0)
        if type(outputs) is int and type(thoughts) is int:
            outputs += thoughts
        cached, created = raw.get("cachedContentTokenCount", 0), 0
    else:
        inputs, outputs = data.get("prompt_eval_count"), data.get("eval_count")
        cached, created = 0, 0
    if not all(type(v) is int and v >= 0 for v in (inputs, outputs, cached, created)):
        return None
    if cached + created > inputs:
        return None
    return {
        "input_tokens": inputs,
        "output_tokens": outputs,
        "total_tokens": inputs + outputs,
        "cached_input_tokens": cached,
        "cache_creation_input_tokens": created,
    }


class Usage:
    def __init__(self):
        self.calls = 0
        self.reported_calls = 0
        self.tokens = dict.fromkeys(
            (
                "input_tokens",
                "output_tokens",
                "total_tokens",
                "cached_input_tokens",
                "cache_creation_input_tokens",
            ),
            0,
        )

    def add(self, usage):
        if usage:
            self.reported_calls += 1
            for key in self.tokens:
                self.tokens[key] += usage[key]

    def public(self):
        return {
            "model_calls": self.calls,
            "reported_calls": self.reported_calls,
            "complete": self.calls == self.reported_calls,
            "tokens": self.tokens if self.reported_calls else None,
        }
