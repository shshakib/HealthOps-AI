# Third-party material

The MIT license applies to original HealthOps code and documentation. It does not
relicense third-party software, container images, terminology systems, or public
registry records bundled for this demonstration.

- `data/clinicaltrials/` contains dated public records from ClinicalTrials.gov and
  study submitters. Each raw response retains its source URL, retrieval timestamp,
  and checksum. See the [data provenance](data/clinicaltrials/README.md) and
  [ClinicalTrials.gov terms](https://clinicaltrials.gov/about-site/terms-conditions).
- Synthea is downloaded from its upstream project by the documented generation
  workflow. Its binaries and generated population are not committed here. See
  [Synthea](https://github.com/synthetichealth/synthea).
- HAPI FHIR, PostgreSQL, Python, Node.js, and application dependencies retain their
  respective licenses. Dependency versions are recorded in `requirements-dev.lock`,
  `frontend/package-lock.json`, and the pinned container definitions.
- The dashboard bundles IBM Plex Sans via Fontsource under the SIL Open Font
  License 1.1. Its [license](frontend/public/assets/ibm-plex-sans-LICENSE.txt)
  is also included in the built application. Fonts are served locally.
- Codes and terminology identifiers in synthetic examples are included to demonstrate
  interoperability, not as a redistributed terminology database or a claim of clinical
  validity. No real patient charts are included.
