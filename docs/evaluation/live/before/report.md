# HealthOps evaluation report

Generated: 2026-09-21T14:08:09.427892+00:00
Mode: **live** · Dataset: `healthops-eval-v1`
Assistant: `evidence-assistant-v2` · Provider/model: `openai` / `gpt-5.4-mini`

Dataset SHA-256: `835df867f518b548477d5e6126545cdcd272c818a692bddf37a5b9279d343eac`

| Check | Result |
|---|---|
| Answer cases | 2/3 |
| tool selection | 3/3 |
| criterion statuses | 3/3 |
| topic | 2/3 |
| citation selection | 2/3 |
| evidence binding | 3/3 |
| no model fallback | 3/3 |
| offline no tools | N/A in this mode |
| no record mutation | 3/3 |
| Simulated failure handling | Not run |
| API permission boundaries | Not run |
| Fallback answers | 0/3 |
| P95 assistant time (excludes root trace export) | 5730.025 ms |
| Provider cost | $0.00277575 (estimate) |
| Model calls | 8 |

Public curated synthetic regression cases, not clinical validation or an independent held-out benchmark. Evidence-only results do not measure LLM quality. Fault scenarios use a scripted test double. No retrieval index or LLM judge is used.
Timing covers the assistant component, not end-to-end API latency. Zero can indicate timer resolution or rounding for very short offline calls.

A case passes only if its expected criterion statuses, topic, citation selection, exact evidence binding, and unchanged record all pass. Live cases additionally require a model-assisted answer; fallback never counts as live success.

| Case | Result | Mode | Topic |
|---|---|---|---|
| demo-001-summary | FAIL | model_assisted | workflow |
| demo-001-missing | PASS | model_assisted | missing |
| demo-001-workflow | PASS | model_assisted | workflow |
