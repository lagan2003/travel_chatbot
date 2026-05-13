"""
Budget Optimization Agent — runs after the three parallel search branches merge.
Picks the best flight + hotel that fit within ~60 % of the user's budget,
leaving ~40 % for daily activities and meals.
"""

import logging
from pydantic import BaseModel, Field
from models.state import AgentState
from services.llm import generate_structured_data
from prompts.system_prompts import BUDGET_OPTIMIZATION_PROMPT

logger = logging.getLogger(__name__)


class BudgetOptimizationOutput(BaseModel):
    chosen_flight_index: int = Field(description="Index of the chosen flight in the list", default=0)
    chosen_hotel_index: int = Field(description="Index of the chosen hotel in the list", default=0)
    daily_budget_remaining: float = Field(description="Remaining budget per day for activities/meals", default=100.0)


def budget_agent(state: AgentState) -> dict:
    """Optimize budget: pick best flight + hotel and compute remaining daily budget."""
    intent = state.get("intent")
    flights = state.get("flights", [])
    hotels = state.get("hotels", [])

    if not intent or not flights or not hotels:
        logger.warning("Missing data for budget optimization — passing through.")
        return {}  # return empty update, don't clobber state

    original_budget = state.get("original_budget", intent.budget)

    # Prepare concise data for the LLM
    flight_data = [{"index": i, "price": f.price, "airline": f.airline} for i, f in enumerate(flights)]
    hotel_data = [{"index": i, "price_per_night": h.price_per_night, "name": h.name} for i, h in enumerate(hotels)]

    prompt = (
        BUDGET_OPTIMIZATION_PROMPT.format(budget=original_budget)
        + f"\nFlights: {flight_data}"
        + f"\nHotels: {hotel_data}"
        + f"\nDuration: {intent.duration_days} days"
    )

    output = generate_structured_data(prompt, BudgetOptimizationOutput)

    if not output:
        logger.warning("LLM budget optimization failed — using cheapest options.")
        output = BudgetOptimizationOutput(
            chosen_flight_index=0,
            chosen_hotel_index=0,
            daily_budget_remaining=100.0,
        )

    idx_f = output.chosen_flight_index if output.chosen_flight_index < len(flights) else 0
    idx_h = output.chosen_hotel_index if output.chosen_hotel_index < len(hotels) else 0

    chosen_flight = flights[idx_f]
    chosen_hotel = hotels[idx_h]

    # Calculate remaining daily budget deterministically as a sanity fallback
    flight_cost = chosen_flight.price
    hotel_cost = chosen_hotel.price_per_night * intent.duration_days
    remaining = max(original_budget - flight_cost - hotel_cost, 0)
    daily_budget = remaining / max(intent.duration_days, 1)
    # Prefer LLM's estimate only if it's reasonable
    if output.daily_budget_remaining > 0 and output.daily_budget_remaining < remaining:
        daily_budget = output.daily_budget_remaining

    logger.info(f"Budget: flight=${flight_cost}, hotel=${hotel_cost}, "
                f"daily_activity=${daily_budget:.2f}")

    return {
        "flights": [chosen_flight],
        "hotels": [chosen_hotel],
        "daily_activity_budget": daily_budget,
    }
