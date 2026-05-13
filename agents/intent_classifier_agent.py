"""
Intent Classifier Agent.

First node after START. Decides which downstream subgraph the orchestrator
should dispatch to:

    ITINERARY    -> full plan pipeline (intent -> flights/hotels/weather -> ...)
    FLIGHT_ONLY  -> live flight NLP suggestion
    HOTEL_ONLY   -> live hotel NLP suggestion
    CHAT         -> chat-style fallback (handled outside the planning graph)

Uses LLM structured output, then falls back to keyword heuristics so the
graph still routes deterministically when the LLM call fails.
"""

from __future__ import annotations

import logging
import re

from models.state import AgentState
from models.schemas import IntentClassification
from services.llm import generate_structured_data
from prompts.system_prompts import INTENT_CLASSIFICATION_PROMPT

logger = logging.getLogger(__name__)


_FLIGHT_KW = re.compile(
    r"\b(flight|flights|airfare|airline|fly|cheapest flight|red[- ]?eye|non[- ]?stop|direct flight)\b",
    re.IGNORECASE,
)
_HOTEL_KW = re.compile(
    r"\b(hotel|hotels|stay|resort|motel|airbnb|accommodation|lodging|room)\b",
    re.IGNORECASE,
)
_ITINERARY_KW = re.compile(
    r"\b(itinerary|plan|trip|vacation|holiday|tour|days?|nights?|week|weekend)\b",
    re.IGNORECASE,
)


def _keyword_route(query: str) -> IntentClassification:
    q = query or ""
    has_flight = bool(_FLIGHT_KW.search(q))
    has_hotel = bool(_HOTEL_KW.search(q))
    has_iter = bool(_ITINERARY_KW.search(q))

    if has_iter or (has_flight and has_hotel):
        label = "ITINERARY"
    elif has_flight:
        label = "FLIGHT_ONLY"
    elif has_hotel:
        label = "HOTEL_ONLY"
    elif q.strip():
        label = "ITINERARY"          # default: assume planning intent
    else:
        label = "CHAT"

    return IntentClassification(
        intent=label,
        confidence=0.55,
        needs_clarification=False,
        reasoning="keyword fallback",
    )


def intent_classifier_agent(state: AgentState) -> dict:
    query = state.get("query", "")
    explicit_src = state.get("explicit_source") or ""
    explicit_dest = state.get("explicit_destination") or ""

    # If the UI sent explicit source+destination, the user wants a full plan.
    if explicit_src and explicit_dest:
        cls = IntentClassification(
            intent="ITINERARY",
            confidence=0.95,
            needs_clarification=False,
            reasoning="explicit source+destination supplied by UI",
        )
        logger.info("Intent classifier: ITINERARY (explicit src+dest).")
        return {"classification": cls, "route": cls.intent}

    cls = generate_structured_data(
        INTENT_CLASSIFICATION_PROMPT.format(query=query),
        IntentClassification,
    )
    if cls is None:
        cls = _keyword_route(query)
        logger.info(f"Intent classifier (heuristic): {cls.intent} ({cls.reasoning})")
    else:
        logger.info(f"Intent classifier (LLM): {cls.intent} ({cls.reasoning!r}, "
                    f"conf={cls.confidence:.2f})")

    return {"classification": cls, "route": cls.intent}
