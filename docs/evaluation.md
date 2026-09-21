# Evaluation and local monitoring

The [measured baseline](evaluation/report.md) contains **22 offline answer cases,
six simulated provider/tool failures, and 15 API permission checks**. The matching
[JSON report](evaluation/report.json) records each outcome and the dataset hash.
These public, curated synthetic regression cases are not a held-out benchmark or
clinical validation. Offline results do not measure real model quality.

## What is checked

The versioned dataset is `src/healthops/evaluation_cases.json`. It covers met,
not-met, stale/missing evidence, age/lab boundaries, question routing, citations,
human-review steps, and requests outside the assistant's scope. Expected values
are explicit fixtures. The grader checks exact evidence binding and that asking
the assistant leaves the saved record unchanged. In live mode, fallback counts
as failure; successful tool selection and a model-assisted answer are required.
Model-only checks are N/A in offline mode.

The six fault cases use a scripted protocol test double. Permission checks use
real session middleware, isolated temporary accounts, and a temporary ledger.
They never create reviews or modify patients in the running application.
CI runs this baseline without provider keys and fails on a regression or missing traces.

## Reproduce the baseline

Install the optional monitoring dependencies, then run from the repository root:

```powershell
& '.\.venv\Scripts\python.exe' -m pip install -c requirements-observability.lock -e '.[dev,observability]'
& '.\.venv\Scripts\python.exe' -m healthops.evaluation --trace --output .local/evaluation
```

This writes `report.json` and `report.md`, and stores MLflow data in `.local/mlflow`.
The constraints file pins the tested dependency versions; platform-specific and
build dependencies can differ. Timings cover the assistant component, excluding
the root trace export; child tracing overhead is included. They are not API load
test results. Very short offline calls can round to zero.

## Inspect Docker monitoring

```powershell
docker compose --profile monitoring up --build -d --wait --wait-timeout 600
docker compose exec -T healthops python -m healthops.evaluation --trace --output /data/evaluations/baseline
```

Open [MLflow](http://127.0.0.1:5000/), select **HealthOps evidence assistant**, and
inspect **Traces** or the evaluation runs. The report artifact lists the case trace
IDs; traces are recorded separately from the evaluation run. Asking a question in
the HealthOps dashboard also generates a trace. Model/tool child spans appear only
when those operations happen. Evidence-only answers have a root span.

Compose enables tracing for HealthOps even without the monitoring UI profile.
`HEALTHOPS_TRACING=1` enables it for a direct Python installation;
`HEALTHOPS_MLFLOW_DIR` controls the local data directory. Logging failures leave
the assistant usable and are surfaced by its monitoring status. The administrator
can inspect `GET /api/v1/admin/monitoring`. Trace IDs and capture status are also
returned with assistant answers. Tests independently read traces back from MLflow.

MLflow shares the persistent application volume under `/data/mlflow`. Ordinary
`docker compose down` preserves it. Its UI is a **trusted local administrator
console**, bound to loopback, with no HealthOps login or role checks. Do not expose
port 5000 publicly. HealthOps roles govern its API, not direct local database access.

Only explicit operational fields are traced: route, mode, fallback reason, timings,
allowed tool names, counts, and provider-reported tokens when available. Questions,
patient names/IDs, clinical findings, prompts, tool arguments/results, credentials,
and exception messages are excluded. No MLflow provider autologging is enabled.
An integration test checks sensitive canaries against a stored trace. Evaluation
artifacts contain only the public fixture questions and their results. MLflow's
own usage telemetry is disabled.

## Run a bounded real-model smoke test

As an Admin, configure the provider, exact model ID, and key privately under
**Model connection settings** in the dashboard. Settings entered there last until
the app restarts. Then use the same running server:

```powershell
& '.\.venv\Scripts\python.exe' -m healthops.evaluation --mode live --api-url http://127.0.0.1:18000 --limit 3 --trace --output .local/evaluation-live
```

The CLI prompts for your HealthOps username/password; it does not ask for or
retrieve the provider key. The admin-only endpoint accepts 1–5 cases and permits
one evaluation at a time per app process. The default three cases use at most
12 model calls total (four per answer), each answer has a 40-second deadline.
Provider calls may cost money. A disconnected CLI does not cancel an in-flight run.
Reports persist under `/data/evaluations/<report-id>` in Docker and are returned
to the CLI. Test records are built in memory, not added to the review ledger.

For all 22 cases, use `--mode live --limit 22` without `--api-url` in a local
process configured with the environment variables in [the assistant guide](assistant.md).
That permits up to 88 model calls. Dashboard settings do not transfer to a separate
process. Start with the bounded smoke test before intentionally running the full set.

Reports include provider/model, fallback count, component latency, model calls,
and provider-reported token counts. Missing usage remains unknown. Cost remains
unknown unless `--pricing <local-json-file>` supplies verified rates with these fields:
`provider`, `model`, `source` (pricing-page URL), `checked_on` (YYYY-MM-DD),
`input_per_million_usd`, and `output_per_million_usd`. Add
`cached_input_per_million_usd` and `cache_creation_per_million_usd` when the provider
reports those tokens. Provider and model must match before any calls are made.
Estimates require complete usage and applicable rates; failed calls can still be
billable. This estimate is not a provider invoice.

**Current limitation:** no real provider/model was configured for the published
offline baseline. Real-model quality, latency, and cost remain unmeasured.
There is no retrieval index, retrieval precision score, LLM judge, or claim of
clinical correctness. A separate unseen dataset and domain review are future work.

Implementation references:
[MLflow manual tracing](https://mlflow.org/docs/latest/genai/tracing/app-instrumentation/manual-tracing/),
[MLflow token accounting](https://mlflow.org/docs/latest/genai/tracing/token-usage-cost/),
[OpenAI response usage](https://developers.openai.com/api/reference/python/resources/responses/methods/retrieve),
[Anthropic message usage](https://platform.claude.com/docs/en/api/messages/create),
[Gemini usage metadata](https://ai.google.dev/api/generate-content),
[Ollama chat statistics](https://docs.ollama.com/api/chat).
