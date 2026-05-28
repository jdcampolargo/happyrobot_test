from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import httpx

from app.models import CarrierVerificationResult


BASE_DIR = Path(__file__).resolve().parents[2]
MOCK_CARRIERS_PATH = BASE_DIR / "data" / "carriers_mock.json"
FMCSA_BASE_URL = "https://mobile.fmcsa.dot.gov/qc/services"


def _mock_carriers() -> dict[str, dict[str, Any]]:
    with MOCK_CARRIERS_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


def _as_bool_yn(value: Any) -> bool | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        value = value.strip().upper()
        if value in {"Y", "YES", "TRUE", "1"}:
            return True
        if value in {"N", "NO", "FALSE", "0"}:
            return False
    return None


def _carrier_payload_from_fmcsa(raw: dict[str, Any]) -> dict[str, Any]:
    # FMCSA QCMobile may return {'content': {'carrier': {...}}} or
    # {'content': [{'carrier': {...}}]} depending on the lookup route.
    content = raw.get("content")
    if isinstance(content, list):
        first = content[0] if content else {}
        if isinstance(first, dict):
            carrier = first.get("carrier")
            return carrier if isinstance(carrier, dict) else first
        return {}
    if isinstance(content, dict):
        carrier = content.get("carrier")
        return carrier if isinstance(carrier, dict) else content
    carrier = raw.get("carrier")
    return carrier if isinstance(carrier, dict) else {}


def _build_result(mc_number: str, payload: dict[str, Any], source: str, raw: dict[str, Any] | None = None) -> CarrierVerificationResult:
    allow = _as_bool_yn(
        payload.get("allowedToOperate", payload.get("allowToOperate", payload.get("allow_to_operate")))
    )
    out = _as_bool_yn(payload.get("outOfService", payload.get("out_of_service")))
    if out is None and payload.get("oosDate"):
        out = True
    eligible = bool(payload.get("eligible", allow is True and out is not True))
    if allow is False:
        eligible = False
    if out is True:
        eligible = False

    safety_rating = payload.get("safetyRating") or payload.get("safety_rating")
    legal_name = payload.get("legalName") or payload.get("legal_name")
    dba_name = payload.get("dbaName") or payload.get("dba_name")
    dot_number = payload.get("dotNumber") or payload.get("dot_number")

    if not payload:
        eligible = False
        reason = "No carrier record was found. Route to manual carrier onboarding before discussing rates."
    elif eligible:
        reason = payload.get("reason") or "Carrier is allowed to operate and is not marked out of service."
    else:
        reason = payload.get("reason") or "Carrier failed eligibility checks. Do not tender the load automatically."

    def as_int(v: Any) -> int | None:
        try:
            return int(v) if v not in (None, "") else None
        except (TypeError, ValueError):
            return None

    return CarrierVerificationResult(
        mc_number=mc_number,
        dot_number=str(dot_number) if dot_number not in (None, "") else None,
        legal_name=legal_name,
        dba_name=dba_name,
        allow_to_operate=allow,
        out_of_service=out,
        safety_rating=safety_rating,
        power_units=as_int(payload.get("powerUnits") or payload.get("totalPowerUnits") or payload.get("power_units")),
        drivers=as_int(payload.get("drivers") or payload.get("totalDrivers")),
        eligible=eligible,
        source=source,  # type: ignore[arg-type]
        reason=reason,
        raw=raw or payload,
    )


async def verify_carrier(mc_number: str) -> CarrierVerificationResult:
    mc_number = "".join(ch for ch in str(mc_number) if ch.isdigit())
    web_key = os.getenv("FMCSA_WEB_KEY")
    if web_key:
        url = f"{FMCSA_BASE_URL}/carriers/docket-number/{mc_number}/"
        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                response = await client.get(url, params={"webKey": web_key})
                response.raise_for_status()
                raw = response.json()
            payload = _carrier_payload_from_fmcsa(raw)
            if payload:
                return _build_result(mc_number, payload, source="fmcsa", raw=raw)
        except Exception as exc:  # pragma: no cover - network varies by environment
            # Keep the carrier-sales flow from failing hard when an external dependency is unavailable.
            fallback_payload = _mock_carriers().get(mc_number, {})
            result = _build_result(mc_number, fallback_payload, source="fallback")
            result.reason = f"FMCSA lookup failed; used demo fallback. External error: {type(exc).__name__}. {result.reason}"
            return result

    mock_payload = _mock_carriers().get(mc_number, {})
    return _build_result(mc_number, mock_payload, source="mock")
