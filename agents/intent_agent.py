"""
Intent Extraction Agent -- first node in the LangGraph pipeline.
Uses the LLM to parse a natural-language travel query into structured fields.

If structured tool-calling fails (Groq schema validation error), we fall back
to a plain-text LLM call and manually parse the JSON.
"""

import json
import logging
from datetime import datetime, timedelta
from models.state import AgentState
from models.schemas import IntentExtraction
from services.llm import get_llm, generate_structured_data
from prompts.system_prompts import INTENT_EXTRACTION_PROMPT

logger = logging.getLogger(__name__)


# Fallback prompt that asks for raw JSON instead of using tool calling
_FALLBACK_PROMPT = """You are an expert travel agent. Extract the travel intent from the user query below.
Return ONLY a valid JSON object with these keys (no extra text):
{{
  "destination": "string",
  "source": "string",
  "start_date": "YYYY-MM-DD or empty string",
  "end_date": "YYYY-MM-DD or empty string",
  "budget": 0.0,
  "duration_days": 5,
  "preferences": ["list", "of", "strings"]
}}

User Query: {query}
"""


def _parse_intent_from_text(text: str) -> IntentExtraction | None:
    """Try to extract JSON from a plain-text LLM response."""
    try:
        # Strip markdown fences if present
        cleaned = text.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[1]
        if cleaned.endswith("```"):
            cleaned = cleaned.rsplit("```", 1)[0]
        cleaned = cleaned.strip()

        data = json.loads(cleaned)
        return IntentExtraction(**data)
    except Exception as e:
        logger.warning(f"JSON parse fallback also failed: {e}")
        return None


def intent_agent(state: AgentState) -> dict:
    """Extract destination, source, dates, budget, duration, and preferences."""
    query = state["query"]

    # Grab explicit values the frontend sent (if any)
    explicit_src = state.get("explicit_source") or ""
    explicit_dest = state.get("explicit_destination") or ""

    # Attempt 1: structured output via tool calling
    prompt = INTENT_EXTRACTION_PROMPT.format(query=query)
    intent = generate_structured_data(prompt, IntentExtraction)

    # Attempt 2: plain-text JSON fallback (avoids Groq schema validation errors)
    if intent is None:
        logger.info("Structured extraction failed -- trying plain-text JSON fallback.")
        llm = get_llm()
        try:
            resp = llm.invoke(_FALLBACK_PROMPT.format(query=query))
            intent = _parse_intent_from_text(resp.content)
        except Exception as e:
            logger.warning(f"Fallback LLM call failed: {e}")

    # Attempt 3: hardcoded defaults
    if intent is None:
        logger.warning("All intent extraction attempts failed -- using hardcoded defaults.")
        intent = IntentExtraction(
            destination=explicit_dest or "Paris",
            source=explicit_src or "New York",
            duration_days=5,
            budget=3000.0,
            preferences=["sightseeing"],
        )

    # ── Override source/destination with explicit UI values ──
    # This is the critical fix: the UI sends explicit cities, so
    # we trust those over whatever the LLM may have extracted.
    if explicit_src:
        intent.source = explicit_src
    if explicit_dest:
        intent.destination = explicit_dest

    # Back-fill dates if the LLM left them blank
    if not intent.start_date:
        intent.start_date = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
    if not intent.end_date and intent.duration_days:
        start = datetime.strptime(intent.start_date, "%Y-%m-%d")
        intent.end_date = (start + timedelta(days=intent.duration_days)).strftime("%Y-%m-%d")
    if intent.duration_days <= 0:
        intent.duration_days = 5

    logger.info(
        f"Intent extracted: {intent.destination} from {intent.source}, "
        f"{intent.duration_days}d, ${intent.budget}"
    )

    return {"intent": intent, "original_budget": intent.budget}
