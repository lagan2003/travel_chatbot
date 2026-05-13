"""
Validation Agent — audits the itinerary deterministically (with optional LLM
sanity check on top). Never produces an opaque "LLM call failed" message: if
the LLM is unavailable, the deterministic rules still cover budget overrun,
date alignment, missing flights/hotels, and day count mismatches.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import List

from pydantic import BaseModel, Field

from models.state import AgentState
from services.llm import generate_structured_data
from prompts.system_prompts import VALIDATION_PROMPT

logger = logging.getLogger(__name__)


class ValidationOutput(BaseModel):
    errors: List[str] = Field(default_factory=list)
    is_valid: bool = Field(default=True)


def _deterministic_checks(itinerary, budget: float) -> List[str]:
    """Run cheap rule-based checks that don't need the LLM."""
    issues: List[str] = []

    total = float(itinerary.total_estimated_cost or 0.0)
    if budget > 0 and total > budget * 1.02:
        issues.append(
            f"Itinerary total cost (${total:,.2f}) exceeds budget (${budget:,.2f})."
        )

    intent = itinerary.intent
    duration = int(intent.duration_days or 0)
    day_count = len(itinerary.daily_plans)
    if duration and day_count and day_count != duration:
        issues.append(f"Day count mismatch — got {day_count}, expected {duration}.")

    if not itinerary.flights:
        issues.append("No flight is selected in the itinerary.")
    if not itinerary.hotels:
        issues.append("No hotel is selected in the itinerary.")

    # Date alignment: start_date + duration_days should equal end_date
    if intent.start_date and intent.end_date:
        try:
            start = datetime.strptime(intent.start_date, "%Y-%m-%d")
            end = datetime.strptime(intent.end_date, "%Y-%m-%d")
            span = (end - start).days
            if duration and span and abs(span - duration) > 1:
                issues.append(
                    f"Date span ({span} days) doesn't match duration ({duration} days)."
                )
        except ValueError:
            issues.append("Trip dates are not in the expected YYYY-MM-DD format.")

    return issues


def validation_agent(state: AgentState) -> dict:
    itinerary = state.get("itinerary")
    original_budget = float(state.get("original_budget", 0) or 0)

    if not itinerary:
        return {"validation_errors": ["Missing itinerary — nothing to validate."]}

    # Always run deterministic checks first — these are the ground truth.
    issues = _deterministic_checks(itinerary, original_budget)

    # Optionally ask the LLM for extra sanity checks; ignore on failure.
    prompt = (
        VALIDATION_PROMPT.format(budget=original_budget)
        + f"\nItinerary Total Cost: ${itinerary.total_estimated_cost:.2f}"
        + f"\nUser Budget: ${original_budget:.2f}"
        + f"\nDays planned: {len(itinerary.daily_plans)} / requested {itinerary.intent.duration_days}"
    )
    output = generate_structured_data(prompt, ValidationOutput)
    if output and output.errors:
        for e in output.errors:
            if e and e not in issues:
                issues.append(e)

    if issues:
        logger.warning(f"Validation found {len(issues)} issue(s).")
    else:
        logger.info("Validation passed — no issues found.")

    return {"validation_errors": issues}
