# Fresh synthetic evaluation — September 21, 2026

The frozen assistant v3 passed **23/24** new questions across **six new synthetic
patient variants** on its first live run. A proposed prompt-only change (v4)
passed **21/24** on a retest and was **not adopted**. The release keeps v3 and its
safe fallback behavior. Neither run changed a patient assessment or review record.

| Run | Assistant | Passed | Fallbacks | Model calls | P95 assistant time | Estimated cost |
|---|---|---:|---:|---:|---:|---:|
| [First pass](first/report.md) | v3 | 23/24 | 1 | 56 | 3.921 s | $0.023493 |
| [Rejected prompt experiment](retest/report.md) | v4 | 21/24 | 3 | 53 | 3.498 s | $0.023859 |

Both used OpenAI `gpt-5.4-mini`. Total estimated provider cost: **$0.047352**,
using the [dated pricing file](../gpt-5.4-mini-pricing.json). These are estimates,
not invoices. All 48 root traces were retrieved from the persisted MLflow store.
Timing measures the assistant component, not browser or API load performance.

## How the cases were prepared

[The protocol](protocol.json) was saved before the first live call. It records
the assistant commit, source fingerprints, dataset fingerprint, and call budget.
[The dataset](../../../data/evaluation/fresh-v1.json) fixes expected statuses,
topics, and citations. No questions duplicate the original 22-case regression set.
Profiles cover exact age/date boundaries, missing birth date, absent/unconfirmed
diagnosis, unsupported units, future laboratory dates, and conflicting latest labs.

The same author who knows the implementation prepared these cases. They are a
prospective first-pass check, **not independently blinded validation**. The patients
are handcrafted fixtures, not new Synthea outputs. The trial is fictional. The
model ID is an alias. The frozen grader uses explicit expectations and exact
saved-evidence comparisons, not an LLM judge or clinician scoring.

## What failed and what was done

On v3, `fresh-11` asked why the age requirement could not be resolved. The model
called the summary tool but did not make the required criterion-evidence lookup;
the server rejected its selection with `invalid_citations`. The answer fell back
to the restricted evidence-only interface. This counts as failure, even though
the application prevented an unvalidated answer.

The [retest protocol](retest-protocol.json) and [prompt patch](rejected-v4.patch)
record the attempted clarification. The retest still failed `fresh-11`, also
failed the evidence lookup on `fresh-02`, and skipped the required initial summary
on `fresh-19`. v4 was reverted to the exact frozen v3 source hash. The planned
additional 22-case live run for v4 was canceled after this failed acceptance check;
no further paid calls were made. One run per version cannot establish a statistical
quality difference, but it did not justify accepting the change.

All criterion-status, evidence-binding, and no-record-mutation checks passed in
both runs. These checks do not establish clinical validity. Fault and permission
scenarios run separately in the offline suite. The earlier v3 **22/22** result is
retained as [public regression evidence](../live/README.md), not pooled with this
first-pass result or presented as unseen performance.

## Reproduce without spending money

From the repository root, with the Python environment installed:

```powershell
& .venv/Scripts/python.exe -m healthops.evaluation --dataset data/evaluation/fresh-v1.json --trace --output .local/evaluation-fresh
```

This tests the fixed screening expectations and the offline fallback; it does
not measure an LLM. The fresh fixture tests also run in CI. `--dataset` is a
local CLI option and cannot be combined with `--api-url`.

For an intentional paid rerun using the provider configured in Docker's `.env`:

```powershell
docker compose exec -T healthops python -m healthops.evaluation --mode live --dataset /app/data/evaluation/fresh-v1.json --limit 24 --trace --output /data/evaluations/fresh-rerun
```

This permits up to 96 model calls. Use a new output directory to keep prior
results; dashboard-only credentials do not transfer to the CLI process. Add a
dated matching `--pricing` JSON file to calculate estimated cost. Further runs on
these now-inspected cases are regression tests. The next quality improvement
should address tool sequencing and then be tested on new, independently authored
questions as well as these regressions.
