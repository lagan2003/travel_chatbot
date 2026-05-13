"""
Orchestrator Agent.

The orchestrator is the *coordinator* of the multi-agent system. It does
NOT perform the work itself — instead it inspects the classification, prepares
the routing decision the LangGraph conditional edge will consume, and emits a
short trace line so the UI can show "which lane was taken".

In LangGraph terms this is a pass-through node whose only side effect is
deciding which downstream branch the graph will execute next.
"""

from __future__ import annotations

import logging
from models.state import AgentState

logger = logging.getLogger(__name__)


_VALID_ROUTES = {"ITINERARY", "FLIGHT_ONLY", "HOTEL_ONLY", "CHAT"}


def orchestrator_agent(state: AgentState) -> dict:
    cls = state.get("classification")
    route = (cls.intent if cls else state.get("route")) or "ITINERARY"
    if route not in _VALID_ROUTES:
        route = "ITINERARY"

    if cls and cls.needs_clarification:
        logger.info(
            "Orchestrator: classifier requested clarification — "
            "defaulting to ITINERARY for safety."
        )

    logger.info(f"Orchestrator dispatching to: {route}")
    return {
        "route": route,
        "loop_count": state.get("loop_count", 0),
        "revision_hint": state.get("revision_hint", ""),
    }


def orchestrator_route_selector(state: AgentState) -> str:
    """LangGraph conditional-edge selector. Returns the next node name."""
    route = state.get("route") or "ITINERARY"
    return {
        "ITINERARY":   "intent",
        "FLIGHT_ONLY": "flight_only",
        "HOTEL_ONLY":  "hotel_only",
        "CHAT":        "chat_fallback",
    }.get(route, "intent")
