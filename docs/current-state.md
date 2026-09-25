# HealthOps checkpoint

## README and repository consistency review — September 24, 2026

The README now leads with the workflow without the repeated "Local portfolio
preview" label. It uses actual September 24 captures of the refreshed interface,
retains the verified full-demo release link, and distinguishes reviewer actions
from viewer access in the Mermaid diagram. Assessment storage and review history
are explicitly SQLite; patient records remain behind HAPI/PostgreSQL. Detailed
Python startup and API examples moved to the dashboard guide, and docs/README.md
provides a navigation index. Machine-specific patient counts and repeated scope
paragraphs were removed from the README.

The existing interface refresh is included with this documentation update so a
checkout matches the screenshots. Docker's build-context allowlist now includes
frontend/public for the bundled font license. The superseded short-video recorder
was removed; an unpublished older narration draft was preserved under the ignored
.local/superseded-docs directory. Evaluation evidence, data snapshots, lock files,
licenses, and historical release notes are retained intentionally.

Frontend formatting/build, all ten isolated browser tests, Python lint/format,
relative documentation links, and focused secret scans passed. No live reviews,
accounts, or provider settings were changed. The repository-tour video remains
local for review; only the full application walkthrough is featured in the README.

## Repository video and demo presentation — September 24, 2026

The README now keeps the two screenshots first, followed by one optional link to
the complete 13:01 application walkthrough. The short recording is no longer
featured. The long MP4 and SRT were uploaded to the existing v0.2.0 GitHub release;
the historical short asset was retained. README, demo documentation, and the
recording helpers were committed and pushed as `e20a0d2`. Earlier interface changes
remain local and were not included in that focused commit.

Video two is a captioned repository tour based on actual public GitHub captures
at commit `2af2535`, with diagrams connecting the folders to the screening flow.
It covers the frontend, backend, AI tools, data formats, runtime storage, docs,
evaluation, tests, helper scripts, Docker, and CI. The 10:18 silent export, SRT,
script, and chapter navigation are in `.local/video-two/export/`, pending review.
See [repository recording notes](demo/video-two.md). Neither video changes live
application data or makes provider calls.

Full decoding passed for the 617.9-second MP4 (5,701,901 bytes), all 54 subtitle cues
are continuous, and browser playback and chapter seeking were verified. The media
helpers passed Ruff checks and formatting, and Gitleaks found no secrets in the
scripts or demo docs. SHA-256:
`b37564c5bdf80cbaaccd3240a2e3e3954be6fc392ce76b25bef7def4127f0128`.
GitHub Actions run `36082125475` passed both jobs: Python/browser tests (including
offline evaluation and frontend build) and the full-history secret scan.

## Complete demo video — September 24, 2026

Video one is a local, silent 13:01 edited walkthrough with 77 caption passages,
current-flow diagrams, administrator settings, roles, trial-rule review, screening,
evidence-only assistance, and a saved human-review example. It uses actual browser
captures held for narration, not continuous cursor footage. All review actions were
simulated in a separate SQLite ledger. Five Synthea records were copied read-only
from HAPI; no live records, accounts, or model settings were changed.

The MP4, SRT, timed narration, chapter list, timeline, and checksum manifest are in
`.local/video-one/export/`. See [the recording notes](demo/video-one.md) and
[caption source](demo/video-one-storyboard.json). Full video decoding and subtitle
continuity/duration checks passed; the result is 1920 × 1080 H.264 with no audio.
The MP4 and SRT are now published as release assets. The repository tour and
publication status are covered in the newer checkpoint above.

## Interface refresh — September 23, 2026

The application now uses locally bundled IBM Plex Sans, an original H mark and
favicon, off-white surfaces, dark text, and restrained blue actions. Navigation,
workspace counts, patient lists, trial rules, findings, dialogs, login, and admin
settings share the new styles. Status colours retain explicit text labels.
The interface has larger supporting text, clearer form borders, and a keyboard
skip link that preserves assessment URLs. Screening and permission logic are unchanged.

All ten browser workflows passed after correcting an existing test timing race:
the provider-settings test now waits for its assessment before reading its URL.
Responsive checks cover 320, 390, 768, 1024, and 1440px widths. Desktop and mobile
screens were visually inspected; keyboard focus and saved assessment navigation
were checked. Frontend build, formatting, whitespace checks, and secret scan passed.
The font, favicon, and font license are served locally; Docker copies the public
assets into its build. See [design decisions and references](interface-design.md).

September 24 deployment verification: all four Docker services are healthy. The
live JavaScript, CSS, favicon, font, and font-license assets match the tested local
build. The workspace still has five Synthea patients, nine assessments, and three
registry studies. OpenAI / `gpt-5.4-mini` remains configured. An evidence-only
assistant request recorded an MLflow trace successfully; no paid model call was
made. These interface changes are local and have not been committed or pushed.

## Admin AI settings — September 22, 2026

Model configuration now lives in **Settings → AI configuration**, available only
to administrators from the account bar. The assessment assistant retains its
provider status, questions, cited answers, and evidence-only switch. Admins can
open settings from a fallback answer. Opening settings and returning preserves
the selected assessment, assistant question, and unfinished review draft.

The optional **Test saved connection** button reuses the bounded admin evaluation
endpoint with one fictional case and at most four model calls. It tests saved
settings only and does not create an assessment or human review. Cloud calls may
incur charges; saving settings still makes no provider call. Existing API role
checks remain in force. Dashboard settings still live in server memory; `.env`
supplies persistent defaults.

Verification: 26 authentication/evaluation Python tests and all ten browser
scenarios passed. Browser checks cover denied settings/evaluation API requests
for viewers and reviewers, key handling, returning to an unfinished review,
status refresh, and connection-test success/failure with simulated responses.
Desktop/mobile settings screenshots were inspected. No paid model calls were
made for this change. See [the assistant guide](assistant.md).

## Portfolio release checkpoint — September 21, 2026

v0.2.0 packages the local authenticated review workflow, monitoring, and evidence
assistant. A frozen first-pass live evaluation on 24 new questions and six new
handcrafted profiles passed **23/24**. A prompt-only experiment passed 21/24 and
was rejected; the app retains the original assistant v3. Both reports and protocols
are published in [the fresh evaluation](evaluation/fresh/README.md). All 48 traces
were retrieved; the two runs cost an estimated $0.047352. The cases were authored
with knowledge of the implementation, not independently blinded.

Verification: 144 Python tests passed; the restored v3 assistant/evaluator subset
also passed all 40 tests. Nine browser scenarios passed. A 1 minute 54 second
captioned recording exercises sign-in, evidence inspection, screening, safe
assistant behavior, a simulated review, and reopening history. It uses an isolated
fixture ledger and evidence-only mode. See [the demo and manual acceptance checklist](demo/walkthrough.md).
The rebuilt Docker stack is healthy and retains five Synthea patients, eight
assessments, and three registry studies. Provider configuration and MLflow capture
remain available. The publication export passed Gitleaks with no detected secrets.
Final human acceptance, actual registry rule approvals, and independent domain
validation remain open. Historical checkpoints below describe earlier states.

## Live model checkpoint — September 21, 2026

OpenAI `gpt-5.4-mini` is configured locally through the ignored `.env` file.
Assistant v3 clarifies findings summaries versus human-review next steps. The
original live smoke test passed 2/3; the same three cases now pass 3/3. One full
run passed 22/22 public synthetic regression cases, with zero fallback answers,
49 model calls, P95 component latency of 3.512 seconds, and estimated provider
cost of $0.020067. The retest plus full run cost an estimated $0.02295075.
All 22 traces were retrieved from MLflow storage. Reports preserve both the
original failure and the successful runs; see [live evaluation](evaluation/live/README.md).
The 59 relevant automated tests and all offline regression/fault/permission checks
passed. Docker serves the updated assistant, and live data remains five Synthea
patients, eight saved assessments, and three registry studies. These are public
regression results, not an unseen benchmark or clinical validation. Earlier
checkpoints below are historical.

## Latest checkpoint — September 21, 2026

Local MLflow monitoring and a versioned evaluation runner are implemented.
The public offline suite covers 22 answer cases, six simulated faults, and 15
API permission boundaries. CI requires this regression suite and trace capture.
See [evaluation](evaluation.md) and the [measured report](evaluation/report.md).
The optional Compose monitoring profile serves MLflow at `127.0.0.1:5000`;
HealthOps remains at `127.0.0.1:18000`. Traces exclude patient text and credentials.
An admin-only endpoint can run a bounded evaluation with the dashboard's selected
model. No model was configured for this checkpoint, so real-provider quality,
latency, and cost still require a live run. Earlier checkpoints below are historical.
Verification: 142 Python tests passed; all nine browser scenarios passed using
isolated fixtures. The offline report passed 22/22 answers, 6/6 simulated faults,
and 15/15 permission checks. Gitleaks found no secrets in the publication export.
The rebuilt Docker services are healthy. A dashboard API trace was retrieved from
the persisted MLflow database, and the live ledger still has five Synthea patients,
eight assessments, and three registry studies.

## Latest checkpoint — September 20, 2026

Local accounts and session authentication now protect the dashboard and API.
Viewer/Reviewer/Admin permissions are enforced on the server. Review events take
identity from the session; old ledger events are retained unchanged and shown as
legacy unverified labels. Admins manage accounts and AI settings. Session expiry,
logout, role/password changes, disable/re-enable, login throttling, and CSRF are
covered by automated checks. See [authentication](authentication.md) for setup.
Default Compose exposes only HealthOps; HAPI maintenance access is an explicit override.
The Docker rebuild and read-only login check retained five Synthea patients, eight
saved assessments, and three registry studies. The local administrator credential
is in an ignored `.local/` file; no credential is part of the repository.
All nine browser workflows passed, including the three authentication scenarios.
Existing test scripts now prompt for a signed-in account.

The earlier checkpoints below are historical. Statements about unauthenticated
HealthOps APIs or always-published HAPI ports no longer describe the current default.
MLflow, live-provider verification, enterprise SSO, and cloud deployment remain future work.

---


Last updated: 2026-09-14 (Toronto). Milestone 0 is complete. Docker infrastructure,
Synthea generation/import, patient retrieval, actual registry snapshots, and the
interpretation approval workflow are implemented. Drafts require actual human review.

## Latest work: provider and API-key settings

- Added native OpenAI Responses, Claude Messages, and Gemini generateContent adapters
  alongside Ollama and evidence-only mode. Tool results preserve provider call IDs and
  native state; existing read-only tools and evidence selection validation remain enforced.
- Dashboard Model connection settings supports provider/model IDs, password key entry,
  replacement, and removal. Keys live in backend memory and are never echoed. Blank
  key entry preserves the existing key. Settings alone make no provider call.
- Optional environment defaults are documented in `.env.example`; dashboard overrides
  expire on restart. Same-origin/localhost request guards protect configuration and
  cloud-backed questions. This is still a single-user local demo without authentication.
- Verification: 118 Python tests and all six headless Edge browser tests passed.
  Tests cover provider wire formats, response-state preservation, key redaction,
  cross-site denial, error sanitization, missing keys, switching/removal, and bypass.
  No real API keys or paid calls were used. Live account/model verification remains open.
- See [the assistant guide](assistant.md) for setup and storage details.
- Final Docker deployment is healthy. The live status endpoint lists all five
  providers and defaults to offline. Dashboard HTML/assets and evidence-only answers
  passed HTTP checks; existing FHIR patient and review persistence checks passed.

## Previously completed: evidence assistant and optional local agent

- Added an assistant panel to saved assessments for explanations, unresolved evidence,
  and human review next steps. Citations open the original finding and saved records.
- Evidence-only fallback works without a model. Optional Ollama integration uses
  bounded, read-only summary/evidence/workflow tools; only validated criterion
  selections are rendered using the original finding text. No review or approval writes.
- Added assistant status and per-screening assistant API endpoints, model bypass,
  local-only adapter configuration, malformed-response/outage fallback, and tool traces.
- Verification: 97 Python tests and all five headless Edge browser tests passed.
  Ruff lint/format passed. Desktop/mobile assistant screenshots were visually inspected.
  Provider HTTP tests use a local protocol stub; no real model inference was tested.
- No model has been selected or installed. Live model setup and quality evaluation
  remain open; do not claim this is a fully verified live LLM deployment. Main-workspace
  rule drafts still require actual human review. See [the assistant guide](assistant.md).
- Final Docker rebuild is healthy. Dashboard HTML/assets return HTTP 200. The live
  assistant returned three saved citations in evidence-only mode and left the complete
  assessment/review response unchanged. FHIR and review persistence checks passed.

## Previously completed: React coordinator dashboard

- Dashboard at `http://127.0.0.1:18000/`; Swagger remains at `/docs`.
- Searchable Synthea/fixture patients, health-record browsing, trial selection,
  criterion findings, source evidence, patient decisions, and paginated review history.
- Registry source and location snapshots, rule versions, draft revision, and explicit
  interpretation approval/rejection are available visually. API gates remain enforced.
- Saved assessment URLs reopen the original evidence and decision history. A stale
  review loads the newer decision without discarding the user's draft reason and
  requires another acknowledgement before resubmission.
- Vite/React frontend is built with a pinned Node image and served by FastAPI in the
  existing HealthOps container. The running stack still has three services.
- Python API tests: 73 passing; lint passed. All four headless Edge browser tests passed: patient review/history, interpretation gate/review, mobile layout, and concurrent-review draft preservation. Browser tests run against
  a separate `.local/dashboard-test-*.sqlite3` ledger on port 18080 and read HAPI.
  Main-workspace actual-study drafts remain pending; QA approvals are isolated.
- Desktop/mobile screenshots are retained in `.local/dashboard-desktop.png` and
  `.local/dashboard-mobile.png`. Browser traces on failure stay under frontend/test-results.

The final Docker rebuild is healthy. The dashboard HTML and both compiled assets return HTTP 200; stack connectivity and existing FHIR/review persistence checks passed after the rebuild.

See [the dashboard guide](dashboard.md) for the complete workflow and checks.

## Latest work: registry snapshots and interpretation review

- Saved NCT07247084, NCT06591286, and NCT06750497 with original API response bytes,
  SHA-256, source URL, retrieval time, and registry update/recruitment information.
  Files live in `data/clinicaltrials/` and are included in the Docker image.
- Registry lists/details/snapshots read offline. Explicit CLI import refreshes data;
  old snapshots remain available and duplicate responses reuse the same version.
- Partial age/condition rule proposals cite exact source material. Draft creation
  is separate from approval, and patient screening is separate from both.
- Rule approvals/rejections are immutable records in the existing SQLite volume.
  Hash and source-version gates reject unapproved, rejected, or stale interpretations.
- Mandatory full-eligibility manual review prevents any partial registry screening
  from returning all criteria met. Missing condition evidence never proves absence.
- All three actual-study drafts remain pending; no agent approval was submitted.
  See [the review guide](trials.md) for the concrete proposed rules and next actions.
- Verification: 71 tests passed; Ruff lint passed. Live checks served all three
  snapshots and sourced drafts, verified rule hashes, and confirmed HTTP 409 when
  each unapproved interpretation was used for screening. The existing FHIR patient
  and review persistence checks passed after the rebuilt container became healthy.

```powershell
& '.\.venv\Scripts\python.exe' -m healthops.trials list
docker compose up --build -d --wait --wait-timeout 600 healthops
& '.\.venv\Scripts\python.exe' scripts/check_trials.py
```

The last command prepares drafts and verifies the blocking gate without approving
anything. Its report is `.local/trials-verification.json`. Actual approval is still
an open milestone acceptance item. Reviewer labels remain unauthenticated demos.

## Previously completed: Synthea pipeline

- Official Synthea v4.0.0 with checksum validation and pinned Java image; temporary
  generator container, fixed seeds 42 and reference/end date 2026-09-01.
- Five patients, seven raw FHIR files, 3,613 resources across 20 resource types.
  Raw data and provenance are in `.local/synthea/`; HAPI persists the imported data
  in its PostgreSQL volume. Original files are preserved.
- Import validates file hashes, stable IDs, and references before writes. UUID and
  identifier references resolve to imported resources; stable transaction PUTs
  allow repeat imports without duplicate resources. Failure reports retain progress.
- API lists Synthea patients with `GET /api/v1/patients?source=hapi` and returns
  Patient/Condition/Observation evidence via `/api/v1/patients/{id}/record`.
- Screen with `source=hapi` and fictional trial `DEMO-SYNTHEA-T2D-001`. The original
  `source=fixtures` workflow remains the default. Human reviews retain HAPI snapshots.
- Verification: 39 tests passed; lint passed. Two independent generation runs
  produced seven identical files. Live repeat import preserved all 20 resource-type
  counts; API retrieval passed for all five patients (including pagination).
  A simulated review persisted after a HAPI-backed screening.
- `.local/synthea/verification.json` and `reproduction-check.json` retain evidence.
  See [the pipeline guide](synthea.md) for commands and limitations.

Generation has already run here; do not overwrite the generated directory. Resume:

```powershell
docker compose up --build -d --wait --wait-timeout 600
& '.\.venv\Scripts\python.exe' -m healthops.synthea import --dry-run
& '.\.venv\Scripts\python.exe' scripts/check_synthea.py
```

Resume verification on 2026-09-13 confirmed that the interrupted Docker setup
had completed: all three existing containers were healthy, all 26 tests passed,
Ruff lint/format and dependency checks passed, and the read-only connectivity and
persistence checks retrieved the saved FHIR patient, screening snapshot, and
human-review event. No container rebuild or data reset was needed.

## Completed: milestone 0

- FastAPI local service with three handcrafted synthetic patient bundles and one
  fictional trial. No clinical or real-trial claims are made for these fixtures.
- Deterministic screening with evidence references and `met`/`not_met`/`unknown`.
- Persisted source snapshots, rules/evidence hashes, and a local SQLite review ledger.
- Explicit review submission, rationale, version conflict handling, and retained history.
- Python 3.11 virtual environment, installed dependencies, and pip constraints snapshot.
- Repeatable HTTP smoke demonstration in `scripts/demo.py`.
- Project brief, milestone acceptance criteria, and setup instructions.

Original milestone verification: 26 tests passed; Ruff lint/format passed. Live HTTP checks inside the
HealthOps container verified HAPI FHIR R4 connectivity, patient-count search, three
screening outcomes, a simulated review, and stale revision rejection. Tests emit
two dependency deprecation warnings (Starlette's
HTTPX compatibility and AnyIO portal alias); they do not fail the checks. Revisit
these dependencies when updating the test environment.

## Docker infrastructure

- `compose.yaml` starts HealthOps, HAPI FHIR, and PostgreSQL, in health-check order.
- Python, HAPI, and PostgreSQL images are pinned to resolved digests. The observed
  HAPI runtime is 8.12.0 and exposes FHIR R4 (4.0.1).
- HealthOps runs as a non-root container user. Its SQLite ledger uses the
  `healthops_reviews` volume; HAPI's PostgreSQL uses `fhir_postgres`.
- HealthOps is published at `http://127.0.0.1:18000/docs` and HAPI metadata at
  `http://127.0.0.1:8080/fhir/metadata`. PostgreSQL has no host port.
- The original Python API on port 8000 and its `.local/` database remain separate.
- The container's `FHIR_BASE_URL` points to `http://hapi:8080/fhir`. It is tested by
  the connectivity script and the HAPI patient-data adapter.
- A labeled synthetic FHIR patient and simulated review were created to test
  persistence. Both were retrieved successfully after `docker compose down`
  followed by rebuilding/recreating all three containers with the same volumes.
- Final status: all three services healthy. Host HTTP checks passed on ports
  18000 and 8080. The post-recreation connectivity and review smoke checks passed.
  HAPI now contains five imported Synthea patients plus the earlier labeled
  infrastructure-test patient. The latter is excluded from the Synthea API list.

## Resume with Docker

```powershell
docker compose up --build -d --wait --wait-timeout 600
docker compose ps
docker compose exec -T healthops python scripts/check_stack.py
docker compose exec -T healthops python scripts/demo.py
```

For the persistence check, see [the Docker guide](docker.md). Normal `docker compose
down` preserves both volumes; `down --volumes` erases them. A generated persistence
test state file lives in the review volume and is used by:

```powershell
docker compose exec -T healthops python scripts/check_persistence.py verify
```

Use the dashboard or `/docs` to submit your own review. Reviewer names are self-reported demo labels;
authentication and authorization are not implemented. Compose publishes both HTTP
ports only on loopback. Direct Python development remains available via the README.

## Next: milestone 1

1. Human review of the concrete, partial actual-study interpretations in the trial guide.
2. Broaden supported criteria only where source semantics and patient evidence are clear.
3. Select and verify a real local model or a cloud provider/model with your own API key.
4. Add authenticated access, persisted tracing, and measured model-quality evaluation.

Docker Desktop's Linux engine is available and the local stack has been built.
No cloud resources or paid model API calls were created. Git is now initialized
for the v0.1.0 local-prototype checkpoint. Publication preparation adds the MIT
license, third-party notices, pinned GitHub Actions, and a staged-file secret scan.
See [release notes](releases/v0.1.0.md) and [automated checks](ci.md).

Live LLM verification, MLflow, real authentication, and Azure remain later work.
This checkpoint is a verified starter, not the completed portfolio application.
