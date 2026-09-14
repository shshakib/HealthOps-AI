# Saved public study records

Three curated snapshots from the [ClinicalTrials.gov API v2](https://clinicaltrials.gov/data-api/api).
Each study has an immutable directory named by the SHA-256 of the exact downloaded
response, containing `study.json` and retrieval metadata in `snapshot.json`.
`latest.json` points to the locally selected version. Old versions are retained.

- [NCT07247084](https://clinicaltrials.gov/study/NCT07247084): an obesity study that
  excludes diabetes; demonstrates that search relevance is not eligibility.
- [NCT06591286](https://clinicaltrials.gov/study/NCT06591286): T2D monitoring study
  with treatment, laboratory timing, and hospital context requiring manual review.
- [NCT06750497](https://clinicaltrials.gov/study/NCT06750497): healthy/T2D cohorts
  with ambiguous BMI text; the prototype preserves rather than repairs that text.

These are public registry records, not patient records. Their presence is not an
endorsement, verification of medical claims, confirmation of site availability,
or approval of an eligibility interpretation. Registry content is attributed to
ClinicalTrials.gov and its study record submitters. Refreshes are explicit via
`python -m healthops.trials import`; runtime API reads stay offline.
