"""Assemble the captioned, edited walkthrough from actual UI captures.

Local media dependencies: Pillow and imageio-ffmpeg (not app dependencies).
The capture directory is intentionally ignored by Git. No app secrets are read.
Storyboards and narration stay in .local/video-{one,two}/production/.
"""

import argparse
import hashlib
import json
import math
import subprocess
from pathlib import Path

import imageio_ffmpeg
from PIL import Image, ImageDraw, ImageFont, ImageOps

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / ".local/video-one"
OUT = WORK / "export"
FRAMES = WORK / "frames"
PRODUCTION = WORK / "production"
STORY = []
VIDEO = "one"
STEM = "healthops-full-demo"
TITLE = "Complete application walkthrough"
TAG = "SYNTHETIC DATA  ·  DEMO WORKSPACE"
COMMENT = (
    "Edited real-interface captures; synthetic data; simulated reviews; evidence-only assistant."
)
W, H, CONTENT_H = 1920, 1080, 936
INK, BLUE, MUTED, BG = "#202833", "#245f93", "#586572", "#f4f4f1"
FONT_DIR = Path("C:/Windows/Fonts")


def font(size, bold=False):
    return ImageFont.truetype(str(FONT_DIR / ("seguisb.ttf" if bold else "segoeui.ttf")), size)


def wrapped(draw, text, face, width):
    lines, line = [], ""
    for word in text.split():
        trial = f"{line} {word}".strip()
        if draw.textlength(trial, font=face) <= width:
            line = trial
        else:
            if line:
                lines.append(line)
            line = word
    if line:
        lines.append(line)
    return lines


def block(draw, xy, text, size=30, color=INK, width=800, bold=False, spacing=12):
    x, y = xy
    face = font(size, bold)
    lines = wrapped(draw, text, face, width)
    for line in lines:
        draw.text((x, y), line, font=face, fill=color)
        y += size + spacing
    return y


def box(draw, rect, title, body, accent=False):
    x, y, x2, y2 = rect
    draw.rounded_rectangle(
        rect, radius=10, fill="white", outline=BLUE if accent else "#ccd2d6", width=3
    )
    draw.rectangle((x, y + 12, x + 5, y2 - 12), fill=BLUE if accent else "#8598a6")
    end = block(draw, (x + 28, y + 22), title, 32, width=x2 - x - 56, bold=True)
    bottom = block(draw, (x + 28, end + 12), body, 26, MUTED, width=x2 - x - 56, spacing=9)
    assert bottom < y2 + 1, (title, bottom, y2)


def arrow(draw, points, color=BLUE):
    draw.line(points, fill=color, width=4, joint="curve")
    (x1, y1), (x2, y2) = points[-2:]
    angle = math.atan2(y2 - y1, x2 - x1)
    pts = [(x2, y2)] + [
        (x2 - 17 * math.cos(angle + d), y2 - 17 * math.sin(angle + d)) for d in (-0.48, 0.48)
    ]
    draw.polygon(pts, fill=color)


def card(kind):
    if kind.startswith("repo-"):
        return repository_card(kind)
    im = Image.new("RGB", (W, CONTENT_H), BG)
    d = ImageDraw.Draw(im)
    d.text((90, 48), "HEALTHOPS  /  APPLICATION WALKTHROUGH", font=font(23, True), fill=BLUE)
    if kind == "title":
        d.rectangle((92, 180, 103, 540), fill=BLUE)
        block(d, (145, 190), "HealthOps", 88, bold=True, width=1500)
        block(d, (148, 315), "Clinical trial prescreening", 49, width=1450)
        block(
            d,
            (148, 410),
            "Check the requirements. See the evidence. Record a human decision.",
            34,
            MUTED,
            width=1230,
        )
        d.line((150, 576, 1770, 576), fill="#c5cdd1", width=2)
        for x, num, title, body in [
            (150, "01", "Understand the flow", "Patient records, trial rules, and optional AI"),
            (720, "02", "Explore the workspace", "Accounts, settings, and screening"),
            (1290, "03", "Follow the decision", "Evidence, review, and saved history"),
        ]:
            d.text((x, 630), num, font=font(30, True), fill=BLUE)
            block(d, (x, 685), title, 31, bold=True, width=480)
            block(d, (x, 741), body, 26, MUTED, width=460)
    elif kind == "inputs":
        block(d, (90, 111), "Two inputs. One screening workflow.", 53, bold=True, width=1700)
        box(d, (90, 245, 555, 445), "Synthetic patient records", "Synthea generates FHIR files.")
        box(
            d,
            (670, 245, 1160, 445),
            "HAPI FHIR + PostgreSQL",
            "Imported records are stored and served through the FHIR API.",
        )
        box(
            d,
            (90, 545, 555, 775),
            "Trial requirements",
            "ClinicalTrials.gov study snapshots, with source and retrieval date.",
        )
        box(
            d,
            (670, 545, 1160, 775),
            "Reviewed partial rules",
            "A person checks the interpretation and approves its exact version.",
        )
        box(
            d,
            (1320, 363, 1830, 662),
            "HealthOps",
            "React dashboard + FastAPI. Defined rules compare patient evidence "
            "with supported requirements.",
            True,
        )
        arrow(d, [(555, 345), (670, 345)])
        arrow(d, [(555, 660), (670, 660)])
        arrow(d, [(1160, 345), (1240, 345), (1240, 445), (1320, 445)])
        arrow(d, [(1160, 660), (1240, 660), (1240, 580), (1320, 580)])
        block(
            d,
            (90, 843),
            "Bundled fictional patients and trial exercises are also available "
            "for trying the workflow.",
            26,
            MUTED,
            width=1730,
        )
    elif kind == "workflow":
        block(d, (90, 111), "The evidence stays with the decision.", 53, bold=True, width=1700)
        boxes = [
            (90, "Defined checks", "Met / not met / unknown"),
            (535, "Saved assessment", "Findings + source evidence"),
            (980, "Human review", "Next step + recorded reason"),
            (1425, "Review history", "SQLite keeps the assessment and review events"),
        ]
        for x, title, body in boxes:
            box(d, (x, 335, x + 390, 575), title, body, accent=title == "Human review")
        for x in (480, 925, 1370):
            arrow(d, [(x, 450), (x + 55, 450)])
        box(
            d,
            (655, 675, 1280, 870),
            "Optional evidence assistant",
            "Read-only tools help explain the saved assessment. No decision-making access.",
        )
        arrow(d, [(730, 575), (730, 650), (760, 650), (760, 675)])
        arrow(d, [(1280, 770), (1340, 770), (1340, 595), (1195, 595), (1195, 575)])
        block(
            d,
            (90, 234),
            "Screening results and a reviewer’s decision are different things.",
            30,
            MUTED,
            width=1730,
        )
    elif kind == "assistant":
        block(d, (90, 111), "What the optional AI can read", 53, bold=True, width=1700)
        box(d, (90, 360, 475, 600), "Your question", "About one saved patient assessment.")
        box(
            d,
            (590, 360, 990, 600),
            "Optional model",
            "Interprets the question and selects relevant evidence.",
            True,
        )
        box(d, (1120, 250, 1820, 430), "Assessment summary", "get_screening_summary")
        box(d, (1120, 455, 1820, 635), "A requirement’s evidence", "get_criterion_evidence")
        box(d, (1120, 660, 1820, 840), "Available review steps", "get_review_workflow")
        arrow(d, [(475, 480), (590, 480)])
        arrow(d, [(990, 480), (1050, 480), (1050, 340), (1120, 340)])
        arrow(d, [(1050, 480), (1050, 545), (1120, 545)])
        arrow(d, [(1050, 545), (1050, 750), (1120, 750)])
        block(
            d,
            (90, 702),
            "The server builds the cited answer from saved findings.",
            30,
            width=885,
            bold=True,
        )
        block(
            d, (90, 800), "No record changes. No enrollment. No web search.", 27, MUTED, width=890
        )
    elif kind == "closing":
        block(d, (90, 148), "Evidence you can inspect.", 66, bold=True, width=1720)
        block(d, (90, 244), "A decision a person can explain.", 66, bold=True, width=1720)
        for y, n, title, body in [
            (
                395,
                "01",
                "Bring the inputs together",
                "Synthetic patient records and reviewed trial rules.",
            ),
            (
                525,
                "02",
                "Check and explain the evidence",
                "Defined checks, with optional AI assistance.",
            ),
            (
                655,
                "03",
                "Record the next step",
                "A human decision, its reason, and the saved history.",
            ),
        ]:
            d.text((95, y), n, font=font(36, True), fill=BLUE)
            block(d, (183, y), title, 35, bold=True, width=1500)
            block(d, (183, y + 55), body, 28, MUTED, width=1500)
        d.text((93, 850), "github.com/shshakib/healthops-ai", font=font(29), fill=BLUE)
    else:
        raise ValueError(kind)
    return im


def repository_card(kind):
    """Readable maps beside the actual GitHub captures; no simulated code UI."""
    im = Image.new("RGB", (W, CONTENT_H), BG)
    d = ImageDraw.Draw(im)
    d.text((90, 48), "HEALTHOPS  /  REPOSITORY WALKTHROUGH", font=font(23, True), fill=BLUE)
    layouts = {
        "repo-title": (
            "A tour of the project",
            "Where the code lives, what the files contain, and how it fits together.",
            [
                ("01  Follow a screening", "React interface → Python API → rules → saved evidence"),
                (
                    "02  Find the right folder",
                    "Application code, sample data, documentation, and tests",
                ),
                ("03  Run and check it", "Docker, local tools, and automated GitHub checks"),
            ],
        ),
        "repo-flow": (
            "Follow one screening request",
            "Example: a coordinator checks a synthetic patient for a trial.",
            [
                (
                    "frontend/src → api.py",
                    "The form sends the patient, trial, and assessment date.",
                ),
                (
                    "fhir.py → screening.py / trial_rules.py",
                    "Read the records, apply supported rules, and keep unknowns explicit.",
                ),
                (
                    "store.py → dashboard",
                    "Save the findings and evidence; return an assessment for human review.",
                ),
            ],
        ),
        "repo-backend": (
            "Inside src/healthops",
            "Python modules split the work into clear responsibilities.",
            [
                (
                    "api.py · auth.py",
                    "Requests, validation, login, and server-enforced permissions",
                ),
                (
                    "fhir.py · synthea.py · trials.py",
                    "Patient-record access, import handling, and trial snapshots",
                ),
                (
                    "screening.py · trial_rules.py · store.py",
                    "Defined checks, reviewed rule versions, and saved decisions",
                ),
            ],
        ),
        "repo-assistant": (
            "Where AI fits in the code",
            "assistant.py + providers.py — questions about one saved assessment.",
            [
                ("get_screening_summary", "Read the findings and the available requirement IDs."),
                (
                    "get_criterion_evidence",
                    "Read the saved evidence behind a specific requirement.",
                ),
                (
                    "get_review_workflow",
                    "Explain available human review steps. Cannot submit a decision.",
                ),
            ],
        ),
        "repo-storage": (
            "Code files and running data",
            "These have different homes in the local Docker setup.",
            [
                (
                    "GitHub repository",
                    "Source code, public trial JSON snapshots, synthetic test cases, and docs",
                ),
                (
                    "HAPI FHIR + PostgreSQL volume",
                    "Imported synthetic patient records, served through the FHIR API",
                ),
                (
                    "HealthOps SQLite + persistent volume",
                    "Accounts, assessment snapshots, rule reviews, and human decisions",
                ),
            ],
        ),
        "repo-runtime": (
            "How the local services fit together",
            "compose.yaml starts the core application and its data services.",
            [
                ("HealthOps container", "Built React interface + Python FastAPI application"),
                ("HAPI FHIR → PostgreSQL", "FHIR service and its patient-record database"),
                (
                    "Optional profiles",
                    "Synthea generates data. MLflow provides an interface for recorded traces.",
                ),
            ],
        ),
        "repo-change": (
            "Where would I make a change?",
            "Start with the part of the workflow you want to improve.",
            [
                ("Change a screen", "frontend/src → browser checks in frontend/tests"),
                (
                    "Change a supported rule",
                    "screening.py / trial_rules.py → Python tests in tests",
                ),
                (
                    "Change an assistant response",
                    "assistant.py → fixed evaluation cases and preserved results",
                ),
            ],
        ),
        "repo-end": (
            "A place for each part of the work",
            "The application walkthrough shows the product; this tour shows how it is built.",
            [
                ("Read", "README.md for the purpose and flow; docs for decisions and instructions"),
                ("Explore", "frontend + src/healthops for the interface and application behavior"),
                ("Verify", "tests + evaluation reports + GitHub checks for evidence of what works"),
            ],
        ),
    }
    title, subtitle, rows = layouts[kind]
    block(d, (90, 115), title, 57, bold=True, width=1750)
    block(d, (90, 210), subtitle, 29, MUTED, width=1730)
    for i, (label, body) in enumerate(rows):
        y = 319 + i * 190
        box(d, (90, y, 1830, y + 166), label, body, accent=i == 0)
    return im


def timestamp(seconds, srt=False):
    ms = round(seconds * 1000)
    h, ms = divmod(ms, 3600000)
    m, ms = divmod(ms, 60000)
    s, ms = divmod(ms, 1000)
    return f"{h:02}:{m:02}:{s:02}{',' if srt else '.'}{ms:03}"


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    FRAMES.mkdir(parents=True, exist_ok=True)
    captions, concat, timeline, chapters = [], [], [], []
    narration = [
        f"# HealthOps — video {VIDEO} narration",
        "",
        "Read the caption paragraphs at a comfortable pace. Timings match the silent MP4.",
        "The video uses actual browser captures with deliberate holds for narration.",
        COMMENT,
        "",
    ]
    now = 0.0
    cue = 0
    previous_chapter = None
    for scene in STORY:
        name = scene["image"]
        source = WORK / "captures" / f"{name}.png"
        is_card = not source.exists()
        if is_card:
            base = card(name)
        else:
            base = Image.new("RGB", (W, CONTENT_H), INK)
            with Image.open(source) as raw:
                screenshot = ImageOps.contain(
                    raw.convert("RGB"), (W, CONTENT_H), Image.Resampling.LANCZOS
                )
            base.paste(
                screenshot, ((W - screenshot.width) // 2, (CONTENT_H - screenshot.height) // 2)
            )
        if scene["chapter"] != previous_chapter:
            chapters.append({"start": now, "title": scene["chapter"]})
            narration.extend([f"## {timestamp(now)[:8]} — {scene['chapter']}", ""])
            previous_chapter = scene["chapter"]
        for line in scene["captions"]:
            cue += 1
            duration = math.ceil(max(6, len(line.split()) / 2.17 + 1) * 10) / 10
            im = Image.new("RGB", (W, H), INK)
            im.paste(base, (0, 0))
            d = ImageDraw.Draw(im)
            d.line((0, CONTENT_H, W, CONTENT_H), fill="#7c9cb7", width=2)
            d.text((64, 951), scene["chapter"].upper(), font=font(18, True), fill="#b7cce0")
            tag = TAG
            d.text(
                (W - 64 - d.textlength(tag, font=font(17)), 952), tag, font=font(17), fill="#b6c0ca"
            )
            lines = wrapped(d, line, font(31), W - 128)
            assert len(lines) <= 2, (cue, line, lines)
            if len(lines) == 2:
                words = line.split()
                splits = [(" ".join(words[:i]), " ".join(words[i:])) for i in range(1, len(words))]
                fits = [
                    pair
                    for pair in splits
                    if all(d.textlength(part, font=font(31)) <= W - 128 for part in pair)
                ]
                lines = min(
                    fits,
                    key=lambda pair: abs(
                        d.textlength(pair[0], font=font(31)) - d.textlength(pair[1], font=font(31))
                    ),
                )
            for i, text in enumerate(lines):
                d.text(
                    ((W - d.textlength(text, font=font(31))) / 2, 982 + i * 40),
                    text,
                    font=font(31),
                    fill="white",
                )
            frame = FRAMES / f"{cue:03}.png"
            im.save(frame)
            concat.extend([f"file '{frame.as_posix()}'", f"duration {duration:.1f}"])
            # Standard subtitles stay separate so a future voice-over edit can retime them.
            captions.extend(
                [
                    str(cue),
                    f"{timestamp(now, True)} --> {timestamp(now + duration, True)}",
                    line,
                    "",
                ]
            )
            narration.extend([f"**{timestamp(now)[:8]}**  {line}", ""])
            timeline.append(
                {
                    "cue": cue,
                    "start": round(now, 3),
                    "end": round(now + duration, 3),
                    "image": name,
                    "chapter": scene["chapter"],
                    "caption": line,
                }
            )
            now = round(now + duration, 3)
    concat.append(f"file '{frame.as_posix()}'")
    (WORK / "frames.ffconcat").write_text("\n".join(concat) + "\n", encoding="utf-8")
    (OUT / f"{STEM}.srt").write_text("\n".join(captions), encoding="utf-8")
    (PRODUCTION / f"video-{VIDEO}-narration.md").write_text("\n".join(narration), encoding="utf-8")
    (OUT / "voiceover-script.md").write_text("\n".join(narration), encoding="utf-8")
    (OUT / "timeline.json").write_text(json.dumps(timeline, indent=2), encoding="utf-8")
    metadata = [
        ";FFMETADATA1",
        f"title=HealthOps — {TITLE}",
        f"comment={COMMENT}",
    ]
    for i, ch in enumerate(chapters):
        end = chapters[i + 1]["start"] if i + 1 < len(chapters) else now
        metadata.extend(
            [
                "[CHAPTER]",
                "TIMEBASE=1/1000",
                f"START={round(ch['start'] * 1000)}",
                f"END={round(end * 1000)}",
                f"title={ch['title']}",
            ]
        )
    (WORK / "chapters.ffmeta").write_text("\n".join(metadata), encoding="utf-8")
    (OUT / "chapters.txt").write_text(
        "\n".join(f"{timestamp(c['start'])[:8]} {c['title']}" for c in chapters) + "\n",
        encoding="utf-8",
    )
    print(f"Rendering {cue} caption cues; {now:.1f} seconds ({now / 60:.1f} minutes).", flush=True)
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    cmd = [
        ffmpeg,
        "-hide_banner",
        "-y",
        "-loglevel",
        "warning",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        str(WORK / "frames.ffconcat"),
        "-i",
        str(WORK / "chapters.ffmeta"),
        "-map_metadata",
        "1",
        "-map_chapters",
        "1",
        "-an",
        "-t",
        str(now),
        "-r",
        "15",
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-tune",
        "stillimage",
        "-crf",
        "20",
        "-pix_fmt",
        "yuv420p",
        "-movflags",
        "+faststart",
        str(OUT / f"{STEM}.mp4"),
    ]
    with (WORK / "encode.log").open("w", encoding="utf-8") as log:
        subprocess.run(cmd, check=True, stderr=log)
    manifest = {
        "duration_seconds": now,
        "resolution": [W, H],
        "fps": 15,
        "audio": False,
        "caption_cues": cue,
        "scenes": len(STORY),
        "format": "H.264 MP4",
        "capture_method": (
            "Actual browser screenshots edited into an instructional walkthrough; "
            "not continuous cursor recording."
        ),
        "data": (
            "Synthea records copied read-only from HAPI, "
            "plus explicitly labelled handcrafted fixtures."
        ),
        "reviews": "Simulated, isolated SQLite ledger.",
        "assistant": "Evidence-only. No provider credentials or live model calls.",
        "sha256": hashlib.sha256((OUT / f"{STEM}.mp4").read_bytes()).hexdigest(),
    }
    if VIDEO == "two":
        for key in ("data", "reviews", "assistant"):
            manifest.pop(key)
        manifest["source"] = "Public shshakib/HealthOps-AI repository at commit 2af2535."
        manifest["scope"] = "Repository architecture tour; no app actions or model calls."
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, indent=2), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--video", choices=("one", "two"), default="one")
    VIDEO = parser.parse_args().video
    if VIDEO == "two":
        WORK = ROOT / ".local/video-two"
        OUT = WORK / "export"
        FRAMES = WORK / "frames"
        STEM = "healthops-repository-tour"
        TITLE = "Repository walkthrough"
        TAG = "PUBLIC REPOSITORY  ·  LOCAL APPLICATION"
        COMMENT = (
            "Actual public GitHub captures and architecture cards; no runtime data or secrets."
        )
    PRODUCTION = WORK / "production"
    storyboard = PRODUCTION / f"video-{VIDEO}-storyboard.json"
    if not storyboard.is_file():
        parser.error(
            f"Local storyboard not found: {storyboard}. Restore your production files first."
        )
    STORY = json.loads(storyboard.read_text(encoding="utf-8"))
    main()
