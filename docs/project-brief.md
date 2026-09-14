# HealthOps AI project brief

## Purpose

Build a clinical-trial prescreening workbench that helps a research coordinator
review possible patient–trial matches. It compares patient evidence with supported
trial criteria, explains the result, and records a human review decision.

All patient records are synthetic. Results support further screening; they do not
establish clinical eligibility, recommend treatment, contact patients, or enroll
anyone in a study.

## First user workflow

1. Select a synthetic patient and a demonstration trial.
2. Evaluate a small, explicitly supported set of structured criteria.
3. Inspect each finding, its evidence, and the evidence and rule versions.
4. Record a review decision and rationale: advance for further screening, dismiss,
   or request more information.
5. Inspect the decision history without replacing earlier review records.

Criterion findings use `met`, `not_met`, or `unknown`. `met` means that a supported
criterion is satisfied as written. Missing, stale, or insufficient evidence
produces `unknown`, rather than proof of absence. Exclusion-rule interpretation
will be added and tested when importing actual trial criteria in milestone 1.
The interface must preserve the individual findings even when showing a summary.

## Initial scope and data

The first slice is a self-contained local API, deterministic screening engine,
and review audit trail. It uses handcrafted, minimal synthetic FHIR bundles and
an explicitly fictional trial. These fixtures test the software workflow; they
are not Synthea exports, live EHR records, or actual recruiting studies.

Docker Compose now supplies HealthOps, HAPI FHIR, and PostgreSQL, plus an on-demand
Synthea generator. Generation/import and the HealthOps patient-data adapter are
implemented, with a HAPI-backed fictional screening and human-review flow.
Three dated ClinicalTrials.gov snapshots and a separate interpretation-approval
workflow are also implemented; actual drafts await human review. Later milestones
add authenticated access and live model evaluation. The React review dashboard is now
implemented for patients, trial interpretations, evidence, decisions, and history.
An evidence assistant is implemented with Ollama/OpenAI/Claude/Gemini tool adapters and
offline fallback. Live model selection/verification remain open; see [the guide](assistant.md).
Unsupported trial criteria remain visible as unknown or requiring manual review.
AI-generated rule interpretations require human approval before activation.

## Acceptance criteria for the initial slice

- A documented local command starts the API and serves a health endpoint.
- A reviewer can evaluate at least one fictional trial against multiple synthetic
  patients with deliberately different screening outcomes.
- Every finding identifies its criterion, status, explanation, and available
  source evidence; screening output identifies the rules and evidence versions.
- Tests cover missing evidence, stale observations, and an out-of-range criterion.
- A candidate can only receive a recorded review decision through an explicit
  review action that includes a reviewer identifier and a nonempty rationale.
- Each saved review identifies its screening result, evidence version, rule
  version, decision, reviewer, and timestamp.
- Advancing means further human screening; no enrollment action is implemented.
- Local demonstration reviewer identifiers are labeled as unverified until real
  authentication is implemented. They do not demonstrate authorization.

## Technical direction

| Layer | Planned technology |
| --- | --- |
| API and screening | Python, FastAPI, SQL |
| Persistent application data | PostgreSQL |
| Review interface | React |
| Synthetic data and healthcare API | Synthea, HAPI FHIR |
| Trial metadata | ClinicalTrials.gov API and dated snapshots |
| AI assistance | One LLM integration with controlled tools |
| Evaluation and tracing | pytest, MLflow |
| Local delivery and checks | Docker, GitHub Actions |

The initial scaffold can use simpler local storage while the PostgreSQL integration
is pending. Planned technologies must not be described as implemented until tested.

Azure is a later deployment milestone: Azure Health Data Services, ADLS,
Databricks, Delta Lake, Lakeflow, Unity Catalog, Entra ID, and Terraform.
MCP and Snowflake are deferred. Keep the local demonstration usable independently
of the cloud deployment, and tear down billable cloud resources after experiments.

## Evidence and portfolio claims

This is a simulated customer engagement. No stakeholder interviews, clinical
validation, compliance certification, accuracy results, or screening-time savings
are claimed. Publish measured software results with test counts, dataset versions,
and limitations. Synthetic benchmarks establish software behavior rather than
effectiveness in clinical practice.
