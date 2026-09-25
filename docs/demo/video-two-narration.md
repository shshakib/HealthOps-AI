# HealthOps — video two narration

Read the caption paragraphs at a comfortable pace. Timings match the silent MP4.
The video uses actual browser captures with deliberate holds for narration.
Actual public GitHub captures and architecture cards; no runtime data or secrets.

## 00:00:00 — What this tour covers

**00:00:00**  In the first video, I showed how someone uses HealthOps. This time, let's open the project and see how it is put together.

**00:00:11**  I'll go through the main folders, explain what they contain, and follow a screening request through the code. You don't need to read every line.

## 00:00:24 — Start at the repository

**00:00:24**  This is the public GitHub repository. The README explains the problem, shows the workflow, and gives you the instructions to run it locally.

**00:00:35**  The main folders separate the interface, Python application, sample data, documentation, and tests. Let's start with the part a reviewer actually sees.

## 00:00:47 — The interface

**00:00:47**  The frontend folder contains the React application. This is the dashboard with login, patient selection, trial rules, assessments, and review history.

**00:00:57**  package.json lists its tools and dependencies. The lock file records dependency versions, and Vite builds the interface into files the application can serve.

**00:01:09**  Inside frontend/src, main.jsx brings the workspace together. The JSX files define the screens and their behavior, while style.css controls their appearance.

**00:01:20**  Auth handles login and user management. AISettings and ProviderSettings contain the administrator's model settings, and Assistant contains the assessment question panel.

## 00:01:30 — Follow a screening request

**00:01:30**  Imagine a coordinator chooses a patient and a trial, then clicks to run screening. The interface sends that selection to the Python API.

**00:01:42**  The application reads the patient's records, checks the supported rules, and saves the findings with their evidence. The dashboard then displays that saved assessment.

## 00:01:54 — The Python application

**00:01:54**  That server-side work lives in src/healthops. These are Python files. api.py connects the dashboard's requests to the application functions.

**00:02:04**  auth.py handles accounts, sessions, and permissions. Permissions are checked on the server, so hiding a button in the dashboard is not the only control.

**00:02:16**  fhir.py reads patient records from the FHIR service. synthea.py supports the synthetic-data workflow, and trials.py manages the saved clinical-trial records.

**00:02:26**  screening.py checks the fictional exercises. trial_rules.py handles reviewed interpretations of registry criteria, including requirements that still need a person's judgment.

**00:02:36**  The checks use defined rules. If the evidence is missing or cannot support a requirement, the result stays unknown instead of becoming a match.

**00:02:49**  store.py keeps the assessment and its evidence. When a reviewer records a decision and reason, that review is saved so it can be revisited.

## 00:03:01 — The optional AI assistant

**00:03:01**  The optional AI part is in assistant.py. It helps someone ask questions about an assessment that has already been saved.

**00:03:11**  providers.py contains the model connections. The assistant can also run in evidence-only mode, so the core workflow does not require an API key.

**00:03:23**  The model has three read-only tools: read the assessment summary, read evidence for a requirement, and explain the available human review steps.

**00:03:34**  For example, it can look up why a blood-test requirement is unknown. The server checks the selected evidence and builds an answer with references.

**00:03:46**  This is a small tool-using assistant over saved evidence. There is no document vector database here, and the assistant cannot approve or enroll a patient.

## 00:03:58 — The data folder

**00:03:58**  Now let's look at data. This folder contains public trial snapshots and synthetic evaluation cases. It is not the running patient database.

**00:04:10**  Each folder here represents a ClinicalTrials.gov study. Its NCT identifier lets us trace the saved record back to the public registry.

**00:04:20**  Inside a study folder, latest.json points to a saved version. The long folder name identifies the snapshot, so the source version stays explicit.

**00:04:32**  study.json contains the registry response. snapshot.json records where it came from and when it was retrieved. JSON is structured text the application can read.

**00:04:44**  Here you can see that source information. It helps explain which trial record a rule interpretation was based on, even if the online study changes.

## 00:04:57 — Where the running data lives

**00:04:57**  The synthetic patient records are generated separately. After import, HAPI serves them from PostgreSQL. The application reaches those records through the FHIR API.

**00:05:08**  HealthOps uses SQLite for its accounts and review records. In Docker, persistent volumes keep the databases outside the application image when containers are replaced.

**00:05:20**  Generated files and local working data stay outside Git. The small handcrafted examples used in tests are defined separately in demo_data.py.

## 00:05:31 — Documentation and results

**00:05:31**  The docs folder explains the design and how to operate the project. Most files are Markdown, which GitHub displays as readable pages.

**00:05:42**  The project brief explains the original problem. Current-state records progress, and the focused guides explain authentication, Docker, trial rules, and the assistant.

**00:05:53**  Evaluation reports live here too. Markdown explains the results, while JSON keeps the detailed measurements and run information in a format tools can read.

**00:06:06**  This folder preserves both a fresh evaluation and a rejected prompt experiment. It keeps the failures visible instead of showing only the strongest result.

**00:06:18**  These are software checks on synthetic cases. They help us understand the assistant's behavior, but they do not establish clinical accuracy.

## 00:06:28 — Tests and local helpers

**00:06:28**  The tests folder contains Python tests for the API, screening rules, permissions, data handling, and assistant. These check behavior with controlled inputs.

**00:06:40**  For example, we can check that missing evidence stays unknown, an unauthorized action is rejected, and a saved review keeps its recorded reason.

**00:06:51**  frontend/tests covers the browser side with Playwright. It exercises user flows such as signing in, opening evidence, and returning to a saved assessment.

**00:07:03**  scripts contains local helpers. Some check the running stack, imported data, or persistence. Others start an isolated test workspace or demonstrate the workflow.

**00:07:14**  These support development and verification. The main application behavior still lives in src/healthops, and the interface code lives in frontend.

## 00:07:25 — Running the project

**00:07:25**  The infrastructure folder currently holds the Docker build file for Synthea. It prepares the generator used to create the synthetic patient records.

**00:07:36**  This is still the local design. Azure deployment, Databricks, and Snowflake are possible extensions; this folder does not contain a deployed cloud platform.

**00:07:47**  At the root, compose.yaml describes the services and how they connect. The main Dockerfile builds the dashboard and packages it with the Python application.

**00:08:00**  The core stack has HealthOps, HAPI FHIR, and PostgreSQL. Optional profiles run Synthea for data generation and the MLflow interface for inspecting traces.

**00:08:11**  telemetry.py records selected operational details for monitoring. That helps inspect assistant activity without putting patient text into those traces.

## 00:08:21 — Dependencies and local settings

**00:08:21**  pyproject.toml defines the Python package, dependencies, and development tools. The requirements lock files constrain dependency versions for the documented setup.

**00:08:31**  The example environment file documents settings. Actual local values go in .env, which is ignored by Git, along with databases, generated files, and dependencies.

**00:08:43**  The MIT license covers the project's code. THIRD_PARTY_NOTICES records the separate notices that apply to included external material.

## 00:08:53 — Automated GitHub checks

**00:08:53**  The GitHub Actions workflow lives in .github/workflows. checks.yml defines what runs when a change reaches the configured branches, tags, or pull requests.

**00:09:04**  It runs formatting checks, Python tests, an offline assistant evaluation, a frontend build, and browser tests. A separate job scans Git history for secrets.

**00:09:16**  The automated evaluation uses no provider keys. This workflow checks the code; it does not deploy an application to Azure when a commit is pushed.

## 00:09:29 — Making a change

**00:09:29**  So if I want to change a screen, I start in frontend. If I want to change a screening rule, I go to the Python modules.

**00:09:42**  For an assistant change, I also run the evaluation cases and inspect the failures. Each change should have evidence that the intended behavior still works.

## 00:09:54 — Where to go next

**00:09:54**  That's the structure: code for the workflow, sample files to reproduce it, documentation to explain it, and checks to test it.

**00:10:05**  If you are exploring the project, start with the README and application walkthrough. Then use these folders to follow the part you want to understand.
