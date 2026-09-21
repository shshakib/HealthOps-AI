# Two-minute HealthOps walkthrough

[Watch/download the recorded walkthrough](https://github.com/shshakib/healthops-ai/releases/download/v0.2.0/healthops-demo.webm).
The recording shows the actual interface with a persistent **automated demo,
synthetic data, simulated review** banner. It uses an isolated test ledger and
public test accounts, not the real administrator account or live review history.
No patient is contacted or enrolled. There is no voiceover; the video has captions.
Duration: **1 minute 54 seconds**, 1440 × 1000. The recording's HAPI/Synthea counter
uses the test server's three-record stand-in; it does not demonstrate ingestion.
The selected patient is explicitly labeled a handcrafted fixture in the interface.

Video SHA-256: `98031b52292de481767dea04192105c50a83b90fe30bc2379e05b42a98458a06`.

| Approximate time | Show | Explain |
|---|---|---|
| 0:00 | Reviewer sign-in | Server-enforced permissions control access and actions. |
| 0:10 | Patient and exercise | Select a handcrafted synthetic patient and fictional rules. |
| 0:22 | Health records | Inspect the source condition and laboratory records. |
| 0:34 | Saved screening | Supported rules produce met, not met, or unknown, with evidence. |
| 0:47 | Evidence dialog | An old laboratory result stays unknown rather than becoming a match. |
| 1:00 | Assistant | Ask what is missing. This recording uses evidence-only mode. |
| 1:12 | Unsupported request | The assistant cannot enroll the patient or submit a review. |
| 1:21 | Simulated decision | Demonstrate requesting information with an explicit reason. |
| 1:34 | History | Reopen the saved assessment and attributable review event. |

The real-model evidence is separate: [22-case regression](../evaluation/live/README.md)
and [fresh first-pass evaluation with preserved failures](../evaluation/fresh/README.md).
The recording does not claim to show a live LLM call. HAPI/PostgreSQL ingestion and
actual registry rule approval have separate automated checks; this short recording
focuses on the reviewer's patient-screening workflow.

## Recreate the recording

Build the dashboard with `npm run build` from `frontend`. Then from the repo root,
start a separate fixture server (never point the recording at the normal app):

```powershell
$env:HEALTHOPS_UI_FIXTURES='1'
& .venv/Scripts/python.exe -m uvicorn scripts.dashboard_test_server:create_app --factory --host 127.0.0.1 --port 18081
```

In a second terminal, from `frontend`, with Microsoft Edge installed:

```powershell
npm exec playwright install ffmpeg
node demo/record.mjs
```

Output is `.local/demo/healthops-demo.webm`; the screenshot is
`docs/images/review-workbench-v0.2.png`. The recorder uses only port 18081, creates
a clearly labeled simulated review, and checks that history can reopen it.
The fixture server creates a new isolated SQLite ledger on each launch and
explicitly excludes real provider credentials. Stop that server afterward.

## Your final manual acceptance check

On [your local dashboard](http://127.0.0.1:18000/), sign in with your own account:

1. Choose a synthetic patient and the matching fictional exercise. Run screening.
2. Open a finding and verify that you can understand its evidence and any unknown.
3. Ask the assistant to explain it. Inspect the citations and mode label; a model
   answer may fall back, as documented in the fresh evaluation.
4. Decide whether to request information, advance for further screening, or dismiss.
   Record **your own** reason only if you are ready to make that demo judgment.
5. Open review history and confirm that the evidence, identity, and reason remain.

This is product acceptance, not clinical validation. Actual registry interpretations
still need a person qualified to review their accuracy; automated tests and the
recorded simulation do not approve them in the live ledger.
