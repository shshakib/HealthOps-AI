# Live assistant evaluation: GPT-5.4 mini

On September 21, 2026, the updated assistant passed **22/22 public synthetic
regression cases** using real OpenAI API calls to `gpt-5.4-mini`. Every answer was
model-assisted; no fallback counted as a success. All 22 traces were independently
retrieved from the local MLflow database after the run.

## Results

| Run | Assistant | Passed | Model calls | P95 assistant time | Estimated provider cost (USD) |
|---|---|---:|---:|---:|---:|
| [Original smoke test](before/report.md) | v2 | 2/3 | 8 | 5.730 s | $0.00277575 |
| [Same questions after the change](retest/report.md) | v3 | 3/3 | 7 | 3.941 s | $0.00288375 |
| [Full regression set](full/report.md) | v3 | 22/22 | 49 | 3.512 s | $0.02006700 |

The retest and full run together cost an estimated **$0.02295075**. The full run
reported 21,776 input tokens and 830 output tokens, with no cached input tokens.
These are calculations from provider-reported usage and the
[dated pricing assumptions](../gpt-5.4-mini-pricing.json), not an invoice.

Each report has a matching machine-readable JSON file:
[before](before/report.json), [retest](retest/report.json), [full](full/report.json).
They preserve the dataset hash, assistant version, model, per-case checks,
latencies, token usage, trace IDs, and MLflow run ID.

## What changed

The original assistant treated **“Explain this screening”** as a request for human
review options. It selected `workflow` and returned no criterion citations instead
of summarizing the findings. The grader rejected that answer even though the
model connected successfully and used allowed tools.

Version 3 defines the routing categories explicitly: summaries explain recorded
findings, missing-evidence questions identify unresolved requirements, specific
criterion questions retrieve evidence, and workflow questions describe human
review options. It tells the model to choose based on the question rather than
the patient's screening outcome. The tool permissions, evidence assembly,
evaluation dataset, expected answers, and passing criteria were unchanged.

The full run checked findings, unknowns, boundary cases, paraphrases, and five
out-of-scope requests. Each case required the expected topic, exact citation
selection, source-bound evidence, correct tools, no fallback, and no change to the
fixture assessment. Asking the assistant cannot submit a human review.

## Reproduce

Configure OpenAI with model ID `gpt-5.4-mini` in `.env` for the Docker command below.
For a three-case check using dashboard settings instead, see the
[authenticated API command](../../evaluation.md#run-a-bounded-real-model-smoke-test).
After intentionally enabling the provider, run:

```powershell
docker compose --profile monitoring up --build -d --wait --wait-timeout 600
docker compose exec -T healthops python -c "from pathlib import Path; Path('/data/evaluations').mkdir(exist_ok=True)"
docker compose cp docs/evaluation/gpt-5.4-mini-pricing.json healthops:/data/evaluations/pricing.json
docker compose exec -T healthops python -m healthops.evaluation --mode live --limit 22 --trace --pricing /data/evaluations/pricing.json --output /data/evaluations/live-full
```

This makes paid model calls, up to 88 for the full set. Verify current pricing
before reusing the dated rates. Open [local MLflow](http://127.0.0.1:5000/) to inspect
the **HealthOps evidence assistant** experiment. The CLI tests fixtures in memory
and does not add assessments or reviews to the live ledger. CI remains offline
and does not use provider keys.

## Limits of this result

This is one full run of a small, public regression set. The prompt was adjusted
after inspecting a failure on this set, so this is **not a held-out accuracy
estimate**, clinical validation, or proof that all future questions will pass.
The model ID is an alias rather than a pinned model snapshot. Timing is component
latency, including child tracing overhead but excluding root trace export; these
small runs do not establish a reliable latency improvement. No other provider was
tested live. Permission boundaries and simulated provider failures are measured
separately by the [offline suite](../report.md).
