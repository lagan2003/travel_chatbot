"""
AgentState -- shared LangGraph state definition.

The orchestrator agent inspects `classification` and routes the workflow.
The critic agent populates `revision_hint` / `loop_count` to drive the
agentic loop back into the itinerary stage when the plan fails review.
"""

from typing import TypedDict, Annotated, List, Optional
import operator
from models.schemas import (
    IntentClassification,
    IntentExtraction,
    Flight,
    Hotel,
    WeatherForecast,
    FullItinerary,
)


class AgentState(TypedDict):
    # -- User input --
    query: str

    # -- Explicit source/destination from the UI (overrides LLM extraction) --
    explicit_source: Optional[str]
    explicit_destination: Optional[str]

    # -- Orchestrator routing --
    classification: Optional[IntentClassification]
    route: Optional[str]                       # "ITINERARY" | "FLIGHT_ONLY" | "HOTEL_ONLY" | "CHAT"

    # -- Intent --
    intent: Optional[IntentExtraction]

    # -- All search results (kept for UI filtering) --
    all_flights: List[Flight]
    all_hotels: List[Hotel]

    # -- Chosen options (narrowed by budget agent) --
    flights: List[Flight]
    hotels: List[Hotel]
    weather: List[WeatherForecast]

    # -- Budget --
    original_budget: float
    daily_activity_budget: float

    # -- Itinerary --
    itinerary: Optional[FullItinerary]

    # -- Recommendations --
    recommendations: List[str]

    # -- Output --
    markdown_output: str
    validation_errors: Annotated[List[str], operator.add]

    # -- Agentic loop bookkeeping --
    revision_hint: str
    loop_count: int
    critic_verdict: Optional[str]              # "APPROVE" | "REVISE"
