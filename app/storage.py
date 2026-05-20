from __future__ import annotations

import json
import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator


BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"


def database_path() -> Path:
    return Path(os.getenv("DATABASE_PATH", str(DATA_DIR / "app.db")))


@contextmanager
def get_conn() -> Iterator[sqlite3.Connection]:
    db_path = database_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    with get_conn() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS calls (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                run_id TEXT NOT NULL UNIQUE,
                caller_phone TEXT,
                mc_number TEXT,
                carrier_name TEXT,
                load_id TEXT,
                origin TEXT,
                destination TEXT,
                outcome TEXT NOT NULL,
                sentiment TEXT NOT NULL,
                initial_offer REAL,
                final_offer REAL,
                loadboard_rate REAL,
                negotiation_rounds INTEGER NOT NULL DEFAULT 0,
                extracted_data TEXT NOT NULL DEFAULT '{}',
                transcript TEXT,
                duration_seconds INTEGER
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_calls_created_at ON calls(created_at)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_calls_outcome ON calls(outcome)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_calls_load_id ON calls(load_id)")


def seed_demo_calls(load_lookup: dict[str, dict[str, Any]]) -> None:
    samples = [
        {
            "run_id": "demo-001",
            "caller_phone": "+13125550101",
            "mc_number": "123456",
            "carrier_name": "B MARRON LOGISTICS LLC",
            "load_id": "ACME-1001",
            "outcome": "booked_transfer_mocked",
            "sentiment": "positive",
            "initial_offer": 2700,
            "final_offer": 2525,
            "negotiation_rounds": 2,
            "duration_seconds": 310,
        },
        {
            "run_id": "demo-002",
            "caller_phone": "+13125550102",
            "mc_number": "100008",
            "carrier_name": "BC ECOCHIPS LTD",
            "load_id": None,
            "outcome": "carrier_ineligible",
            "sentiment": "negative",
            "initial_offer": None,
            "final_offer": None,
            "negotiation_rounds": 0,
            "duration_seconds": 95,
        },
        {
            "run_id": "demo-003",
            "caller_phone": "+13125550103",
            "mc_number": "777888",
            "carrier_name": "Midwest Reefer Group LLC",
            "load_id": "ACME-1002",
            "outcome": "quoted_too_high",
            "sentiment": "neutral",
            "initial_offer": 3700,
            "final_offer": None,
            "negotiation_rounds": 3,
            "duration_seconds": 265,
        },
        {
            "run_id": "demo-004",
            "caller_phone": "+13125550104",
            "mc_number": "123456",
            "carrier_name": "B MARRON LOGISTICS LLC",
            "load_id": "ACME-1004",
            "outcome": "booked_transfer_mocked",
            "sentiment": "positive",
            "initial_offer": 1900,
            "final_offer": 1825,
            "negotiation_rounds": 1,
            "duration_seconds": 220,
        },
        {
            "run_id": "demo-005",
            "caller_phone": "+13125550105",
            "mc_number": "123456",
            "carrier_name": "B MARRON LOGISTICS LLC",
            "load_id": "ACME-1003",
            "outcome": "not_interested",
            "sentiment": "mixed",
            "initial_offer": None,
            "final_offer": None,
            "negotiation_rounds": 0,
            "duration_seconds": 140,
        },
    ]
    with get_conn() as conn:
        count = conn.execute("SELECT COUNT(*) AS c FROM calls").fetchone()["c"]
        if count:
            return
        for row in samples:
            load = load_lookup.get(row.get("load_id") or "")
            if load:
                row["origin"] = load["origin"]
                row["destination"] = load["destination"]
                row["loadboard_rate"] = load["loadboard_rate"]
            else:
                row["origin"] = None
                row["destination"] = None
                row["loadboard_rate"] = None
            row["extracted_data"] = json.dumps(
                {
                    "demo_seed": True,
                    "summary": f"Seeded call for {row['outcome']}",
                    "next_step": "Transfer mocked" if row["outcome"] == "booked_transfer_mocked" else "No transfer",
                }
            )
            conn.execute(
                """
                INSERT OR IGNORE INTO calls (
                    run_id, caller_phone, mc_number, carrier_name, load_id, origin, destination,
                    outcome, sentiment, initial_offer, final_offer, loadboard_rate,
                    negotiation_rounds, extracted_data, transcript, duration_seconds
                ) VALUES (
                    :run_id, :caller_phone, :mc_number, :carrier_name, :load_id, :origin, :destination,
                    :outcome, :sentiment, :initial_offer, :final_offer, :loadboard_rate,
                    :negotiation_rounds, :extracted_data, :transcript, :duration_seconds
                )
                """,
                {**row, "transcript": None},
            )
