from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from app.models import Load, LoadSearchRequest


BASE_DIR = Path(__file__).resolve().parents[2]
LOADS_PATH = BASE_DIR / "data" / "loads.json"


def load_all() -> list[Load]:
    with LOADS_PATH.open("r", encoding="utf-8") as f:
        raw = json.load(f)
    return [Load(**item) for item in raw]


def load_lookup() -> dict[str, dict[str, Any]]:
    return {load.load_id: load.model_dump(mode="json") for load in load_all()}


def get_load(load_id: str) -> Load | None:
    for load in load_all():
        if load.load_id.lower() == load_id.lower():
            return load
    return None


def _norm(value: str | None) -> str:
    if not value:
        return ""
    return " ".join(value.lower().replace(",", " ").split())


def _score_load(load: Load, request: LoadSearchRequest) -> tuple[int, list[str]]:
    score = 0
    reasons: list[str] = []
    if request.equipment_type:
        req = _norm(request.equipment_type)
        got = _norm(load.equipment_type)
        if req in got or got in req:
            score += 50
            reasons.append("equipment match")
        else:
            score -= 100
            reasons.append("equipment mismatch")
    if request.origin:
        req = _norm(request.origin)
        got = _norm(load.origin)
        if req in got or any(part in got for part in req.split() if len(part) > 2):
            score += 30
            reasons.append("origin match")
        else:
            score -= 10
    if request.destination:
        req = _norm(request.destination)
        got = _norm(load.destination)
        if req in got or any(part in got for part in req.split() if len(part) > 2):
            score += 30
            reasons.append("destination match")
        else:
            score -= 10
    if request.pickup_date:
        try:
            req_date = datetime.fromisoformat(request.pickup_date.replace("Z", "+00:00")).date()
            if load.pickup_datetime.date() == req_date:
                score += 20
                reasons.append("pickup date match")
            else:
                score -= 5
        except ValueError:
            # Keep search forgiving for voice-agent tool calls.
            reasons.append("pickup date ignored: not ISO formatted")
    if not any([request.origin, request.destination, request.equipment_type, request.pickup_date]):
        score += 1
        reasons.append("default top open load")
    return score, reasons


def search_loads(request: LoadSearchRequest) -> list[dict[str, Any]]:
    scored: list[tuple[int, Load, list[str]]] = []
    for load in load_all():
        score, reasons = _score_load(load, request)
        if score >= 0:
            scored.append((score, load, reasons))
    scored.sort(key=lambda item: (-item[0], item[1].pickup_datetime, item[1].loadboard_rate))
    result: list[dict[str, Any]] = []
    for score, load, reasons in scored[: request.max_results]:
        item = load.model_dump(mode="json")
        item["match_score"] = score
        item["match_reasons"] = reasons
        item["rate_per_mile"] = round(load.loadboard_rate / load.miles, 2) if load.miles else None
        result.append(item)
    return result
