# Registry snapshots and human-reviewed interpretations

The app now has three actual ClinicalTrials.gov study records alongside the two
fictional trial exercises. All patients remain synthetic. Browse
[the registry study list](http://127.0.0.1:18000/api/v1/trials?source=registry).

## What is implemented

- Public API import by explicit NCT identifier; no patient information is sent to
  the registry. Reads use saved local files and work without registry access.
- Original response bytes, SHA-256, retrieval time, source/API URLs, and registry
  last-update date. Listings label recruitment status as **at the snapshot**, with
  snapshot age; site locations are also explicitly snapshot data.
- Partial, versioned interpretations with exact source quotations. Drafts propose
  whole-year age bounds and two narrowly scoped, curated T2D code mappings.
- Separate interpretation approval/rejection and patient-screening review. Both
  record rationale and a self-reported reviewer label in the local SQLite ledger.
- Screening requires an approved rule set for the exact currently selected study
  snapshot. Changed registry data needs a new interpretation and review. Saved
  patient screenings retain their original registry, rules, approval, and evidence.

## Review these three drafts

| Study | Proposed automation | Still requires manual assessment |
|---|---|---|
| [NCT07247084](https://clinicaltrials.gov/study/NCT07247084) | Age 18+; documented active T2D is an **exclusion component** | Other diabetes types, BMI, waist ratio, weight history, comorbidities, and full eligibility |
| [NCT06591286](https://clinicaltrials.gov/study/NCT06591286) | Age 18–80; documented active T2D is an **inclusion component** | Hospital admission, insulin, HbA1c timing/range, monitoring history, consent, and all exclusions |
| [NCT06750497](https://clinicaltrials.gov/study/NCT06750497) | Age 18–80 | Healthy vs T2D cohort assignment, medications, BMI wording, consent timing, and all other criteria |

The drafts are **pending human review**. No actual-study interpretation was
approved automatically. Automated approval-path checks use isolated test databases
and clearly fictional study fixtures; they do not constitute human review.

The source BMI expression in NCT06750497 appears ambiguous. We preserve it and leave
it manual. FHIR administrative gender is not used to infer registry sex eligibility.
We also do not invent an HbA1c recency window when a criterion is unclear or omit
the admission/treatment context of a compound requirement.

## Review and activate a partial interpretation

Open [Swagger](http://127.0.0.1:18000/docs):

1. Read `GET /api/v1/trials/{trial_id}` for complete eligibility text, source links,
   snapshot dates, and existing rule sets. The `/snapshot` endpoint exposes the
   original registry JSON with metadata; optional `snapshot_id` retrieves an older version.
2. Use `POST /api/v1/trials/{trial_id}/rule-sets/draft` if no draft exists. It proposes
   supported components and leaves them pending. Repeating it returns the same
   interpretation rather than duplicating or resetting its review.
3. Inspect each rule's quotation, direction, field/code mapping, and partial scope.
   To correct a draft, submit a sourced `RuleProposal` to
   `POST /api/v1/trials/{trial_id}/rule-sets`. Changed content creates a new hash/version.
4. A person records a review using `POST /api/v1/rule-sets/{rule_set_id}/reviews`:

```json
{
  "reviewer": "YOUR REVIEWER LABEL",
  "decision": "approve",
  "reason": "EXPLAIN YOUR REVIEW OF THE SOURCE AND PARTIAL INTERPRETATION",
  "expected_rules_hash": "COPY THE DRAFT'S RULES_HASH"
}
```

Use `reject` when the proposal is incorrect. Approval means acceptance of a limited
demo interpretation, not clinical validation. An interpretation can be reviewed
once; changing it requires a new version. Revocation and authenticated reviewers
are future work. Do not activate these demo rules for real patients.

5. After approval, submit a screening with an explicit assessment date:

```json
{
  "source": "hapi",
  "patient_id": "COPY A SYNTHEA PATIENT ID",
  "trial_id": "NCT06591286",
  "rule_set_id": "COPY THE APPROVED RULE SET ID",
  "as_of": "2026-09-01"
}
```

This is a retrospective synthetic patient assessment using a saved registry
snapshot; it does not imply the snapshot describes recruitment on the patient
assessment date. Each finding preserves both patient evidence and registry text.
The existing screening review endpoint then records the human's next step.

## Conservative interpretation limits

- An inclusion predicate that is established yields `met`. An established
  exclusion predicate yields `not_met`.
- No matching condition is **unknown**, including for exclusions: missing records
  do not prove absence. Conditions must be linked to the patient and carry an exact
  supported SNOMED code, valid clinical/verification status systems, active/confirmed
  status, a recorded date no later than assessment, and no contradictory abatement.
- Age boundaries are inclusive; incomplete birth dates and unsupported age units
  remain unknown/manual. No terminology expansion is implemented.
- A mandatory `full_eligibility_review: unknown` finding always carries the full
  original eligibility text. Partial automation can never return an all-criteria-met
  result. Rules with a failed component report `criteria_not_met`; other results
  remain `insufficient_evidence`. These are component comparisons, not enrollment decisions.
- Quote validation establishes provenance, not semantic correctness. That is why
  interpretation review is required independently of the patient's review.

## Import, refresh, and verify

The curated snapshots are included in `data/clinicaltrials/` and copied into the
Docker image at build time. They are separate from Synthea's generated patient data.

```powershell
& '.\.venv\Scripts\python.exe' -m healthops.trials list
& '.\.venv\Scripts\python.exe' -m healthops.trials import
docker compose up --build -d --wait --wait-timeout 600 healthops
& '.\.venv\Scripts\python.exe' scripts/check_trials.py
```

Use `--ids NCT06591286` to refresh one study. Same-byte responses reuse the immutable
snapshot and its original retrieval time. Changed bytes create a new version;
old versions and past decisions remain available. Registry unavailable? Keep
using saved snapshots; failed imports do not advance the local latest pointer.

The live check saves draft interpretations but **never approves them**. It verifies
source attribution, rule hashes, and the unapproved-screening gate, and saves its
results to `.local/trials-verification.json`. Approvals and reviews persist in the
HealthOps Docker review volume. Rebuilding the image does not reset that ledger.
