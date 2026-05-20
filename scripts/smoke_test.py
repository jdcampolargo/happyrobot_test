#!/usr/bin/env python3
"""Minimal stdlib smoke test for a running local service."""
from __future__ import annotations

import json
import os
import sys
import urllib.request

BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")
API_KEY = os.getenv("API_KEY", "local-dev-key")


def request(method: str, path: str, payload: dict | None = None) -> dict:
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(
        BASE_URL + path,
        data=data,
        method=method,
        headers={"X-API-Key": API_KEY, "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode("utf-8"))


def main() -> int:
    print("health", request("GET", "/health"))
    print("verify", request("POST", "/api/carriers/verify", {"mc_number": "123456"}))
    print("loads", request("POST", "/api/loads/search", {"origin": "Chicago", "destination": "Dallas", "equipment_type": "dry van"}))
    print("offer", request("POST", "/api/offers/evaluate", {"load_id": "ACME-1001", "mc_number": "123456", "proposed_rate": 2700, "negotiation_round": 1}))
    print("metrics", request("GET", "/api/metrics"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
