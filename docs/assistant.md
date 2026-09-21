# Evidence assistant

The dashboard now has **Ask about this assessment** beneath each saved screening.
It explains the screening, lists unknown requirements, and describes the available
human review steps. Click a citation to expand the original criterion and inspect
its saved patient evidence and trial source text.

## What runs now

The evidence-only mode is usable immediately, without a model, API key, or cloud
service. The three suggested questions use fixed templates and exact saved findings.
Other questions receive an explicit scope message. This fallback is not an LLM.

Optional Ollama, OpenAI, Claude (Anthropic), and Gemini integrations add a bounded agent that can interpret
natural-language questions and select relevant criteria. It uses:

- `get_screening_summary`: the selected assessment's criteria and statuses.
- `get_criterion_evidence`: one criterion's saved reason, record references, and source text.
- `get_review_workflow`: the allowed human review steps.

Tools are bound to the assessment loaded by the API. They cannot accept a different
patient ID, execute SQL, browse URLs, change findings, approve rules, or submit reviews.
No write tools are registered. Session authentication and server-enforced roles
also protect these endpoints; see [authentication](authentication.md).

The model selects a response topic and criterion IDs. The server validates the IDs
and assembles the response from the saved findings. Free-form model medical claims
are never displayed. Summary selections must retain every criterion, and missing-
evidence selections must retain every unknown. Specific-criterion selections require
that the model read that criterion's evidence first. This is an extractive evidence
assistant, not a general medical chatbot or a model that decides eligibility.

Each request is independent. There is no conversational memory, new screening, or
assistant transcript stored in the review ledger. Responses carry evidence/rule
hashes, assessment ID, review revision, actual duration, and successful tool-call
metadata. [Local MLflow traces and regression evaluation](evaluation.md) are implemented.
Real-provider verification and an independent held-out benchmark remain future work.

## Choose a provider, model, and API key

Open a saved assessment, then expand **Model connection settings** in the assistant.
Choose **OpenAI**, **Claude (Anthropic)**, **Gemini (Google)**, **Ollama (local)**,
or **Evidence only**. Enter the exact model ID from your provider account. Cloud
providers also need an API key. Choose **Save model settings** to activate it.

Saving makes no provider request. Asking a question with a cloud provider selected
sends that question and selected synthetic assessment findings/source excerpts to
the chosen provider and may incur API charges. The interface shows this before
you ask. The model must support tools; access, model-specific compatibility, and
live answer quality still need validation with your own key. No paid calls were
made while implementing or testing these adapters.

Keys entered in the dashboard are password fields cleared after submission. The
backend keeps keys in process memory; it never returns them in status, errors, or
assistant output. Nothing is written to browser storage, source files, or the
review database. A blank key preserves the existing key for that provider.
**Remove API key** clears that provider's key for the current server session.
Switching providers preserves the other providers' keys for this session.

Settings apply to this single local workspace. Use the single-process server in
Compose; session settings are not shared between multiple worker processes. A
restart discards dashboard-entered settings. For persistent defaults, edit the
ignored `.env` locally; `.env.example` lists the available variables:

| Provider value | Model variable | Key variable |
| --- | --- | --- |
| `openai` | `HEALTHOPS_OPENAI_MODEL` | `OPENAI_API_KEY` |
| `anthropic` | `HEALTHOPS_ANTHROPIC_MODEL` | `ANTHROPIC_API_KEY` |
| `gemini` | `HEALTHOPS_GEMINI_MODEL` | `GEMINI_API_KEY` |
| `ollama` | `HEALTHOPS_OLLAMA_MODEL` | None |

Set `HEALTHOPS_AI_PROVIDER` to choose the startup provider. An empty value defaults
to Ollama when its model is set, otherwise evidence-only. Environment-provided keys
are reloaded on restart, even if removed from a previous session. `.env` is a local
plaintext configuration option, not an encrypted secret vault; never commit it or
share `docker compose config` output after adding keys. Direct Python development
reads process environment variables, not `.env` automatically.

Configuration writes and cloud-backed questions require a same-origin localhost
request with `X-HealthOps-Request: 1`; the dashboard adds it automatically. Provider
HTTP endpoints are fixed, use HTTPS, and disable redirects/proxies. These controls
reduce cross-site request and credential-forwarding risks; they are not user
authentication. Keep the application on loopback as configured. The local HTTP
key-entry form is not suitable for a remote multiuser deployment.

Native adapters follow [OpenAI Responses function calling](https://developers.openai.com/api/docs/guides/function-calling),
[Claude tool use](https://platform.claude.com/docs/en/agents-and-tools/tool-use/overview),
and [Gemini content generation](https://ai.google.dev/api/generate-content).
Tool-call IDs and native response state are replayed between requests. OpenAI
requests use `store=false`. This does not make a general claim about each provider's
data-retention policy. Provider error bodies are not returned; fixed error messages
cover missing/rejected keys, access denial, model availability, rate limits, and outages.

## Optional local model

No real model or provider credential has been configured or live-validated in this workspace.
Provider protocols are tested with mocks and a local HTTP stub; that is not evidence of a
particular model's quality or performance. The default configuration stays offline.

Use a downloaded local Ollama model that supports tools. The adapter follows the
official [chat API](https://docs.ollama.com/api/chat) and
[tool-calling protocol](https://docs.ollama.com/capabilities/tool-calling).

For Docker, set `HEALTHOPS_OLLAMA_MODEL` in your ignored `.env` to the exact installed
model name. Compose connects to the host's Ollama through `host.docker.internal:11434`.
Recreate only HealthOps after changing configuration:

```powershell
docker compose -p healthops up -d --wait --wait-timeout 600 healthops
```

For direct Python development, set the environment before starting the API:

```powershell
$env:HEALTHOPS_OLLAMA_MODEL = 'YOUR_INSTALLED_LOCAL_MODEL'
$env:HEALTHOPS_OLLAMA_URL = 'http://127.0.0.1:11434'
& '.\.venv\Scripts\python.exe' -m healthops
```

The API accepts only local hostnames for this adapter, disables proxies/redirects,
and rejects model names containing `cloud`. Use a local model and an Ollama setup
with cloud functionality disabled; hostname checks alone cannot govern what an
external model server does. Do not expose the unauthenticated Ollama service to
the public network. Host accessibility from Docker depends on the local Ollama
binding/firewall; if unavailable, the assistant explicitly falls back.

`GET /api/v1/assistant/status` reports configuration, not model readiness. A successful
answer with `mode=model_assisted` confirms that the configured model completed a
validated tool path. `mode=fallback` includes a fixed reason code. Missing models,
network errors, malformed responses, unknown tools, invalid citations, and exhausted
budgets leave human review available. There are at most four model requests, three
tool calls per request, a 40-second deadline checked between calls, and a socket
timeout capped at 15 seconds per request. An evidence-only switch bypasses the model.

## API and verification

`POST /api/v1/screenings/{id}/assistant` accepts:

```json
{"question": "What evidence is missing?", "use_model": false}
```

Only the saved snapshot is read, even if live FHIR records later change. Unknown
criteria with no patient evidence remain visibly unsupported rather than gaining
invented record citations. Source text and direction are retained for registry findings.

The automated checks cover exact evidence attribution, unresolved/manual requirements,
outage fallback, scope refusals, forbidden tool calls, another-patient arguments,
invalid or omitted citations, iteration limits, input validation, no review-ledger
writes, the real HTTP adapter against a stub, and the dashboard citation flow.

```powershell
& '.\.venv\Scripts\python.exe' -m pytest -q
cd frontend
npm run build
npm run test:ui
```

Browser tests isolate settings from the shell, use fake keys with model bypass,
and use their own temporary review ledger. Live model selection and quality evaluation remain
open before claiming the LLM workflow is fully verified.
