"""
Lightweight terminal nodes used by the orchestrator when the route is NOT
a full itinerary.

- flight_only_node : runs the same flight search but skips budget+itinerary.
- hotel_only_node  : same idea for hotels.
- chat_fallback_node : produces a short conversational response.

All three write straight into `markdown_output` so the existing
QueryResponse contract still works.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta

from models.state import AgentState
from services.flights import search_flights
from services.hotels import search_hotels
from services.nlp import extract_flight_query, extract_hotel_query
from services.llm import get_llm

logger = logging.getLogger(__name__)


def _default_date(days_ahead: int = 14) -> str:
    return (datetime.now() + timedelta(days=days_ahead)).strftime("%Y-%m-%d")


async def flight_only_node(state: AgentState) -> dict:
    """Live flight suggestions from a free-form NLP query (no full plan)."""
    query = state.get("query", "")
    extracted = extract_flight_query(query)

    source = extracted.source or state.get("explicit_source") or ""
    destination = extracted.destination or state.get("explicit_destination") or ""
    if not destination:
        return {
            "all_flights": [],
            "flights": [],
            "markdown_output": (
                "✈️ I need a destination to search flights. "
                "Try: *cheapest flights from Delhi to Dubai next weekend*."
            ),
        }
    if not source:
        source = "your city"

    date = extracted.departure_date or _default_date()
    flights = await search_flights(source, destination, date)

    if extracted.max_price:
        flights = [f for f in flights if f.price <= extracted.max_price] or flights
    if extracted.non_stop:
        flights = [f for f in flights if f.stops == 0] or flights

    flights.sort(key=lambda f: f.price)

    md_lines = [
        f"## ✈️ Flight suggestions — {source} → {destination}",
        f"_Date: {date} · cabin: {extracted.cabin_class}_",
        "",
    ]
    for i, f in enumerate(flights[:6], 1):
        md_lines.append(
            f"{i}. **{f.airline}** {f.flight_number} — ${f.price:.2f} · "
            f"{f.departure_time} → {f.arrival_time} · stops: {f.stops}"
        )

    logger.info(f"flight_only_node: returned {len(flights)} flights.")
    return {
        "all_flights": flights,
        "flights": flights,
        "markdown_output": "\n".join(md_lines),
    }


async def hotel_only_node(state: AgentState) -> dict:
    """Live hotel suggestions from a free-form NLP query (no full plan)."""
    query = state.get("query", "")
    extracted = extract_hotel_query(query)

    destination = extracted.destination or state.get("explicit_destination") or ""
    if not destination:
        return {
            "all_hotels": [],
            "hotels": [],
            "markdown_output": (
                "🏨 I need a destination to search hotels. "
                "Try: *family hotels in Singapore under $200 with a pool*."
            ),
        }

    check_in = extracted.check_in or _default_date()
    check_out = extracted.check_out or _default_date(days_ahead=17)
    hotels = await search_hotels(destination, check_in, check_out)

    if extracted.max_price_per_night:
        hotels = [h for h in hotels if h.price_per_night <= extracted.max_price_per_night] or hotels
    if extracted.min_rating:
        hotels = [h for h in hotels if h.rating >= extracted.min_rating] or hotels
    if extracted.amenities:
        wanted = {a.lower() for a in extracted.amenities}
        filtered = [
            h for h in hotels
            if any(a.lower() in wanted for a in h.amenities)
        ]
        hotels = filtered or hotels

    hotels.sort(key=lambda h: (-h.rating, h.price_per_night))

    md_lines = [
        f"## 🏨 Hotel suggestions — {destination}",
        f"_Check-in: {check_in} · Check-out: {check_out}_",
        "",
    ]
    for i, h in enumerate(hotels[:6], 1):
        amen = ", ".join(h.amenities[:4]) if h.amenities else "—"
        md_lines.append(
            f"{i}. **{h.name}** · ⭐ {h.rating} · ${h.price_per_night:.2f}/night · "
            f"{h.address} · {amen}"
        )

    logger.info(f"hotel_only_node: returned {len(hotels)} hotels.")
    return {
        "all_hotels": hotels,
        "hotels": hotels,
        "markdown_output": "\n".join(md_lines),
    }


def chat_fallback_node(state: AgentState) -> dict:
    """Generic conversational fallback when the user has no concrete plan."""
    query = state.get("query", "")
    llm = get_llm()
    try:
        resp = llm.invoke(
            "You are a friendly travel concierge. Answer in 3 short paragraphs.\n\n"
            f"User: {query}"
        )
        md = resp.content
    except Exception as e:
        logger.warning(f"chat_fallback LLM failed: {e}")
        md = (
            "👋 I'm a travel-planning agent. Ask me to build an itinerary, "
            "find flights, or suggest hotels."
        )
    return {"markdown_output": md}
