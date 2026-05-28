from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field, field_validator


class Load(BaseModel):
    load_id: str
    origin: str
    destination: str
    pickup_datetime: datetime
    delivery_datetime: datetime
    equipment_type: str
    loadboard_rate: float = Field(gt=0)
    notes: str = ""
    weight: int = Field(ge=0)
    commodity_type: str
    num_of_pieces: int = Field(ge=0)
    miles: int = Field(ge=0)
    dimensions: str


class LoadSearchRequest(BaseModel):
    origin: Optional[str] = None
    destination: Optional[str] = None
    pickup_date: Optional[str] = None
    equipment_type: Optional[str] = None
    max_results: int = Field(default=3, ge=1, le=10)


class CarrierVerificationRequest(BaseModel):
    mc_number: str = Field(description="Motor carrier docket number. Accepts values like MC-123456 or 123456.")

    @field_validator("mc_number")
    @classmethod
    def normalize_mc_number(cls, value: str) -> str:
        digits = "".join(ch for ch in value if ch.isdigit())
        if not digits:
            raise ValueError("mc_number must contain at least one digit")
        return digits


class CarrierVerificationResult(BaseModel):
    mc_number: str
    dot_number: Optional[str] = None
    legal_name: Optional[str] = None
    dba_name: Optional[str] = None
    allow_to_operate: Optional[bool] = None
    out_of_service: Optional[bool] = None
    safety_rating: Optional[str] = None
    power_units: Optional[int] = None
    drivers: Optional[int] = None
    eligible: bool
    source: Literal["fmcsa", "mock", "fallback"]
    reason: str
    raw: dict[str, Any] = Field(default_factory=dict)


class OfferEvaluationRequest(BaseModel):
    load_id: str
    mc_number: str
    proposed_rate: float = Field(gt=0)
    negotiation_round: int = Field(default=1, ge=1, le=3)
    carrier_name: Optional[str] = None


class OfferEvaluationResult(BaseModel):
    load_id: str
    mc_number: str
    loadboard_rate: float
    proposed_rate: float
    negotiation_round: int
    max_acceptable_rate: float
    decision: Literal["accept", "counter", "reject", "human_review"]
    counter_rate: Optional[float] = None
    transfer_required: bool = False
    message_for_agent: str
    pricing_rationale: str


Outcome = Literal[
    "booked_transfer_mocked",
    "quoted_too_high",
    "carrier_ineligible",
    "no_matching_load",
    "not_interested",
    "follow_up_required",
    "abandoned",
]
Sentiment = Literal["positive", "neutral", "negative", "mixed"]


class CallLogRequest(BaseModel):
    run_id: str = Field(description="Workflow run id, or a locally generated id for testing")
    caller_phone: Optional[str] = None
    mc_number: Optional[str] = None
    carrier_name: Optional[str] = None
    load_id: Optional[str] = None
    outcome: Outcome
    sentiment: Sentiment
    initial_offer: Optional[float] = None
    final_offer: Optional[float] = None
    loadboard_rate: Optional[float] = None
    negotiation_rounds: int = Field(default=0, ge=0, le=3)
    extracted_data: dict[str, Any] = Field(default_factory=dict)
    transcript: Optional[str] = None
    duration_seconds: Optional[int] = Field(default=None, ge=0)


class CallLogResult(BaseModel):
    id: int
    run_id: str
    created_at: datetime


class MetricsResponse(BaseModel):
    total_calls: int
    booked_calls: int
    transfer_rate: float
    qualified_carrier_rate: float
    avg_final_offer: Optional[float]
    avg_rate_vs_loadboard_pct: Optional[float]
    avg_negotiation_rounds: Optional[float]
    outcome_counts: dict[str, int]
    sentiment_counts: dict[str, int]
    lane_summary: list[dict[str, Any]]
    recent_calls: list[dict[str, Any]]
