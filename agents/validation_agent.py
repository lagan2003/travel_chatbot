"""
Validation Agent — audits the itinerary for budget overruns and date conflicts.
"""

import logging
from pydantic import BaseModel, Field
from typing import List
from models.state import AgentState
from services.llm import generate_structured_data
from prompts.system_prompts import VALIDATION_PROMPT

logger = logging.getLogger(__name__)


class ValidationOutput(BaseModel):
    errors: List[str] = Field(description="List of validation errors found. Empty if none.", default_factory=list)
    is_valid: bool = Field(description="True if the itinerary is valid and within budget", default=True)


def validation_agent(state: AgentState) -> dict:
    """Validate the complete plan against constraints."""
    itinerary = state.get("itinerary")
    original_budget = state.get("original_budget", 0)

    if not itinerary:
        return {"validation_errors": ["Missing itinerary — nothing to validate."]}

    prompt = (
        VALIDATION_PROMPT.format(budget=original_budget)
        + f"\nItinerary Total Cost: ${itinerary.total_estimated_cost:.2f}"
        + f"\nUser Budget: ${original_budget:.2f}"
    )

    output = generate_structured_data(prompt, ValidationOutput)
    errors = output.errors if output else ["Validation LLM call failed."]

    if errors:
        logger.warning(f"Validation found {len(errors)} issue(s).")
    else:
        logger.info("Validation passed — no issues found.")

    return {"validation_errors": errors}
