# HealthOps dashboard

Sign in first using the [login guide](authentication.md). Viewer accounts are read-only;
Reviewer and Admin accounts can record screening and interpretation decisions.

Open [the dashboard](http://127.0.0.1:18000/). The React interface is served by
HealthOps, so the local stack still needs only three running containers. Node
is used during the image build; it is not a fourth application service.

## What you can do

- **Patient screening:** search Synthea patients, inspect diagnoses and observations,
  choose a study or fictional exercise, and set the assessment date.
- **Evidence review:** expand each criterion, inspect cited patient resources and
  trial text, and see met, not-met, and unknown findings.
- **Patient decisions:** request information, advance for further screening, or
  dismiss a match. A signed-in Reviewer/Admin account, reason, and acknowledgement are required.
- **Trial rules:** inspect full registry eligibility text, dated recruitment and
  location information, draft mappings, and previous interpretation versions.
  Prepare or revise a draft, then explicitly approve or reject it.
- **Review history:** browse paginated saved assessments, reopen their immutable
  evidence, and see every recorded decision. Saved assessment URLs survive refresh.

The interface honors the API's approval gate. Registry screening needs an approved
interpretation for the current snapshot; unsupported criteria stay manual. A stale
patient-review submission loads the newer decision, preserves the user's draft,
and requires renewed acknowledgement before another submission.

The three existing actual-study drafts in the main workspace remain pending human
review. UI testing uses a separate ledger, not your main decisions. The dashboard
includes an [evidence assistant](assistant.md) with Ollama, OpenAI, Claude, and Gemini adapters
and explicit offline fallback. It uses authenticated reviewer accounts but does not contact patients,
or enroll anyone.

## Try a complete workflow

1. In **Patient screening**, choose **Handcrafted demo fixtures** under Patient data.
2. Select `Synthetic demo-001` and run the fictional screening exercise.
3. Expand a finding and open its supporting evidence.
   Use **Ask about this assessment** to explain the result or show missing evidence.
   Administrators use **Settings → AI configuration** in the top account bar to
   choose a provider/model and enter a cloud API key. Configuration is separate
   from the assessment. **Back to workspace** preserves unfinished review text.
   Keys entered here stay in server memory for the current session; saving does not call a model.
4. Choose a next step, enter a reason under your signed-in identity, acknowledge the evidence,
   and save your review.
5. Open **Review history** and reopen that assessment.

Use Synthea records for the imported-data workflow. Actual registry trials become
available for screening only after someone reviews their partial rule interpretation
in **Trial rules**. The [trial guide](trials.md) describes those limits.

## Start and develop

```powershell
docker compose up --build -d --wait --wait-timeout 600
```

Open port **18000** for the dashboard; `/docs` still opens Swagger. Do not use the
older Python server on port 8000 to check a newly built Docker dashboard.

For frontend development, keep the Docker API running and start Vite:

```powershell
cd frontend
npm ci --ignore-scripts --no-audit --no-fund
npm run dev
```

Open the local URL Vite prints. Vite proxies `/api` and `/health` to port 18000.
If that API port changes, update `frontend/vite.config.js` accordingly.

`npm run build` writes assets into `src/healthops/static/`, which is excluded from
Git. Python's package configuration includes these assets when built. Docker uses
a pinned Node image to build them from source, then copies them into the Python
image. UI assets are served locally with no runtime CDN dependency.

## Checks

```powershell
& '.\.venv\Scripts\python.exe' -m pytest -q
& '.\.venv\Scripts\python.exe' -m ruff check .
cd frontend
npm run format:check
npm run build
npm run test:ui
```

Browser tests use headless Microsoft Edge on Windows and require the Python venv,
the generated frontend build, imported Synthea records, and HAPI on port 8080.
They start a temporary API on port **18080** with a fresh SQLite ledger under
`.local/dashboard-test-*.sqlite3`. Synthetic test reviews and simulated rule
approvals only affect that ledger. The test server stops when the suite finishes;
the database remains available for inspection. Generated screenshots and traces
are local artifacts, not committed patient information.

GitHub Actions uses Chromium and an isolated handcrafted FHIR stand-in so it does
not need the Docker stack. See [automated checks](ci.md) for this separate CI mode.
