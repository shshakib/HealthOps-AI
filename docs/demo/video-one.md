# Complete application walkthrough — video one

The video is a silent **13:01** walkthrough with readable captions, ready for
a later voice-over. It starts with the current application architecture and then
shows login, account management, model settings, viewer permissions, patient
records, trial-rule review, screening, the evidence assistant, human review, and
the saved assessment history. It ends with a brief view of the API documentation.

This is an **edited screen walkthrough**, assembled from real browser captures
held on screen for narration, rather than a continuous cursor recording. No UI
results were fabricated or overlaid. The diagrams describe the current local
application; the proposed Databricks/Snowflake extension is not shown as deployed.

## Local deliverables

The media is in the ignored `.local/video-one/export/` directory:

- `healthops-full-demo.mp4`: 1920 × 1080 H.264, 15 fps, visible captions, no audio.
- `healthops-full-demo.srt`: matching editable subtitles.
- `voiceover-script.md`: the timed narration, in plain language.
- `chapters.txt`: navigation timestamps.
- `timeline.json`: exact caption timing and source-image mapping.
- `manifest.json`: export properties, provenance, and SHA-256 checksum.
- `index.html`: local player with chapter navigation and download links.

The editable [storyboard](video-one-storyboard.json) and
[timed narration](video-one-narration.md) live in this folder.
[Watch or download the MP4](https://github.com/shshakib/HealthOps-AI/releases/download/v0.2.0/healthops-full-demo.mp4)
and [download the subtitles](https://github.com/shshakib/HealthOps-AI/releases/download/v0.2.0/healthops-full-demo.srt)
from the v0.2.0 release assets. This replaces the short recording as the featured
README walkthrough; the screenshots remain the first interface preview.

## What was demonstrated

- Signed in with disposable administrator, viewer, and reviewer accounts.
- Inspected user creation, role controls, active status, password controls, and
  account events. Account creation and password reset forms were shown without
  submitting them.
- Selected the supported providers and saved evidence-only mode. Provider keys
  remained empty; no live model request or connection test was performed.
- Verified that the viewer lacks administration controls and cannot run screening.
- Searched copied Synthea records and opened their health-record evidence.
- Prepared and approved a partial registry interpretation in an isolated ledger,
  with an explicit simulated-demo reason, then screened a copied Synthea patient.
- Screened all three handcrafted examples to show met, not-met, and unknown results.
- Used the evidence-only assistant, followed its citation, inspected the workflow
  explanation, and demonstrated its refusal to enroll a patient.
- Saved a simulated request for more information and reopened it through history.

The Synthea records were exported read-only from the existing HAPI server. The
recording server serves those copies and uses a separate SQLite database. It does
not load the real administrator credentials or provider keys. The recording does
not demonstrate a fresh Synthea generation/import, clinical validation, or a live
LLM answer. The latter's architecture is explained separately and labelled optional.

## Rebuild the edit

`scripts/demo_video_server.py` creates the isolated recording app, using
`.local/video-one/synthea-snapshot.json` as its read-only FHIR boundary. Bind it
only to loopback; the demonstration accounts are deliberately disposable.

The captures under `.local/video-one/captures/` came from actual browser
interactions. To rebuild the edit from those captures on Windows, install Pillow
and imageio-ffmpeg into a local Python environment, then run:

```powershell
& .venv/Scripts/python.exe scripts/render_demo_video.py
```

These are media-production dependencies, not application dependencies. The renderer
reads the storyboard, draws the diagrams, lays out captions, writes the SRT and
narration, and encodes an MP4 with chapter metadata. It does not read `.env` or any
credential note. The captures are local inputs and are not included in the repository.

To reopen the local player, run `scripts/serve_demo_video.py` using the same Python
environment, then open `http://127.0.0.1:18082/`. This loopback-only server serves
the export folder and supports byte-range requests for chapter seeking. The MP4
also plays independently in a normal video player.

For a voice-over, record one section at a time using the timed script. Add that
audio to the silent video in an editor, adjusting holds and subtitle timing as
needed. The [repository walkthrough](video-two.md) is a separate video.
