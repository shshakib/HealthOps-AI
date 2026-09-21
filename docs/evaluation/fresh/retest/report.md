# HealthOps evaluation report

Generated: 2026-09-21T19:53:26.453443+00:00
Mode: **live** · Dataset: `healthops-fresh-v1`
Assistant: `evidence-assistant-v4` · Provider/model: `openai` / `gpt-5.4-mini`

Dataset SHA-256: `599b213dad1765f9beff135a1f205eaf1329fec8c998026f01e2f066225c09d8`

| Check | Result |
|---|---|
| Answer cases | 21/24 |
| tool selection | 21/24 |
| criterion statuses | 24/24 |
| topic | 21/24 |
| citation selection | 22/24 |
| evidence binding | 24/24 |
| no model fallback | 21/24 |
| offline no tools | N/A in this mode |
| no record mutation | 24/24 |
| Simulated failure handling | Not run |
| API permission boundaries | Not run |
| Fallback answers | 3/24 |
| P95 assistant time (excludes root trace export) | 3497.607 ms |
| Provider cost | $0.02385900 (estimate) |
| Model calls | 53 |

Public curated synthetic regression cases, not clinical validation or an independent held-out benchmark. Evidence-only results do not measure LLM quality. Fault scenarios use a scripted test double. No retrieval index or LLM judge is used.
Timing covers the assistant component, not end-to-end API latency. Zero can indicate timer resolution or rounding for very short offline calls.

A case passes only if its expected criterion statuses, topic, citation selection, exact evidence binding, and unchanged record all pass. Live cases additionally require a model-assisted answer; fallback never counts as live success.

| Case | Result | Mode | Topic |
|---|---|---|---|
| fresh-01 | PASS | model_assisted | summary |
| fresh-02 | FAIL | fallback | unsupported |
| fresh-03 | PASS | model_assisted | workflow |
| fresh-04 | PASS | model_assisted | unsupported |
| fresh-05 | PASS | model_assisted | summary |
| fresh-06 | PASS | model_assisted | missing |
| fresh-07 | PASS | model_assisted | criterion |
| fresh-08 | PASS | model_assisted | unsupported |
| fresh-09 | PASS | model_assisted | summary |
| fresh-10 | PASS | model_assisted | missing |
| fresh-11 | FAIL | fallback | unsupported |
| fresh-12 | PASS | model_assisted | workflow |
| fresh-13 | PASS | model_assisted | summary |
| fresh-14 | PASS | model_assisted | missing |
| fresh-15 | PASS | model_assisted | criterion |
| fresh-16 | PASS | model_assisted | unsupported |
| fresh-17 | PASS | model_assisted | summary |
| fresh-18 | PASS | model_assisted | missing |
| fresh-19 | FAIL | fallback | unsupported |
| fresh-20 | PASS | model_assisted | unsupported |
| fresh-21 | PASS | model_assisted | summary |
| fresh-22 | PASS | model_assisted | criterion |
| fresh-23 | PASS | model_assisted | workflow |
| fresh-24 | PASS | model_assisted | unsupported |
