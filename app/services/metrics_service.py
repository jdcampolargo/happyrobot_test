from __future__ import annotations

import json
from collections import Counter, defaultdict
from typing import Any

from app.models import CallLogRequest, CallLogResult, MetricsResponse
from app.services.load_service import get_load
from app.storage import get_conn


def log_call(payload: CallLogRequest) -> CallLogResult:
    load = get_load(payload.load_id) if payload.load_id else None
    origin = load.origin if load else None
    destination = load.destination if load else None
    loadboard_rate = payload.loadboard_rate if payload.loadboard_rate is not None else (load.loadboard_rate if load else None)
    with get_conn() as conn:
        cursor = conn.execute(
            """
            INSERT INTO calls (
                run_id, caller_phone, mc_number, carrier_name, load_id, origin, destination,
                outcome, sentiment, initial_offer, final_offer, loadboard_rate,
                negotiation_rounds, extracted_data, transcript, duration_seconds
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(run_id) DO UPDATE SET
                caller_phone=excluded.caller_phone,
                mc_number=excluded.mc_number,
                carrier_name=excluded.carrier_name,
                load_id=excluded.load_id,
                origin=excluded.origin,
                destination=excluded.destination,
                outcome=excluded.outcome,
                sentiment=excluded.sentiment,
                initial_offer=excluded.initial_offer,
                final_offer=excluded.final_offer,
                loadboard_rate=excluded.loadboard_rate,
                negotiation_rounds=excluded.negotiation_rounds,
                extracted_data=excluded.extracted_data,
                transcript=excluded.transcript,
                duration_seconds=excluded.duration_seconds
            """,
            (
                payload.run_id,
                payload.caller_phone,
                payload.mc_number,
                payload.carrier_name,
                payload.load_id,
                origin,
                destination,
                payload.outcome,
                payload.sentiment,
                payload.initial_offer,
                payload.final_offer,
                loadboard_rate,
                payload.negotiation_rounds,
                json.dumps(payload.extracted_data),
                payload.transcript,
                payload.duration_seconds,
            ),
        )
        row = conn.execute("SELECT id, run_id, created_at FROM calls WHERE run_id = ?", (payload.run_id,)).fetchone()
    return CallLogResult(id=row["id"], run_id=row["run_id"], created_at=row["created_at"])


def get_metrics() -> MetricsResponse:
    with get_conn() as conn:
        rows = [dict(row) for row in conn.execute("SELECT * FROM calls ORDER BY created_at DESC, id DESC").fetchall()]

    total = len(rows)
    if total == 0:
        return MetricsResponse(
            total_calls=0,
            booked_calls=0,
            transfer_rate=0,
            qualified_carrier_rate=0,
            avg_final_offer=None,
            avg_rate_vs_loadboard_pct=None,
            avg_negotiation_rounds=None,
            outcome_counts={},
            sentiment_counts={},
            lane_summary=[],
            recent_calls=[],
        )

    outcome_counts = Counter(row["outcome"] for row in rows)
    sentiment_counts = Counter(row["sentiment"] for row in rows)
    booked = outcome_counts.get("booked_transfer_mocked", 0)
    qualified_count = total - outcome_counts.get("carrier_ineligible", 0)
    final_rates = [row["final_offer"] for row in rows if row["final_offer"] is not None]
    rate_vs_board = [
        ((row["final_offer"] - row["loadboard_rate"]) / row["loadboard_rate"]) * 100
        for row in rows
        if row["final_offer"] is not None and row["loadboard_rate"]
    ]
    negotiation_rounds = [row["negotiation_rounds"] for row in rows if row["negotiation_rounds"] is not None]

    lane_data: dict[str, dict[str, Any]] = defaultdict(lambda: {"lane": "", "calls": 0, "booked": 0, "avg_final_offer": None, "_offers": []})
    for row in rows:
        if not row.get("origin") or not row.get("destination"):
            continue
        lane = f"{row['origin']} -> {row['destination']}"
        lane_data[lane]["lane"] = lane
        lane_data[lane]["calls"] += 1
        if row["outcome"] == "booked_transfer_mocked":
            lane_data[lane]["booked"] += 1
        if row["final_offer"] is not None:
            lane_data[lane]["_offers"].append(row["final_offer"])
    lane_summary: list[dict[str, Any]] = []
    for item in lane_data.values():
        offers = item.pop("_offers")
        item["avg_final_offer"] = round(sum(offers) / len(offers), 2) if offers else None
        item["conversion_rate"] = round(item["booked"] / item["calls"] * 100, 1) if item["calls"] else 0
        lane_summary.append(item)
    lane_summary.sort(key=lambda item: (-item["calls"], item["lane"]))

    recent_calls = []
    for row in rows[:10]:
        extracted = row.get("extracted_data")
        try:
            extracted_data = json.loads(extracted) if extracted else {}
        except json.JSONDecodeError:
            extracted_data = {}
        recent_calls.append(
            {
                "created_at": row["created_at"],
                "run_id": row["run_id"],
                "carrier_name": row["carrier_name"],
                "mc_number": row["mc_number"],
                "load_id": row["load_id"],
                "outcome": row["outcome"],
                "sentiment": row["sentiment"],
                "initial_offer": row["initial_offer"],
                "final_offer": row["final_offer"],
                "negotiation_rounds": row["negotiation_rounds"],
                "summary": extracted_data.get("summary"),
            }
        )

    return MetricsResponse(
        total_calls=total,
        booked_calls=booked,
        transfer_rate=round(booked / total * 100, 1),
        qualified_carrier_rate=round(qualified_count / total * 100, 1),
        avg_final_offer=round(sum(final_rates) / len(final_rates), 2) if final_rates else None,
        avg_rate_vs_loadboard_pct=round(sum(rate_vs_board) / len(rate_vs_board), 2) if rate_vs_board else None,
        avg_negotiation_rounds=round(sum(negotiation_rounds) / len(negotiation_rounds), 2) if negotiation_rounds else None,
        outcome_counts=dict(outcome_counts),
        sentiment_counts=dict(sentiment_counts),
        lane_summary=lane_summary,
        recent_calls=recent_calls,
    )
