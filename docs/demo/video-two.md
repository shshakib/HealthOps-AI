# Repository walkthrough — video two

A silent **10:18** tour of the published HealthOps repository, with natural-language
captions and a separate narration script for a later voice-over.

The video explains the main folders through one practical example: a coordinator
submits a screening request, the API reads records and applies defined rules, and
the application saves evidence for human review. It then covers the optional AI
tools, trial snapshots, runtime storage, documentation, evaluation reports, tests,
local helpers, Docker, dependencies, and GitHub Actions.

The footage uses actual public GitHub browser captures, with explanatory diagrams
and deliberate holds for narration. It is an edited walkthrough, not continuous
cursor recording. Captures show the published repository at commit `2af2535`;
later interface and media-production changes are not presented as already published.
The tour identifies Azure, Databricks, and Snowflake as future extensions.

## Files and preview

The export is local for review and has not been uploaded:

- `.local/video-two/export/healthops-repository-tour.mp4`: 1920 × 1080 H.264,
  15 fps, burned-in captions, no audio.
- `.local/video-two/export/healthops-repository-tour.srt`: editable timed subtitles.
- `.local/video-two/export/voiceover-script.md`: narration for recording your voice.
- `.local/video-two/export/chapters.txt`: section timestamps.
- `.local/video-two/export/timeline.json`: caption and source-image timings.
- `.local/video-two/export/manifest.json`: provenance, duration, and checksum.
- `.local/video-two/export/index.html`: local player with chapter navigation.

The [storyboard](video-two-storyboard.json) and [timed narration](video-two-narration.md)
are the editable text sources. No credentials, local database contents, private
files, or live patient records are shown. No application actions or model calls
were performed to make this tour.

## Rebuild from the local captures

Use the same local media dependencies as video one: Pillow and imageio-ffmpeg.
The actual browser captures are under `.local/video-two/captures/`, ignored by Git.
A clean checkout does not contain those media inputs; it needs a new capture pass.

```powershell
& .venv/Scripts/python.exe scripts/render_demo_video.py --video two
& .venv/Scripts/python.exe scripts/serve_demo_video.py --video two
```

The preview opens at `http://127.0.0.1:18083/`; the server binds only to loopback.
The MP4 also plays independently in a normal video player. Captions are visible
in the video; use the SRT and script to plan a later voice-over edit.
