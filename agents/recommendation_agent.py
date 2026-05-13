"""
Recommendation Agent — suggests hidden gems and local experiences.
Stores recommendations in state so the Formatter can include them.
"""

import logging
from pydantic import BaseModel, Field
from typing import List
from models.state import AgentState
from services.llm import generate_structured_data
from prompts.system_prompts import RECOMMENDATION_PROMPT

logger = logging.getLogger(__name__)


class RecommendationOutput(BaseModel):
    recommendations: List[str] = Field(description="List of extra recommendations")


def recommendation_agent(state: AgentState) -> dict:
    """Generate destination-specific hidden-gem recommendations."""
    intent = state.get("intent")
    if not intent:
        return {}

    prompt = RECOMMENDATION_PROMPT.format(
        destination=intent.destination,
        preferences=", ".join(intent.preferences) if intent.preferences else "general",
    )

    output = generate_structured_data(prompt, RecommendationOutput)
    recs = output.recommendations if output else []

    logger.info(f"Generated {len(recs)} recommendations.")
    return {"recommendations": recs}
