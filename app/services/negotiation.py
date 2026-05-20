from __future__ import annotations

from datetime import datetime, timezone
from math import ceil

from app.models import OfferEvaluationRequest, OfferEvaluationResult
from app.services.load_service import get_load


def round_to_25(value: float) -> float:
    return float(int(ceil(value / 25.0) * 25))


def max_acceptable_rate(loadboard_rate: float, pickup_datetime: datetime, notes: str) -> tuple[float, str]:
    now = datetime.now(tz=pickup_datetime.tzinfo or timezone.utc)
    hours_to_pickup = max((pickup_datetime - now).total_seconds() / 3600, 0)
    notes_lower = notes.lower()
    if "high priority" in notes_lower or "urgent" in notes_lower or hours_to_pickup <= 12:
        multiplier = 1.08
        rationale = "high-priority or near-pickup load: max rate set to 108% of loadboard"
    elif hours_to_pickup <= 36:
        multiplier = 1.05
        rationale = "near-pickup load: max rate set to 105% of loadboard"
    else:
        multiplier = 1.03
        rationale = "standard pickup window: max rate set to 103% of loadboard"
    return round_to_25(loadboard_rate * multiplier), rationale


def evaluate_offer(request: OfferEvaluationRequest) -> OfferEvaluationResult:
    load = get_load(request.load_id)
    if not load:
        return OfferEvaluationResult(
            load_id=request.load_id,
            mc_number=request.mc_number,
            loadboard_rate=0,
            proposed_rate=request.proposed_rate,
            negotiation_round=request.negotiation_round,
            max_acceptable_rate=0,
            decision="human_review",
            counter_rate=None,
            transfer_required=False,
            message_for_agent="I could not find that load in the system, so I need to have a sales rep follow up instead of quoting a rate.",
            pricing_rationale="Load id not found.",
        )

    max_rate, rationale = max_acceptable_rate(load.loadboard_rate, load.pickup_datetime, load.notes)
    proposed = round_to_25(request.proposed_rate)

    if proposed <= max_rate:
        return OfferEvaluationResult(
            load_id=load.load_id,
            mc_number=request.mc_number,
            loadboard_rate=load.loadboard_rate,
            proposed_rate=proposed,
            negotiation_round=request.negotiation_round,
            max_acceptable_rate=max_rate,
            decision="accept",
            counter_rate=None,
            transfer_required=True,
            message_for_agent=(
                f"Accept the carrier's ${proposed:,.0f} offer. Say: 'That works. I have you at ${proposed:,.0f}. "
                "Transfer was successful and now you can wrap up the conversation.'"
            ),
            pricing_rationale=f"Proposed rate is within max acceptable rate. {rationale}.",
        )

    if request.negotiation_round >= 3:
        return OfferEvaluationResult(
            load_id=load.load_id,
            mc_number=request.mc_number,
            loadboard_rate=load.loadboard_rate,
            proposed_rate=proposed,
            negotiation_round=request.negotiation_round,
            max_acceptable_rate=max_rate,
            decision="reject",
            counter_rate=max_rate,
            transfer_required=False,
            message_for_agent=(
                f"Do not continue negotiating automatically. Say: 'The most I can do on this load is ${max_rate:,.0f}. "
                "Since that does not work, I will note your offer and have the team follow up if anything changes.'"
            ),
            pricing_rationale=f"Carrier remained above max rate after three negotiation rounds. {rationale}.",
        )

    # Structured concession schedule: start close to the board rate, then move toward max.
    progress = request.negotiation_round / 3.0
    counter = round_to_25(load.loadboard_rate + (max_rate - load.loadboard_rate) * progress)
    counter = min(counter, max_rate)
    return OfferEvaluationResult(
        load_id=load.load_id,
        mc_number=request.mc_number,
        loadboard_rate=load.loadboard_rate,
        proposed_rate=proposed,
        negotiation_round=request.negotiation_round,
        max_acceptable_rate=max_rate,
        decision="counter",
        counter_rate=counter,
        transfer_required=False,
        message_for_agent=(
            f"Counter at ${counter:,.0f}. Say: 'I cannot get to ${proposed:,.0f}, but I can offer ${counter:,.0f}. "
            "Would you be willing to run it at that rate?'"
        ),
        pricing_rationale=f"Proposed rate is above max acceptable rate; concession schedule used. {rationale}.",
    )
