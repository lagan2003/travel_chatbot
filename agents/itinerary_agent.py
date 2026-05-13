"""
Itinerary Planning Agent — generates day-by-day plans.
Builds a FullItinerary Pydantic model and stores it in state.
"""

import logging
from typing import List
from pydantic import BaseModel
from models.state import AgentState
from models.schemas import DailyPlan, FullItinerary
from services.llm import generate_structured_data
from prompts.system_prompts import ITINERARY_PLANNING_PROMPT

logger = logging.getLogger(__name__)


class ItineraryOutput(BaseModel):
    daily_plans: List[DailyPlan]


def itinerary_agent(state: AgentState) -> dict:
    """Generate a detailed, day-by-day itinerary.

    If the critic looped us back with a `revision_hint`, append it to the
    prompt so the next generation respects the critic's feedback.
    """
    intent = state.get("intent")
    weather = state.get("weather", [])
    flights = state.get("flights", [])
    hotels = state.get("hotels", [])

    if not intent:
        logger.warning("No intent — cannot build itinerary.")
        return {}

    daily_budget = state.get("daily_activity_budget", 100.0)
    revision_hint = (state.get("revision_hint") or "").strip()

    prompt = ITINERARY_PLANNING_PROMPT.format(
        duration=intent.duration_days,
        destination=intent.destination,
        preferences=", ".join(intent.preferences) if intent.preferences else "general sightseeing",
        daily_budget=daily_budget,
        weather=[w.model_dump() for w in weather] if weather else "No forecast available",
    )

    if revision_hint:
        prompt += (
            "\n\n## Revision instructions from the critic agent\n"
            f"{revision_hint}\n"
            "Apply this feedback strictly in the new plan."
        )
        logger.info(f"Itinerary agent: applying revision hint -> {revision_hint!r}")

    output = generate_structured_data(prompt, ItineraryOutput)
    daily_plans = output.daily_plans if output else []

    # Compute total estimated cost (handle empty lists safely)
    flight_cost = sum(f.price for f in flights) if flights else 0.0
    hotel_cost = sum(h.price_per_night * intent.duration_days for h in hotels) if hotels else 0.0
    activity_cost = sum(act.estimated_cost for dp in daily_plans for act in dp.activities) if daily_plans else 0.0
    total = flight_cost + hotel_cost + activity_cost

    itinerary = FullItinerary(
        intent=intent,
        flights=flights,
        hotels=hotels,
        weather=weather,
        daily_plans=daily_plans,
        total_estimated_cost=total,
    )

    logger.info(f"Itinerary built: {len(daily_plans)} days, total=${total:.2f}")
    return {"itinerary": itinerary}
