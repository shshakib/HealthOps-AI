# HealthOps AI milestones

Each milestone should produce a runnable, reviewable result. The list describes
planned work; completion requires the acceptance evidence described below.

## 0 — Local screening and human review

Status: completed and locally verified on 2026-09-13. See
[the checkpoint](current-state.md) for evidence and remaining limitations.

Build the FastAPI skeleton, handcrafted synthetic FHIR fixtures, a fictional trial,
deterministic screening rules, and a persisted review history.

Done when:

- A fresh local setup can start the API using documented commands.
- Screening returns `met`, `not_met`, and `unknown` findings with source evidence
  and rule/evidence version attribution.
- Meaningful tests exercise missing/stale evidence and an out-of-range criterion.
- Human reviews preserve rationale, reviewer identifier, timestamp, and the exact
  screening result reviewed; previous reviews remain available.
- Fixtures and any unverified reviewer identities are visibly labeled as demos.

## 1 — Reproducible healthcare and trial data

Infrastructure portion implemented and verified: Compose for HealthOps, HAPI FHIR,
and PostgreSQL with persistent volumes. FHIR records and reviews survived a full
container recreation test. Synthea generation/import and the HealthOps patient
adapter are now implemented and verified: five patients, repeat imports without
duplicates, reproducible raw files, and a HAPI-backed human-review flow. See
[the pipeline guide](synthea.md). Three real registry snapshots and the versioned
interpretation approval workflow are now implemented. Drafts remain pending actual
human review; approval-path tests use isolated fictional fixtures. Thus the human
approval acceptance criterion is still open. See [the trial guide](trials.md).

Add Synthea-generated FHIR R4 data, HAPI FHIR, and a small curated collection of
real ClinicalTrials.gov snapshots. Add the planned PostgreSQL and Docker setup.

Done when:

- A documented seed command reproduces the demonstration dataset.
- Importing the same input twice does not duplicate records.
- Invalid or unsupported input is reported, with malformed records quarantined.
- Trial records retain study identifiers, source links, retrieval dates, and raw
  snapshots; the demo remains usable without live API access.
- A reviewer approves the supported structured interpretation of each trial's
  criteria; unsupported criteria stay visible for manual review.
- Inclusion and exclusion directions are explicit, with tests for exclusion
  violations and for insufficient evidence to establish an exclusion's absence.
- Snapshot recruitment information is displayed with its age and does not imply
  that a particular site currently accepts participants.

## 2 — Coordinator review screen and AI assistance

The React coordinator dashboard is implemented: patient/record selection, trial
source and interpretation review, screening evidence, decisions, and saved history.
The evidence assistant and LLM-unavailable fallback are implemented. An optional
Ollama/OpenAI/Claude/Gemini agent selects evidence through bounded read-only tools;
provider/model/key settings are available in the dashboard. Answers use the
saved findings. Backend, provider-protocol stub, and browser tests pass. A real
model still needs selection and live verification before this milestone is complete.
See [the dashboard guide](dashboard.md) and [assistant guide](assistant.md).

Add React screens for patient/trial selection, criterion evidence, review decisions,
and review history. Add one LLM integration for explanations and controlled tools.

Done when:

- A coordinator can complete the review workflow from the browser.
- Evidence links and unknown findings are inspectable before a decision.
- AI explanations reference the same evidence used by the screening engine.
- The workflow remains usable when the LLM is unavailable.
- An incorrect interpretation can be corrected through a versioned approval flow;
  the updated result does not rewrite prior decisions.

## 3 — Access control and measured quality

Local accounts, server-enforced roles, user management, session revocation, and
authenticated reviewer attribution are implemented. See [authentication](authentication.md).
Local MLflow tracing and a versioned public regression report are implemented. See
[evaluation](evaluation.md) for measured offline results and reproduction commands.
Real-model verification, an independent held-out benchmark, and a recorded demo
remain open; this milestone is not yet fully complete.

Add authenticated identities, server-enforced permissions, MLflow tracing,
evaluation fixtures, error handling, and GitHub Actions checks.

Done when:

- Distinct authenticated identities demonstrate allowed and denied requests,
  including direct API calls; authentication supplies the reviewer identity.
- A reserved evaluation set checks criterion correctness, unknown handling,
  evidence citations, and unauthorized disclosure attempts.
- Evaluation reports give actual counts, dataset versions, and limitations;
  latency and cost are measured when live AI is used.
- CI runs the relevant deterministic tests and available evaluation checks.
- Setup instructions, an architecture diagram, and a short recorded demo match
  the implemented system.

## 4 — Temporary Azure/Databricks deployment

Deploy one genuine cloud path: synthetic FHIR through Azure Health Data Services
and ADLS into Databricks Delta tables using Lakeflow, with Unity Catalog and Entra
access controls. Represent deployed infrastructure in Terraform.

Done when:

- Deployment and teardown instructions are tested and include billable resources.
- A pipeline demonstrates repeatable ingestion and data-quality quarantine.
- Two authenticated identities demonstrate enforced access boundaries.
- Saved execution evidence supports the portfolio's deployment claims.
- The lightweight public showcase and local demonstration remain available after
  the full cloud environment is removed.

Snowflake sharing, MCP exposure, care-gap detection, and additional clinical
domains remain optional future work rather than prerequisites for completion.
