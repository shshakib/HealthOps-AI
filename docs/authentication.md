# Login and permissions

HealthOps uses local accounts and server-side sessions. No identity-provider
subscription, cloud account, or API key is required. Accounts, password hashes,
sessions, and account events live in the existing HealthOps SQLite database.
HAPI still stores FHIR resources separately in PostgreSQL.

## First administrator

Start the stack, then create your administrator from a trusted terminal:

```powershell
docker compose up --build -d --wait --wait-timeout 600
docker compose exec healthops python -m healthops.auth admin
```

The command prompts twice for a password without displaying it. Use 15–128
characters; usernames allow 3–64 letters, numbers, dots, underscores, or hyphens
and are case-insensitive. There are no built-in accounts or default passwords.
Bootstrap refuses to run once any account exists. Do not put passwords in shell
arguments, commit them, or use the isolated test accounts in your working database.

For direct Python development, create the account in the same database as the API:

```powershell
& '.\.venv\Scripts\python.exe' -m healthops.auth admin
& '.\.venv\Scripts\python.exe' -m healthops
```

`HEALTHOPS_DB_PATH` selects the database for both commands. Docker's volume and
the direct-Python `.local/healthops.sqlite3` file are separate workspaces.

Open [the Docker dashboard](http://127.0.0.1:18000/) and sign in. The administrator
can select **Manage users** to create accounts, change roles, disable users, or
reset passwords. Users can change their own password. Share initial passwords
privately and have recipients change them. At least one active administrator is
required; account IDs and usernames remain stable for historical attribution.

## Role matrix

| Action | Viewer | Reviewer | Admin |
|---|---|---|---|
| Read synthetic patients, trial snapshots, assessments, history | Yes | Yes | Yes |
| Ask the read-only evidence assistant | Yes | Yes | Yes |
| Create a screening assessment | No | Yes | Yes |
| Draft/revise trial rules and approve/reject interpretations | No | Yes | Yes |
| Record a patient-screening decision | No | Yes | Yes |
| Change provider, model, or API key | No | No | Yes |
| Manage users and inspect account activity | No | No | Yes |
| Change own password and sign out | Yes | Yes | Yes |

The server checks permissions on direct API requests as well as browser actions.
All roles currently see the same synthetic cohort; patient assignment, tenant
isolation, de-identification, and field-level permissions are not implemented.
Viewers can use a model already enabled by an administrator, so that access can
incur provider charges. Model tools cannot change users, rules, or review decisions.

## Sessions and security behavior

- Passwords use a random salt and scrypt (`N=131072`, `r=8`, `p=1`). Passwords
  are never returned by the API or stored in plaintext in the database.
- The browser receives a random, HttpOnly, SameSite=Strict session cookie. Only
  its SHA-256 digest is stored on the server. Sessions expire after eight hours.
  The Secure cookie flag is set for HTTPS; local loopback HTTP is supported.
- Logout revokes the current session. Role changes, disabling a user, password
  resets, and password changes revoke all of that user's sessions. New requests
  must sign in again; an already-running request may finish.
- Every mutation requires `X-HealthOps-Request: 1`. Foreign browser origins and
  cross-site fetches are rejected. No cross-origin access is enabled. Use a
  consistent host (`127.0.0.1` or `localhost`) for the UI and API.
- Login is limited to five attempts per username and 30 per client address in a
  15-minute window. Successful sign-in clears the username's recorded attempts.
  Invalid usernames and passwords produce the same error.
- Account activity records sign-ins, failed logins, logout, account creation,
  and account changes. The administrator sees the latest 100 events. Review
  evidence and decisions remain in their original ledger.
- Responses containing application data are marked `Cache-Control: no-store`.
  Session secrets and passwords are not put into localStorage or sessionStorage.

The initial account requires trusted machine access; there is no anonymous
web-based registration or password-reset endpoint. Keep an accessible administrator
account and back up the persistent volume. There is no email recovery or MFA yet.
Local accounts are not clinical credential verification or enterprise SSO.
SQLite and its audit records are not tamper-proof against the machine owner.

## Existing reviews

Existing patient data, study interpretations, snapshots, and decisions are retained.
New review events capture the authenticated account ID, username, and role at the
time of review. A submitted `reviewer` label is accepted for compatibility but
ignored for identity. Earlier events keep `self_reported_demo_only`; they are not
retroactively attributed to new accounts or relabeled as authenticated.

## API clients and maintenance

Sign in at `POST /api/v1/auth/login`, retain its cookie, and send the mutation
header on POSTs. `/api/v1/auth/me` returns the current account; `/auth/logout`
revokes its session. API documentation is available after dashboard sign-in and
exposes the request header with its required default. Maintenance scripts prompt
for a username and password and retain cookies only in process memory.
Use `docker compose exec` without `-T` for commands that prompt for a password.

Only HealthOps publishes a port in default Compose. HAPI and PostgreSQL stay on
the internal Docker network. A trusted developer can temporarily expose HAPI for
the existing host-side importer and connectivity tests:

```powershell
docker compose -f compose.yaml -f compose.fhir-dev.yaml up -d --wait --wait-timeout 600
# Run the host-side Synthea import/check commands.
docker compose -f compose.yaml up -d --wait --wait-timeout 600
```

The override exposes an **unauthenticated** HAPI API on loopback port 8080 and
bypasses HealthOps roles. Disable it again after maintenance. Docker administrators
and processes with database access remain trusted. This is a local synthetic-data
prototype; HTTPS ingress, enterprise identity, and production hardening are separate work.

## Verification

Backend tests cover anonymous denial, role enforcement, forged reviewer names,
rule-review attribution, session expiry/revocation, CSRF, login throttling, and
last-administrator protection. Browser tests exercise actual sign-in/out, viewer
restrictions, reviewer attribution, account creation, and password change. Existing
workflow tests now authenticate through the same login endpoint. CI runs both suites.
