# HealthOps — video one narration

Read the caption paragraphs at a comfortable pace. Timings match the silent MP4.
The video uses actual interface captures with deliberate holds for narration.
All review actions were simulated in an isolated ledger. No real model call is shown.

## 00:00:00 — The idea

**00:00:00**  Hi, this is HealthOps. I built it to help a research coordinator check whether a patient might be a fit for a clinical trial.

**00:00:12**  I'll show you how the data flows, then walk through the app from signing in to saving a review.

**00:00:21**  Everything here uses synthetic patients. I'm working in a separate demo workspace, so these actions won't change the main application's records.

## 00:00:32 — How the data reaches the app

**00:00:32**  We start with Synthea. It generates fictional patient records in FHIR, a standard format for exchanging health information.

**00:00:41**  Those records are imported into HAPI FHIR. PostgreSQL stores them, and HAPI makes them available through an API.

**00:00:51**  On the trial side, we save study records from ClinicalTrials.gov. Each snapshot keeps the source and the date it was saved.

**00:01:01**  A person reviews the supported trial rules before they're used for screening. The app then compares those rules with the patient's recorded evidence.

## 00:01:13 — What happens after screening

**00:01:13**  The checks give us three possible results: met, not met, or unknown. These results come from code and defined rules.

**00:01:23**  The optional assistant helps explain the saved assessment. It doesn't decide whether the patient is eligible.

**00:01:32**  A reviewer checks the evidence, chooses a next step, and records a reason. SQLite keeps the assessment and its review history.

## 00:01:42 — Sign in

**00:01:42**  Okay, let's open the app. Everyone signs in with an account, and their role controls what they can do.

**00:01:52**  I'll start as an administrator so I can show the account and model settings before we begin screening.

## 00:02:02 — The workspace

**00:02:02**  The workspace has three main sections: patient screening, trial rules, and review history.

**00:02:09**  This recording uses copies of our five imported Synthea patients. The three study records are saved registry snapshots.

## 00:02:18 — User management

**00:02:18**  In user management, we have viewers, reviewers, and administrators. A viewer can read records and ask the assistant questions.

**00:02:28**  A reviewer can also run screenings and record reviews. An administrator manages accounts and the workspace's AI settings.

**00:02:37**  To add someone, I enter a username, an initial password, and a role. I'm showing the form here without creating another account.

**00:02:48**  For an existing account, I can change its role, deactivate it, or reset its password. Saving a change revokes that account's sessions.

## 00:02:59 — Account activity

**00:02:59**  There's also an account activity log. It records actions such as sign-ins and account changes, with the actor and time.

## 00:03:10 — AI settings

**00:03:10**  Model configuration has its own settings page. Only an administrator can change it, so reviewers don't need to handle API keys.

**00:03:20**  For a cloud provider, I choose the provider and enter the exact model ID and API key. I'm leaving those fields empty in this demo.

**00:03:33**  OpenAI and Claude are supported. Switching the provider brings up the same model and key controls.

**00:03:41**  Gemini is another option. Saving settings doesn't make a model call; asking the assistant or testing the connection can.

**00:03:51**  There's also Ollama for a local model. The model needs to be available locally and support the tools this assistant uses.

**00:04:02**  For this walkthrough, I'll save evidence-only mode. The assistant will use saved findings without calling a language model.

**00:04:11**  With a model configured, the connection test checks one fictional assessment. Keys entered here last for the server session.

## 00:04:21 — Your account

**00:04:21**  Users can change their own password from the account bar. I'll leave this form untouched and move on to the roles.

## 00:04:32 — Try a viewer account

**00:04:32**  Now I'm signed in as a viewer. Notice that user management and model settings are no longer available.

**00:04:41**  The viewer can inspect records, but Run screening is disabled. These permissions are checked by the API as well.

## 00:04:51 — Switch to a reviewer

**00:04:51**  I'll switch to a reviewer account for the rest of the workflow. Any decisions I save will be tied to this signed-in user.

## 00:05:02 — Choose a patient

**00:05:02**  We can search for a patient by name or identifier. These unusual names come from Synthea; they don't represent real people.

## 00:05:13 — Inspect the health records

**00:05:13**  Before running anything, I can open the health records. This view shows the recorded conditions and observations available to the app.

**00:05:24**  I'll search for a blood-test result. The list includes the value and date, which both matter when checking a trial's requirements.

**00:05:34**  Opening a record shows its identifier, date, value, and code. We can also inspect the original FHIR resource.

## 00:05:44 — A trial needs reviewed rules

**00:05:44**  I've selected a saved registry study. Screening is blocked because nobody has approved an interpretation of this study's rules yet.

## 00:05:54 — Read the trial source

**00:05:54**  The Trial rules page shows the study, its source, and when the snapshot was saved.

**00:06:02**  The recruitment status belongs to that snapshot. It doesn't tell us whether a site is still accepting participants today.

**00:06:12**  Here are the original inclusion and exclusion criteria. A reviewer needs to compare these with what the app can actually check.

**00:06:23**  The saved study locations are available too. They provide context, but this app doesn't contact the study site.

## 00:06:32 — Prepare a partial interpretation

**00:06:32**  Prepare draft creates a partial interpretation. It stays inactive until a reviewer has looked at it.

**00:06:40**  For this study, the draft covers an age range and a recorded diabetes condition. Each component keeps its supporting source text.

**00:06:51**  That leaves other requirements for manual review. Preparing a draft doesn't mean the entire trial has been translated into code.

## 00:07:01 — Inspect the rule editor

**00:07:01**  If the interpretation needs a correction, I can revise its supported fields and source quotation. A changed draft becomes a new version.

## 00:07:12 — Record a trial-rule review

**00:07:12**  I can approve or reject this version and explain why. Here I'm recording a simulated approval in the separate demo workspace.

**00:07:23**  The note makes that clear. This demonstrates the approval workflow; it isn't a clinical validation of the study rules.

**00:07:33**  The approval is now saved with the reviewer and time. It applies to this specific interpretation and study snapshot.

## 00:07:43 — Run a registry screening

**00:07:43**  Back in screening, I select that approved version and the assessment date. Now I can run the supported checks.

**00:07:53**  The assessment is saved. In this case, the age requirement is met, while the condition check remains unresolved.

## 00:08:02 — Keep the limits visible

**00:08:02**  Full eligibility review stays unknown. The app keeps the remaining source requirements visible instead of treating a partial check as a final answer.

## 00:08:13 — Three small examples

**00:08:13**  To make the three result types easier to see, I'll switch to the small handcrafted examples included with the project.

**00:08:24**  These use a fictional diabetes exercise. Its thresholds are there to demonstrate the program, not to provide clinical guidance.

## 00:08:34 — When a requirement is met

**00:08:34**  In the first example, all three modeled requirements are met. Even here, the program doesn't declare the patient eligible or enroll them.

## 00:08:45 — When a requirement is not met

**00:08:45**  In this example, the recent blood-test value is outside the fictional range, so that requirement is marked not met.

## 00:08:55 — When evidence is unclear

**00:08:55**  For the rest of the walkthrough, I'll use the second example. It has a result we need to look at more carefully.

**00:09:06**  Age and diagnosis meet the rules, but the blood test is too old. That requirement is unknown because the evidence isn't recent enough.

## 00:09:17 — Open the supporting evidence

**00:09:17**  Here's the result behind that finding: 8.2 percent, recorded in August 2025. The assessment is using September 2026 as its reference date.

**00:09:29**  The original resource is available as well. The finding is linked to the evidence saved with this assessment.

## 00:09:38 — Ask about the assessment

**00:09:38**  Now I'll ask, what evidence is missing? The assistant points me back to the unresolved blood-test requirement.

**00:09:47**  The label says evidence-only answer. This response uses saved findings and templates; a language model isn't generating it.

## 00:09:56 — Where the optional AI fits

**00:09:56**  When a model is connected, it helps interpret the question and find the relevant saved evidence through three read-only tools.

**00:10:06**  Those tools read the assessment summary, a requirement's evidence, and the review workflow. The app builds the cited answer from those results.

**00:10:18**  It isn't searching the internet or making a treatment decision. Its access is limited to explaining this saved assessment.

## 00:10:27 — Follow the answer back to evidence

**00:10:27**  The answer links back to the finding, so I can check it myself. I don't have to take the assistant's explanation on trust.

## 00:10:39 — Ask about the next step

**00:10:39**  I can also ask what a reviewer can do next. The answer explains the available steps and how this response was produced.

## 00:10:50 — The assistant's boundary

**00:10:50**  Let's try something outside its job: asking it to enroll this patient.

**00:10:57**  It doesn't do that. It can explain the saved assessment, but it can't change records or make the review decision.

## 00:11:07 — Record the human review

**00:11:07**  This is where the reviewer decides. The choices are to request information, advance for further screening, or dismiss the match.

**00:11:17**  For this example, I'll request an updated blood test and record the reason. The note is clearly marked as a simulated demo review.

**00:11:29**  Before saving, I confirm that I've reviewed the evidence and unresolved requirements. The reviewer identity comes from my signed-in account.

## 00:11:39 — A saved decision

**00:11:39**  The decision and reason are now in the history. Saving this step doesn't send a message, order a test, or enroll anyone.

## 00:11:50 — Review history

**00:11:50**  The review ledger brings the saved assessments together. I can see the screening outcome separately from the review status.

**00:12:00**  Our example now says Information requested. The other assessments are still waiting for their first review.

## 00:12:09 — Reopen the saved case

**00:12:09**  Opening it again brings back the assessment and the recorded reason, with who reviewed it and when.

## 00:12:18 — Keep the evidence traceable

**00:12:18**  The provenance section includes the assessment identifier, evidence fingerprint, and rules version. Later review events don't replace the original evidence.

## 00:12:28 — The API behind the dashboard

**00:12:28**  Behind the dashboard is a FastAPI service. Its API documentation describes the endpoints for accounts, patient records, screening, and reviews.

## 00:12:38 — The complete workflow

**00:12:38**  So that's the flow: bring in synthetic records, review the trial rules, check the evidence, and let a person decide the next step.

**00:12:50**  The optional AI helps explain the assessment. The evidence and the human review remain the part we can come back and check.
