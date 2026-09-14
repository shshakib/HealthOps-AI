# Automated checks

GitHub Actions runs on pushes to `main`, version tags, pull requests, and manual dispatch.
The workflow has read-only repository permissions and actions pinned to commit SHAs.

The test job installs the pinned Python dependencies, runs Ruff and pytest, checks
frontend formatting, builds the dashboard, and runs six workflows in Chromium on Linux.
Browser checks use a fresh temporary SQLite ledger and a handcrafted FHIR boundary
stand-in in `scripts/dashboard_test_server.py`. The stand-in is not Synthea-generated
data and is never used by the normal application server. Provider settings do not
inherit credentials, and fake keys are exercised with evidence-only bypass.

These CI browser checks cover product workflows without Docker or billable APIs.
They complement the existing local HAPI integration and persistence scripts, which
still require the running Docker stack. They do not demonstrate live model quality.

The secret job verifies a pinned Gitleaks archive checksum and scans complete Git
history with redacted output. Avoid adding broad allowlists to suppress findings.

To run the same self-contained browser scenarios on Windows after building the frontend:

```powershell
$env:HEALTHOPS_UI_FIXTURES = '1'
cd frontend
npm run test:ui
Remove-Item Env:HEALTHOPS_UI_FIXTURES
```

Windows uses installed Edge; CI uses Playwright's Chromium. No test traces or
screenshots are uploaded automatically. Build outputs, local data, credentials,
databases, caches, and logs are excluded from version control.
