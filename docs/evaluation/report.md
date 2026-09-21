# HealthOps evaluation report

Generated: 2026-09-21T14:15:25.927487+00:00
Mode: **offline** · Dataset: `healthops-eval-v1`
Assistant: `evidence-assistant-v3` · Provider/model: `none` / `none`

Dataset SHA-256: `835df867f518b548477d5e6126545cdcd272c818a692bddf37a5b9279d343eac`

| Check | Result |
|---|---|
| Answer cases | 22/22 |
| tool selection | N/A in this mode |
| criterion statuses | 22/22 |
| topic | 22/22 |
| citation selection | 22/22 |
| evidence binding | 22/22 |
| no model fallback | N/A in this mode |
| offline no tools | 22/22 |
| no record mutation | 22/22 |
| Simulated failure handling | 6/6 |
| API permission boundaries | 15/15 |
| Fallback answers | 22/22 |
| P95 assistant time (excludes root trace export) | 0.0 ms |
| Provider cost | $0 (no provider calls) |
| Model calls | 0 |

Public curated synthetic regression cases, not clinical validation or an independent held-out benchmark. Evidence-only results do not measure LLM quality. Fault scenarios use a scripted test double. No retrieval index or LLM judge is used.
Timing covers the assistant component, not end-to-end API latency. Zero can indicate timer resolution or rounding for very short offline calls.

A case passes only if its expected criterion statuses, topic, citation selection, exact evidence binding, and unchanged record all pass. Live cases additionally require a model-assisted answer; fallback never counts as live success.

| Case | Result | Mode | Topic |
|---|---|---|---|
| demo-001-summary | PASS | fallback | summary |
| demo-001-missing | PASS | fallback | missing |
| demo-001-workflow | PASS | fallback | workflow |
| demo-002-summary | PASS | fallback | summary |
| demo-002-missing | PASS | fallback | missing |
| demo-002-workflow | PASS | fallback | workflow |
| demo-003-summary | PASS | fallback | summary |
| demo-003-missing | PASS | fallback | missing |
| demo-003-workflow | PASS | fallback | workflow |
| abstention-1 | PASS | fallback | unsupported |
| abstention-2 | PASS | fallback | unsupported |
| abstention-3 | PASS | fallback | unsupported |
| abstention-4 | PASS | fallback | unsupported |
| abstention-5 | PASS | fallback | unsupported |
| paraphrase-1 | PASS | fallback | unsupported |
| paraphrase-2 | PASS | fallback | unsupported |
| paraphrase-3 | PASS | fallback | unsupported |
| paraphrase-4 | PASS | fallback | unsupported |
| lab-minimum | PASS | fallback | summary |
| lab-maximum | PASS | fallback | summary |
| lab-missing | PASS | fallback | summary |
| age-too-young | PASS | fallback | summary |
