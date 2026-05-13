"""
Itinerary Planning Agent — generates day-by-day plans.

Strategy:
  1. Try the LLM (via `generate_structured_data`, which itself has a JSON-fallback).
  2. If the LLM yields zero days, synthesize a plausible itinerary deterministically
     so the user always gets a full day-by-day plan.
"""

from __future__ import annotations

import logging
import random
from datetime import datetime, timedelta
from typing import List

from pydantic import BaseModel

from models.state import AgentState
from models.schemas import Activity, DailyPlan, FullItinerary
from services.llm import generate_structured_data
from prompts.system_prompts import ITINERARY_PLANNING_PROMPT

logger = logging.getLogger(__name__)


class ItineraryOutput(BaseModel):
    daily_plans: List[DailyPlan]


# Generic activity templates that work for almost any destination.
_ACTIVITY_TEMPLATES = [
    ("Morning city walk in {dest}",
     "Stroll through the central streets, soak in the atmosphere, and grab a coffee.", 0.5, 2.0),
    ("Visit a top landmark in {dest}",
     "Check out one of the must-see attractions and learn about the local history.", 0.25, 2.0),
    ("Local lunch at a popular eatery",
     "Try a signature regional dish at a recommended restaurant.", 0.4, 1.5),
    ("Museum or cultural site visit",
     "Spend the afternoon at a museum, gallery, or heritage site in {dest}.", 0.3, 2.5),
    ("Sunset viewpoint",
     "Catch the sunset from a scenic spot — bring a camera.", 0.1, 1.0),
    ("Evening neighborhood dinner",
     "Dinner at a buzzing local restaurant; ideal for soaking in the night atmosphere.", 0.5, 2.0),
    ("Shopping at the local market",
     "Pick up souvenirs, handicrafts, or fresh produce at the central market.", 0.3, 1.5),
    ("Day trip to a nearby attraction",
     "Take a half-day trip to a notable spot just outside the city.", 0.6, 4.0),
    ("Park or nature stroll",
     "Relax in a major park or natural area; perfect after a busy morning.", 0.1, 1.5),
    ("Evening walking tour",
     "Join a free or paid walking tour to learn the local stories.", 0.2, 2.0),
]


def _synth_daily_plans(intent, daily_budget: float) -> List[DailyPlan]:
    """Build a plausible N-day itinerary deterministically from the intent."""
    duration = max(1, int(intent.duration_days or 1))

    try:
        start = datetime.strptime(intent.start_date, "%Y-%m-%d") if intent.start_date else datetime.now()
    except ValueError:
        start = datetime.now()

    # Deterministic seed per route so repeated calls return the same plan.
    rng = random.Random(f"{intent.source}|{intent.destination}|{duration}")
    plans: List[DailyPlan] = []
    budget = max(daily_budget, 30.0)

    for d in range(duration):
        # Pick 3 activities, mixed for variety
        picks = rng.sample(_ACTIVITY_TEMPLATES, k=min(3, len(_ACTIVITY_TEMPLATES)))
        activities: List[Activity] = []
        for tmpl_name, tmpl_desc, cost_frac, dur in picks:
            activities.append(Activity(
                name=tmpl_name.format(dest=intent.destination),
                description=tmpl_desc.format(dest=intent.destination),
                estimated_cost=round(budget * cost_frac, 2),
                duration_hours=dur,
            ))
        plans.append(DailyPlan(
            day=d + 1,
            date=(start + timedelta(days=d)).strftime("%Y-%m-%d"),
            activities=activities,
            daily_budget=round(budget, 2),
        ))
    return plans


def itinerary_agent(state: AgentState) -> dict:
    """Generate a detailed, day-by-day itinerary."""
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
    daily_plans = output.daily_plans if output and output.daily_plans else []

    # Deterministic fallback — synthesize if LLM returned nothing OR a wrong day count
    expected = int(intent.duration_days or 0)
    if not daily_plans or (expected and len(daily_plans) != expected):
        logger.warning(
            f"LLM produced {len(daily_plans)} days; expected {expected}. "
            "Synthesizing deterministic day-by-day plan."
        )
        daily_plans = _synth_daily_plans(intent, daily_budget)

    # Compute total estimated cost
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
