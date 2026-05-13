"""
LangGraph workflow — Agentic multi-agent travel system.

Architecture (no ML — pure agentic / LLM orchestration):

  START
    │
    ▼
  ┌────────────────────────┐
  │  intent_classifier      │  ── classify ITINERARY / FLIGHT_ONLY / HOTEL_ONLY / CHAT
  └─────────┬──────────────┘
            ▼
  ┌────────────────────────┐
  │  orchestrator           │  ── decides which subgraph runs
  └─────────┬──────────────┘
            │  (conditional edge — multi-route)
            ├─────────────► flight_only ─► END
            ├─────────────► hotel_only  ─► END
            ├─────────────► chat_fallback ─► END
            ▼
        intent (extracts source / destination / dates / budget)
            │
   ┌────────┼────────┐
   ▼        ▼        ▼
 flights  hotels  weather       (parallel fan-out — LangGraph runs concurrently)
   │        │        │
   └────────┼────────┘
            ▼
        budget   (fan-in: picks best flight + hotel, computes daily $)
            │
            ▼
        itinerary  ◄──────────────┐
            │                      │
            ▼                      │ REVISE
        recommendation             │  (agentic loop, capped at MAX_LOOPS)
            │                      │
            ▼                      │
        validation                 │
            │                      │
            ▼                      │
        critic ────────────────────┘
            │
            │ APPROVE
            ▼
        formatter ──► END

Implementation notes:
- Each node is a Runnable (LangGraph wraps sync/async functions as Runnables).
- The three search agents (flights, hotels, weather) execute in parallel because
  they have a common predecessor (`intent`) and a common successor (`budget`) —
  LangGraph schedules them concurrently in a single super-step.
- The critic agent powers an agentic feedback loop: REVISE routes back to the
  itinerary node; APPROVE proceeds to the formatter. `critic_agent.MAX_LOOPS`
  guarantees termination.
- The orchestrator drives a conditional edge with `add_conditional_edges`, so
  the same compiled graph handles full-plan, flight-only, hotel-only and chat
  intents with no branching at the FastAPI layer.
"""

from langgraph.graph import StateGraph, START, END
from models.state import AgentState

# Core agents
from agents.intent_classifier_agent import intent_classifier_agent
from agents.orchestrator_agent import orchestrator_agent, orchestrator_route_selector
from agents.intent_agent import intent_agent
from agents.flight_agent import flight_agent
from agents.hotel_agent import hotel_agent
from agents.weather_agent import weather_agent
from agents.budget_agent import budget_agent
from agents.itinerary_agent import itinerary_agent
from agents.recommendation_agent import recommendation_agent
from agents.validation_agent import validation_agent
from agents.critic_agent import critic_agent, critic_route_selector
from agents.formatter_agent import formatter_agent

# Subgraph terminal nodes (flight-only / hotel-only / chat)
from agents.subgraph_agents import (
    flight_only_node,
    hotel_only_node,
    chat_fallback_node,
)


def create_travel_workflow():
    """Build and compile the LangGraph agentic state machine."""
    workflow = StateGraph(AgentState)

    # ── Register nodes ──
    workflow.add_node("intent_classifier", intent_classifier_agent)
    workflow.add_node("orchestrator", orchestrator_agent)

    # Itinerary lane
    workflow.add_node("intent", intent_agent)
    workflow.add_node("flights", flight_agent)
    workflow.add_node("hotels", hotel_agent)
    workflow.add_node("weather", weather_agent)
    workflow.add_node("budget", budget_agent)
    workflow.add_node("itinerary", itinerary_agent)
    workflow.add_node("recommendation", recommendation_agent)
    workflow.add_node("validation", validation_agent)
    workflow.add_node("critic", critic_agent)
    workflow.add_node("formatter", formatter_agent)

    # Other lanes
    workflow.add_node("flight_only", flight_only_node)
    workflow.add_node("hotel_only", hotel_only_node)
    workflow.add_node("chat_fallback", chat_fallback_node)

    # ── Edges ──
    workflow.add_edge(START, "intent_classifier")
    workflow.add_edge("intent_classifier", "orchestrator")

    # Conditional dispatch from orchestrator
    workflow.add_conditional_edges(
        "orchestrator",
        orchestrator_route_selector,
        {
            "intent":         "intent",
            "flight_only":    "flight_only",
            "hotel_only":     "hotel_only",
            "chat_fallback":  "chat_fallback",
        },
    )

    # Parallel fan-out from `intent` (ITINERARY lane)
    workflow.add_edge("intent", "flights")
    workflow.add_edge("intent", "hotels")
    workflow.add_edge("intent", "weather")

    # Fan-in to budget (LangGraph waits for all three before running budget)
    workflow.add_edge("flights", "budget")
    workflow.add_edge("hotels", "budget")
    workflow.add_edge("weather", "budget")

    # Linear pipeline up to critic
    workflow.add_edge("budget", "itinerary")
    workflow.add_edge("itinerary", "recommendation")
    workflow.add_edge("recommendation", "validation")
    workflow.add_edge("validation", "critic")

    # Agentic loop: critic decides REVISE -> itinerary, or APPROVE -> formatter
    workflow.add_conditional_edges(
        "critic",
        critic_route_selector,
        {
            "itinerary": "itinerary",
            "formatter": "formatter",
        },
    )

    # Terminal edges
    workflow.add_edge("formatter", END)
    workflow.add_edge("flight_only", END)
    workflow.add_edge("hotel_only", END)
    workflow.add_edge("chat_fallback", END)

    return workflow.compile()
