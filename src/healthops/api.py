"""Authenticated local API for synthetic trial screening and human review."""

import os
from datetime import date
from pathlib import Path
from threading import Lock
from typing import Literal
from urllib.parse import urlsplit
from uuid import uuid4

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field

from healthops import __version__
from healthops.assistant import AssistantRequest, EvidenceAssistant
from healthops.auth import install_auth
from healthops.demo_data import DEMO_AS_OF, PATIENTS, SYNTHEA_TRIAL, TRIAL, get_patient
from healthops.evaluation import Pricing
from healthops.evaluation import run as evaluate
from healthops.evaluation import save as save_evaluation
from healthops.fhir import FhirClient, FhirError
from healthops.providers import ProviderSettings, ProviderUpdate
from healthops.screening import screen_patient
from healthops.store import ReviewStore
from healthops.telemetry import status as monitoring_status
from healthops.trial_rules import (
    RuleProposal,
    RuleReview,
    draft_proposal,
    screen_registry,
    validate_proposal,
)
from healthops.trials import TrialCatalog


class ScreeningRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    patient_id: str = Field(default="demo-001", min_length=1)
    trial_id: str = Field(default="DEMO-T2D-001", min_length=1)
    as_of: date = date.fromisoformat(DEMO_AS_OF)
    source: Literal["fixtures", "hapi"] = "fixtures"
    rule_set_id: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")


class EvaluationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    limit: int = Field(default=3, ge=1, le=5)
    pricing: Pricing | None = None


class ReviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    reviewer: str | None = Field(default=None, min_length=2, max_length=100)
    decision: Literal["advance_for_screening", "dismiss", "request_information"]
    reason: str = Field(min_length=10, max_length=2000)
    expected_revision: int = Field(default=0, ge=0)


def request_header(x_healthops_request: str = Header(default="1")):
    """Expose the required mutation header in interactive API documentation."""


def create_app(
    db_path: Path | None = None,
    fhir_client: FhirClient | None = None,
    trial_catalog: TrialCatalog | None = None,
    assistant: EvidenceAssistant | None = None,
    provider_settings: ProviderSettings | None = None,
) -> FastAPI:
    fhir = fhir_client or FhirClient()
    catalog = trial_catalog or TrialCatalog()
    settings = provider_settings if provider_settings is not None else ProviderSettings()

    def active_assistant():
        return assistant if assistant is not None else EvidenceAssistant(settings.client())

    store = ReviewStore(
        db_path
        if db_path is not None
        else Path(os.environ.get("HEALTHOPS_DB_PATH", ".local/healthops.sqlite3"))
    )
    app = FastAPI(
        title="HealthOps local prototype",
        dependencies=[Depends(request_header)],
        version=__version__,
        description=(
            "Synthea patients from HAPI (source=hapi) or bundled fixtures. "
            "Fictional demo rules and saved ClinicalTrials.gov studies are available. "
            "Registry screening requires a reviewed partial interpretation. "
            "Start by listing patients and "
            "trials, create a screening, then record a human review using the returned ID. "
            "Optional Ollama, OpenAI, Claude, or Gemini models use read-only evidence tools, "
            "with an offline fallback. "
            "Sign in through the dashboard first. Reviewer identity comes from the session. "
            "Local accounts, role permissions, and synthetic data only."
        ),
    )

    install_auth(app, store.path)
    evaluation_lock = Lock()

    @app.post("/api/v1/admin/evaluations")
    def evaluate_live(request: EvaluationRequest):
        if not settings.public()["model_configured"]:
            raise HTTPException(409, "Configure a model and its key in the dashboard first.")
        client = settings.client()
        if request.pricing and (request.pricing.provider, request.pricing.model) != (
            getattr(client, "provider", None),
            client.model,
        ):
            raise HTTPException(422, "Pricing must match the selected provider and model.")
        if not evaluation_lock.acquire(blocking=False):
            raise HTTPException(409, "An evaluation is already running.")
        try:
            report = evaluate(
                "live", client, request.limit, include_permissions=False, pricing=request.pricing
            )
            report["report_id"] = str(uuid4())
            save_evaluation(report, store.path.parent / "evaluations" / report["report_id"])
            return report
        finally:
            evaluation_lock.release()

    @app.get("/api/v1/admin/monitoring")
    def monitoring():
        return monitoring_status()

    @app.get("/health")
    def health() -> dict:
        return {"status": "ok", "version": __version__, "mode": "synthetic_local_demo"}

    @app.get("/api/v1/patients")
    def patients(source: Literal["fixtures", "hapi"] = "fixtures") -> list[dict]:
        if source == "hapi":
            try:
                return [
                    {
                        "id": p["id"],
                        "synthetic": True,
                        "source": "synthea",
                        "name": p.get("name", []),
                        "birthDate": p.get("birthDate"),
                    }
                    for p in fhir.patients()
                ]
            except FhirError as exc:
                raise HTTPException(exc.status, str(exc)) from exc
        return [
            {
                "id": patient_id,
                "synthetic": True,
                "source": "fixtures",
                "name": get_patient(patient_id)["entry"][0]["resource"].get("name", []),
                "birthDate": get_patient(patient_id)["entry"][0]["resource"].get("birthDate"),
            }
            for patient_id in PATIENTS
        ]

    @app.get("/api/v1/patients/{patient_id}/record")
    def patient_record(patient_id: str, source: Literal["hapi", "fixtures"] = "hapi") -> dict:
        """HAPI Patient, Condition and Observation evidence; not the complete medical chart."""
        if source == "fixtures":
            if patient_id not in PATIENTS:
                raise HTTPException(404, "Fixture patient not found.")
            return get_patient(patient_id)
        try:
            return fhir.record(patient_id)
        except FhirError as exc:
            raise HTTPException(exc.status, str(exc)) from exc

    @app.get("/api/v1/trials")
    def trials(source: Literal["all", "registry", "fixtures"] = "all") -> list[dict]:
        fixtures = [TRIAL, SYNTHEA_TRIAL] if source != "registry" else []
        return fixtures + (catalog.list() if source != "fixtures" else [])

    def load_study(trial_id: str, snapshot_id: str | None = None) -> dict:
        try:
            return catalog.snapshot(trial_id, snapshot_id)
        except KeyError as exc:
            raise HTTPException(404, str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(503, str(exc)) from exc

    def load_rule_set(rule_set_id: str) -> dict:
        try:
            return store.get_rule_set(rule_set_id)
        except KeyError as exc:
            raise HTTPException(404, str(exc)) from exc

    @app.get("/api/v1/trials/{trial_id}")
    def registry_trial(trial_id: str) -> dict:
        snapshot = load_study(trial_id)
        protocol = snapshot["study"]["protocolSection"]
        return {
            **catalog.summary(trial_id),
            "eligibility": protocol["eligibilityModule"],
            "locations_at_snapshot": protocol.get("contactsLocationsModule", {}).get(
                "locations", []
            ),
            "rule_sets": store.list_rule_sets(trial_id),
        }

    @app.get("/api/v1/trials/{trial_id}/snapshot")
    def registry_snapshot(trial_id: str, snapshot_id: str | None = None) -> dict:
        """Original registry JSON with retrieval metadata; reads locally saved data only."""
        return load_study(trial_id, snapshot_id)

    @app.post("/api/v1/trials/{trial_id}/rule-sets/draft", status_code=201)
    def draft_rules(trial_id: str) -> dict:
        snapshot = load_study(trial_id)
        try:
            return store.save_rule_set(validate_proposal(snapshot, draft_proposal(snapshot)))
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc

    @app.post("/api/v1/trials/{trial_id}/rule-sets", status_code=201)
    def propose_rules(trial_id: str, request: RuleProposal) -> dict:
        try:
            return store.save_rule_set(validate_proposal(load_study(trial_id), request))
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc

    @app.get("/api/v1/rule-sets/{rule_set_id}")
    def get_rule_set(rule_set_id: str) -> dict:
        return load_rule_set(rule_set_id)

    @app.post("/api/v1/rule-sets/{rule_set_id}/reviews", status_code=201)
    def review_rules(rule_set_id: str, request: RuleReview, http_request: Request) -> dict:
        rules = load_rule_set(rule_set_id)
        snapshot = load_study(rules["document"]["trial_id"])
        if rules["document"]["snapshot_id"] != snapshot["snapshot_id"]:
            raise HTTPException(
                409, "Study snapshot changed; create and review a new interpretation."
            )
        try:
            return store.review_rule_set(
                rule_set_id, request.model_dump(), actor=http_request.state.user
            )
        except ValueError as exc:
            raise HTTPException(409, str(exc)) from exc

    @app.post("/api/v1/screenings", status_code=201)
    def create_screening(request: ScreeningRequest) -> dict:
        if request.trial_id.startswith("NCT"):
            if (
                request.source != "hapi"
                or request.rule_set_id is None
                or "as_of" not in request.model_fields_set
            ):
                raise HTTPException(
                    422,
                    "Registry screening needs source=hapi, rule_set_id, and explicit as_of.",
                )
            snapshot = load_study(request.trial_id)
            rules = load_rule_set(request.rule_set_id)
            if (
                rules["status"] != "approved"
                or rules["document"]["trial_id"] != request.trial_id
                or rules["document"]["snapshot_id"] != snapshot["snapshot_id"]
            ):
                raise HTTPException(
                    409, "Approve an interpretation for this exact current study snapshot first."
                )
            try:
                bundle = fhir.record(request.patient_id)
            except FhirError as exc:
                raise HTTPException(exc.status, str(exc)) from exc
            result = screen_registry(bundle, snapshot, rules, request.as_of)
            return store.save_screening(
                result,
                bundle,
                {
                    "registry": snapshot,
                    "interpretation": rules,
                    "summary_at_screening": catalog.summary(request.trial_id),
                },
            )
        if request.source == "hapi":
            if request.trial_id != SYNTHEA_TRIAL["id"]:
                raise HTTPException(422, "Use DEMO-SYNTHEA-T2D-001 for HAPI records.")
            try:
                bundle = fhir.record(request.patient_id)
            except FhirError as exc:
                raise HTTPException(exc.status, str(exc)) from exc
            trial = SYNTHEA_TRIAL
        else:
            if request.patient_id not in PATIENTS or request.trial_id != TRIAL["id"]:
                raise HTTPException(404, "Demo patient or trial not found.")
            bundle, trial = get_patient(request.patient_id), TRIAL
        result = screen_patient(bundle, trial, request.as_of)
        result["data_source"] = request.source
        return store.save_screening(result, bundle, trial)

    @app.get("/api/v1/screenings")
    def screening_history(
        limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0)
    ) -> dict:
        return store.list_screenings(limit, offset)

    @app.get("/api/v1/screenings/{screening_id}")
    def get_screening(screening_id: str) -> dict:
        try:
            return store.get_screening(screening_id)
        except KeyError as exc:
            raise HTTPException(404, "Screening not found.") from exc

    @app.post("/api/v1/screenings/{screening_id}/reviews", status_code=201)
    def review(screening_id: str, request: ReviewRequest, http_request: Request) -> dict:
        try:
            return store.add_review(
                screening_id, request.model_dump(), actor=http_request.state.user
            )
        except KeyError as exc:
            raise HTTPException(404, "Screening not found.") from exc
        except ValueError as exc:
            raise HTTPException(409, str(exc)) from exc

    @app.get("/api/v1/assistant/status")
    def assistant_status():
        return JSONResponse(
            {**active_assistant().status(), **settings.public()},
            headers={"Cache-Control": "no-store"},
        )

    def local_request(request: Request):
        # Browser mutations must originate from this loopback application, not another site.
        if request.url.hostname not in {"localhost", "127.0.0.1", "::1", "testserver"}:
            raise HTTPException(403, "Assistant configuration is available on localhost only.")
        origin = request.headers.get("origin")
        if origin and (
            urlsplit(origin).scheme != request.url.scheme
            or urlsplit(origin).netloc != request.headers.get("host")
        ):
            raise HTTPException(403, "Use the HealthOps dashboard on this same address.")
        if request.headers.get("x-healthops-request") != "1":
            raise HTTPException(403, "A HealthOps request header is required.")

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError):
        # Pydantic errors normally include submitted input; a key must never be echoed.
        return JSONResponse(
            status_code=422,
            content={
                "detail": [
                    {"loc": e["loc"], "msg": e["msg"], "type": e["type"]} for e in exc.errors()
                ]
            },
        )

    @app.post("/api/v1/assistant/settings")
    def save_assistant_settings(update: ProviderUpdate, request: Request):
        local_request(request)
        try:
            return JSONResponse(settings.update(update), headers={"Cache-Control": "no-store"})
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from None

    @app.post("/api/v1/screenings/{screening_id}/assistant")
    def ask_assistant(screening_id: str, request: AssistantRequest, http_request: Request) -> dict:
        current = active_assistant()
        if request.use_model and getattr(current.model, "provider", "ollama") in {
            "openai",
            "anthropic",
            "gemini",
        }:
            local_request(http_request)
        return current.answer(get_screening(screening_id), request)

    static = Path(__file__).parent / "static"
    if (static / "index.html").exists():
        app.mount("/assets", StaticFiles(directory=static / "assets"), name="dashboard-assets")

        @app.get("/", include_in_schema=False)
        def dashboard():
            return FileResponse(static / "index.html", headers={"Cache-Control": "no-cache"})

    return app
