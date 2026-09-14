# Run HealthOps with Docker Compose

The Compose project starts three containers. HAPI uses PostgreSQL to store FHIR
resources; HealthOps currently stores its review ledger in SQLite on a separate
volume. The [Synthea pipeline](synthea.md) adds a temporary generator container and
connects imported records to HealthOps screening and human review.

| Service | Address on your computer | Storage |
| --- | --- | --- |
| HealthOps dashboard / API | http://127.0.0.1:18000/ (Swagger at `/docs`) | `healthops_reviews` volume |
| HAPI FHIR R4 | http://127.0.0.1:8080/fhir/metadata | PostgreSQL service |
| PostgreSQL | Internal Docker network only | `fhir_postgres` volume |

Inside Docker, services use the names `healthops`, `hapi`, and `postgres`. For
example, the HealthOps container reaches HAPI at `http://hapi:8080/fhir`.
The dashboard is built during the image build and served from the same HealthOps
container; no additional running frontend service is required. See [the dashboard guide](dashboard.md).
`localhost` inside a container refers to that container, not your computer.

## Start

Prerequisites: Docker Desktop running in Linux-container mode, with Compose v2.
Allow roughly 4 GB of Docker memory for this small stack; HAPI has a 2 GB container
limit and a 1.5 GB Java heap limit. Initial image downloads and HAPI's database
initialization can take several minutes. No cloud account or model key is needed.

From the repository directory:

```powershell
docker compose up --build -d --wait --wait-timeout 600
docker compose ps
```

PostgreSQL must become healthy before HAPI starts. HAPI's health check requests
FHIR metadata before HealthOps starts. HealthOps runs as a non-root user and checks
its own `/health` endpoint. The Dockerfile listens on all interfaces *inside* the
container; Compose publishes both HTTP ports only on your computer's loopback.

Port 18000 avoids colliding with existing services on ports 8000 and 8001.
The optional `.env.example` documents port/password overrides. Defaults work without
creating `.env`. The database password is a deliberately public local-demo value;
this unauthenticated synthetic-data stack is not a production deployment.

## Verify

```powershell
docker compose exec -T healthops python scripts/check_stack.py
docker compose exec -T healthops python scripts/demo.py
```

The first command checks actual network access from HealthOps to HAPI and a FHIR
patient-count query. The second exercises synthetic screening and simulated human
review; each run creates three local screening snapshots and one labeled test review.

HAPI begins empty on a fresh installation. After running the Synthea pipeline,
HealthOps uses `FHIR_BASE_URL` to retrieve imported patients when `source=hapi` is
selected. The default `source=fixtures` preserves the original three-patient demo.
See [the pipeline guide](synthea.md) for generation, import, and live verification.

## Stop, restart, and preserve records

```powershell
docker compose down
docker compose up -d --wait --wait-timeout 600
```

Normal `down` removes the containers and network while keeping named volumes.
Do not add `--volumes` unless you intend to erase the FHIR and review databases.
Avoid deleting volumes from Docker Desktop when retaining your records.

To verify persistence yourself (creates one labeled synthetic FHIR test patient
and one simulated review):

```powershell
docker compose exec -T healthops python scripts/check_persistence.py seed
docker compose down
docker compose up -d --wait --wait-timeout 600
docker compose exec -T healthops python scripts/check_persistence.py verify
```

This retains the test patient and review for inspection. They are infrastructure
test fixtures, not Synthea output.

The Docker review ledger is independent of the earlier `.local/healthops.sqlite3`
file. Existing direct-Python reviews stay in that file; this setup does not migrate
or overwrite them. PostgreSQL currently belongs to HAPI; a future application
database must use its own schema/database and migrations.

## Troubleshoot

```powershell
docker version
docker compose logs --tail 100 postgres hapi healthops
docker compose config --quiet
```

- A missing `dockerDesktopLinuxEngine` pipe means Docker's backend is unavailable,
  even if the Desktop window is open. Resolve Desktop/WSL startup before retrying.
- If a port is occupied, choose `HEALTHOPS_PORT` or `FHIR_PORT` in a local `.env`.
- If startup times out, inspect HAPI logs and available Docker memory.
- Changing `FHIR_DB_PASSWORD` after PostgreSQL initialized will not update the stored
  database password. Keep the existing value or perform an explicit password change;
  do not erase volumes as a routine fix.
- `/docs` loads Swagger assets from a CDN. The API and fixtures themselves can run
  offline once images and dependencies have been downloaded.

HAPI's PostgreSQL environment settings and Java metadata health check follow the
[official starter](https://github.com/hapifhir/hapi-fhir-jpaserver-starter/blob/master/docker-compose.yml).

Python, HAPI, and PostgreSQL images are pinned by digest as resolved on 2026-09-13.
Update those digests deliberately and repeat the stack and persistence checks when
upgrading. Image digests fix the image contents; they do not pin downloaded Python
build tools or replace periodic dependency/security updates.
