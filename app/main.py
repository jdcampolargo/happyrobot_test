from __future__ import annotations

import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.auth import require_api_key
from app.models import (
    CallLogRequest,
    CallLogResult,
    CarrierVerificationRequest,
    CarrierVerificationResult,
    LoadSearchRequest,
    MetricsResponse,
    OfferEvaluationRequest,
    OfferEvaluationResult,
)
from app.services.carrier_service import verify_carrier
from app.services.load_service import load_all, load_lookup, search_loads
from app.services.metrics_service import get_metrics, log_call
from app.services.negotiation import evaluate_offer
from app.storage import init_db, seed_demo_calls


BASE_DIR = Path(__file__).resolve().parents[1]
load_dotenv(BASE_DIR / ".env")

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    seed_demo_calls(load_lookup())
    yield


app = FastAPI(
    title="Inbound Carrier Sales API",
    version="1.0.0",
    description="Secured API and custom dashboard for a HappyRobot inbound carrier sales proof of concept.",
    lifespan=lifespan,
)
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=BASE_DIR / "templates")


@app.get("/", include_in_schema=False, dependencies=[Depends(require_api_key)])
def root(request: Request) -> RedirectResponse:
    api_key = request.query_params.get("api_key")
    suffix = f"?api_key={api_key}" if api_key else ""
    return RedirectResponse(url=f"/dashboard{suffix}")


@app.get("/health", dependencies=[Depends(require_api_key)])
def health() -> dict[str, str]:
    return {"status": "ok", "environment": os.getenv("ENVIRONMENT", "development")}


@app.post("/api/carriers/verify", response_model=CarrierVerificationResult, dependencies=[Depends(require_api_key)])
async def carrier_verify(payload: CarrierVerificationRequest) -> CarrierVerificationResult:
    return await verify_carrier(payload.mc_number)


@app.post("/api/loads/search", dependencies=[Depends(require_api_key)])
def loads_search(payload: LoadSearchRequest) -> dict[str, Any]:
    results = search_loads(payload)
    return {"count": len(results), "loads": results}


@app.get("/api/loads", dependencies=[Depends(require_api_key)])
def loads_all() -> dict[str, Any]:
    loads = [load.model_dump(mode="json") for load in load_all()]
    return {"count": len(loads), "loads": loads}


@app.post("/api/offers/evaluate", response_model=OfferEvaluationResult, dependencies=[Depends(require_api_key)])
def offers_evaluate(payload: OfferEvaluationRequest) -> OfferEvaluationResult:
    return evaluate_offer(payload)


@app.post("/api/calls/log", response_model=CallLogResult, dependencies=[Depends(require_api_key)])
def calls_log(payload: CallLogRequest) -> CallLogResult:
    return log_call(payload)


@app.get("/api/metrics", response_model=MetricsResponse, dependencies=[Depends(require_api_key)])
def metrics() -> MetricsResponse:
    return get_metrics()


@app.get("/dashboard", response_class=HTMLResponse, dependencies=[Depends(require_api_key)])
def dashboard(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "broker_name": os.getenv("BROKER_NAME", "Acme Logistics"),
            "environment": os.getenv("ENVIRONMENT", "development"),
        },
    )
