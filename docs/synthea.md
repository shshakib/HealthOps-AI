# Synthea data pipeline

The working path is:

```text
Synthea (temporary Docker container)
  -> raw FHIR JSON + manifest on your computer
  -> import script -> HAPI FHIR -> PostgreSQL volume
  -> HealthOps patient/evidence API -> fictional screening -> human review
```

Synthea generates fictional people and longitudinal records. This demo uses its
Massachusetts model, five adults aged 40–75, population/provider seeds 42, a fixed
reference/end date of 2026-09-01, UTC, and one generation thread. It is not a
representative population, Canadian data, or a diabetes-enriched cohort. The
verified five-patient dataset has no Condition matching the exercise's exact
type-2 diabetes code; missing documentation correctly remains unknown.

The generator uses the official **Synthea v4.0.0** JAR with its release SHA-256
checked during image build. Java's image is pinned by digest. See the
[official generator instructions](https://github.com/synthetichealth/synthea/wiki/Basic-Setup-and-Running)
and [versioned release](https://github.com/synthetichealth/synthea/releases/tag/v4.0.0).

## Generate and import

Run in the project directory with Docker Desktop and the existing Python venv:

```powershell
docker compose -f compose.yaml -f compose.fhir-dev.yaml up --build -d --wait --wait-timeout 600
& '.\.venv\Scripts\python.exe' -m healthops.synthea generate
& '.\.venv\Scripts\python.exe' -m healthops.synthea import --dry-run
& '.\.venv\Scripts\python.exe' -m healthops.synthea import
& '.\.venv\Scripts\python.exe' scripts/check_synthea.py
docker compose -f compose.yaml up -d --wait --wait-timeout 600
```

**This workspace already has generated and imported data.** Skip `generate` when
resuming; it refuses to overwrite an existing FHIR directory. Import can be rerun.
The generation command launches a temporary fourth container and removes it when
finished. Only the three application services stay running. Initial builds need
internet access; saved files can be reimported without contacting Synthea online.

The maintenance override temporarily exposes unauthenticated HAPI on loopback 8080.
The final command removes that port. HealthOps port 18000 requires login; the check
script prompts for a Reviewer/Admin account created using the [login guide](authentication.md). If customized, pass
`--fhir-url http://127.0.0.1:YOUR_PORT/fhir` to import/check and
`--api-url http://127.0.0.1:YOUR_PORT` to the check script. Generation runs from the
source checkout on the host, not inside the HealthOps application container.

## Storage and provenance

| Location | Contents |
|---|---|
| `.local/synthea/fhir/` | Original generated patient, hospital, and practitioner JSON |
| `.local/synthea/manifest.json` | Generation arguments, timestamp, Dockerfile hash, file hashes |
| `.local/synthea/import-report.json` | Latest import counts and completed/failed transaction status |
| `.local/synthea/verification.json` | Latest live retrieval, repeat-import, and review check |
| `.local/synthea/quarantine/` | Validation errors and copies of malformed JSON when encountered |
| Docker `healthops_fhir_postgres` volume | HAPI's stored FHIR resources in PostgreSQL |
| Docker `healthops_healthops_reviews` volume | HealthOps screening snapshots and reviews in SQLite |

Generated artifacts are excluded from Git. Raw files remain unchanged during
import. The importer verifies their hashes and validates IDs and references
before sending anything. It translates UUID and unambiguous identifier references
to stable `ResourceType/id` references and uses transaction PUTs with original IDs.
All exported resource types are stored; HealthOps currently retrieves only Patient,
Condition, and Observation for its evidence bundle.

Transactions are atomic individually; the whole dataset is not a single atomic
import. If a request fails, the report retains the number completed and marks the
run failed. A timeout may occur after the server committed; rerun the same input
to recover. Stable PUTs prevent duplicate resources, though server history versions
can change. Never change source IDs to retry. This is structural checking, not
full FHIR profile or clinical terminology validation. Correct invalid inputs at
the source; do not edit a manifest merely to bypass an integrity error.

## Try the API

1. Open [Synthea patients](http://127.0.0.1:18000/api/v1/patients?source=hapi).
2. Copy a patient's `id`; use `GET /api/v1/patients/{patient_id}/record` in
   [Swagger](http://127.0.0.1:18000/docs) to retrieve its evidence bundle.
3. Submit `POST /api/v1/screenings` with:

```json
{
  "source": "hapi",
  "patient_id": "COPY_PATIENT_ID_HERE",
  "trial_id": "DEMO-SYNTHEA-T2D-001",
  "as_of": "2026-09-01"
}
```

4. Review evidence and unknowns, then use the existing review endpoint to record
   `request_information`, `dismiss`, or `advance_for_screening` with a reason.

The new exercise uses SNOMED CT `44054006` and LOINC `4548-4` as exact code matches,
with the original fictional thresholds. No terminology expansion or actual trial
eligibility interpretation is implemented. The source snapshot preserves the HAPI
evidence retrieved at screening time. Failed/incomplete HAPI retrieval returns an
error and never falls back to the handcrafted fixtures.

`source=fixtures` remains the default for the original three-patient demo.
`source=hapi` lists only records tagged by this importer. This tag identifies the
demo dataset; it is not an authorization control. HealthOps requires login and permissions; direct HAPI maintenance access bypasses those roles.

## Verified on 2026-09-13 (Toronto)

- Five Synthea patients; **3,613 resources across 20 types**, including 1,479
  Observations, 172 Conditions, 247 Encounters, and 507 Procedures.
- Seven FHIR files reproduced byte-for-byte in a second independent generator run.
  Comparison saved in `.local/synthea/reproduction-check.json`; second copy retained
  under `.local/synthea-reproduction/`.
- A repeat import preserved counts for every imported resource type.
- HealthOps retrieved each patient's evidence, including paginated results.
- A HAPI-backed screening and simulated human review retained the exact snapshot.

The live check adds one clearly labeled simulated screening/review each time.
Real trial snapshots and the separate interpretation-approval workflow are now
available; see [the trial guide](trials.md). Actual drafts await human review.
