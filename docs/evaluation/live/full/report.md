# HealthOps evaluation report

Generated: 2026-09-21T14:21:09.476237+00:00
Mode: **live** · Dataset: `healthops-eval-v1`
Assistant: `evidence-assistant-v3` · Provider/model: `openai` / `gpt-5.4-mini`

Dataset SHA-256: `835df867f518b548477d5e6126545cdcd272c818a692bddf37a5b9279d343eac`

| Check | Result |
|---|---|
| Answer cases | 22/22 |
| tool selection | 22/22 |
| criterion statuses | 22/22 |
| topic | 22/22 |
| citation selection | 22/22 |
| evidence binding | 22/22 |
| no model fallback | 22/22 |
| offline no tools | N/A in this mode |
| no record mutation | 22/22 |
| Simulated failure handling | Not run |
| API permission boundaries | Not run |
| Fallback answers | 0/22 |
| P95 assistant time (excludes root trace export) | 3511.548 ms |
| Provider cost | $0.02006700 (estimate) |
| Model calls | 49 |

Public curated synthetic regression cases, not clinical validation or an independent held-out benchmark. Evidence-only results do not measure LLM quality. Fault scenarios use a scripted test double. No retrieval index or LLM judge is used.
Timing covers the assistant component, not end-to-end API latency. Zero can indicate timer resolution or rounding for very short offline calls.

A case passes only if its expected criterion statuses, topic, citation selection, exact evidence binding, and unchanged record all pass. Live cases additionally require a model-assisted answer; fallback never counts as live success.

| Case | Result | Mode | Topic |
|---|---|---|---|
| demo-001-summary | PASS | model_assisted | summary |
| demo-001-missing | PASS | model_assisted | missing |
| demo-001-workflow | PASS | model_assisted | workflow |
| demo-002-summary | PASS | model_assisted | summary |
| demo-002-missing | PASS | model_assisted | missing |
| demo-002-workflow | PASS | model_assisted | workflow |
| demo-003-summary | PASS | model_assisted | summary |
| demo-003-missing | PASS | model_assisted | missing |
| demo-003-workflow | PASS | model_assisted | workflow |
| abstention-1 | PASS | model_assisted | unsupported |
| abstention-2 | PASS | model_assisted | unsupported |
| abstention-3 | PASS | model_assisted | unsupported |
| abstention-4 | PASS | model_assisted | unsupported |
| abstention-5 | PASS | model_assisted | unsupported |
| paraphrase-1 | PASS | model_assisted | summary |
| paraphrase-2 | PASS | model_assisted | missing |
| paraphrase-3 | PASS | model_assisted | workflow |
| paraphrase-4 | PASS | model_assisted | criterion |
| lab-minimum | PASS | model_assisted | summary |
| lab-maximum | PASS | model_assisted | summary |
| lab-missing | PASS | model_assisted | summary |
| age-too-young | PASS | model_assisted | summary |
