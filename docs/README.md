# HealthOps documentation

Start with the [project README](../README.md) for the purpose, workflow, screenshots,
and Docker quick start.

| I want to… | Guide |
|---|---|
| Run, troubleshoot, or back up the Docker stack | [Docker](docker.md) |
| Generate and import synthetic patient records | [Synthea pipeline](synthea.md) |
| Use the dashboard, run Python directly, or try the API | [Dashboard](dashboard.md) |
| Set up accounts and understand permissions | [Authentication](authentication.md) |
| Review registry criteria and approve a rule version | [Trial interpretations](trials.md) |
| Configure a model and understand its tools | [Evidence assistant](assistant.md) |
| Inspect monitoring and evaluation results | [Evaluation](evaluation.md), [fresh results](evaluation/fresh/README.md) |
| Understand the automated checks | [CI](ci.md) |
| Watch the application walkthrough | [Demo](demo/video-one.md) |
| Read the repository-tour script | [Repository tour](demo/video-two.md) |

The [design notes](interface-design.md) explain the interface choices.
The [project brief](project-brief.md) and [milestones](milestones.md) preserve the
original scope and implementation plan. [Release notes](releases/v0.2.0.md) and
the [development checkpoint log](current-state.md) are dated records; counts,
screenshots, and workspace status in older entries describe that point in time.

Evaluation JSON files, protocols, and rejected experiments are kept deliberately
so reported results can be inspected. Generated databases, recordings, build
outputs, and local credentials are excluded from the repository.
