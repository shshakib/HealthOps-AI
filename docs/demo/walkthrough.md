# HealthOps walkthrough

The README keeps the screenshots as its quick preview. For a more detailed look,
[watch the complete captioned application walkthrough](https://github.com/shshakib/HealthOps-AI/releases/download/v0.2.0/healthops-full-demo.mp4).
It runs for **13:01**, with no audio, and is ready for a later voice-over.

It starts with the architecture, then covers login, user management, administrator
model settings, role permissions, trial-rule review, patient screening, evidence,
the optional assistant, human review, and saved history.

See [recording details](video-one.md) for the exact scope and
[timed narration](video-one-narration.md) for the script. It uses real interface
captures held on screen for explanation. Patients are synthetic, review actions
are simulated in an isolated ledger, and the assistant runs in evidence-only mode.
The older short recording remains a historical release asset; it is no longer the
featured demo.

The separate [repository tour](video-two.md) explains the folders, source files,
data formats, storage, and automated checks. It is available locally for review.

## Your final manual acceptance check

On [your local dashboard](http://127.0.0.1:18000/), sign in with your own account:

1. Choose a synthetic patient and the matching fictional exercise. Run screening.
2. Open a finding and verify that you understand its evidence and any unknown.
3. Ask the assistant to explain it. Inspect the citations and mode label; a model
   answer may fall back, as documented in the fresh evaluation.
4. Decide whether to request information, advance for further screening, or dismiss.
   Record your own reason when you are ready to make that demo judgment.
5. Open review history and confirm that the evidence, identity, and reason remain.

This is product acceptance, not clinical validation. Actual registry interpretations
still need a person qualified to review their accuracy; automated tests and the
recorded simulation do not approve them in the live ledger.
