"""
Formatter Agent — final node.

Compiles all itinerary state into a polished, human-readable Markdown document.

Strategy:
  1. Always compute a deterministic Markdown rendering from the FullItinerary —
     this is the bulletproof fallback and never produces JSON.
  2. Try the LLM to make it more engaging and travel-blog-style.
  3. If the LLM fails OR returns JSON-shaped content (e.g. starts with `{` or
     contains a ```json fence), discard it and use the deterministic version.
"""

from __future__ import annotations

import logging
import re

from models.state import AgentState
from models.schemas import FullItinerary
from services.llm import get_llm
from prompts.system_prompts import FORMATTER_PROMPT

logger = logging.getLogger(__name__)


_JSON_FENCE_RE = re.compile(r"```\s*json", re.IGNORECASE)


def _looks_like_json(text: str) -> bool:
    """True if LLM output is JSON instead of Markdown."""
    if not text:
        return True
    stripped = text.lstrip()
    if stripped.startswith("{") or stripped.startswith("["):
        return True
    if _JSON_FENCE_RE.search(stripped[:200]):
        return True
    return False


def _build_deterministic_markdown(itinerary: FullItinerary, errors: list[str]) -> str:
    """Render a clean, human-readable Markdown document from the itinerary —
    guaranteed to never look like JSON."""
    intent = itinerary.intent
    lines: list[str] = []

    # Title
    lines.append(f"# ✈️ {intent.source} → {intent.destination}")
    lines.append(
        f"_{intent.duration_days}-day trip"
        + (f" starting {intent.start_date}" if intent.start_date else "")
        + (f", budget ${intent.budget:,.0f}" if intent.budget else "")
        + "_"
    )
    lines.append("")

    # Trip overview
    lines.append("## 🌍 Trip Overview")
    if intent.preferences:
        lines.append(f"**Preferences:** {', '.join(intent.preferences)}")
    if intent.travelers and intent.travelers > 1:
        lines.append(f"**Travelers:** {intent.travelers}")
    if intent.travel_class:
        lines.append(f"**Travel class:** {intent.travel_class.title()}")
    lines.append(f"**Total estimated cost:** **${itinerary.total_estimated_cost:,.2f}**")
    lines.append("")

    # Flights
    if itinerary.flights:
        lines.append("## 🛫 Selected Flight")
        for f in itinerary.flights:
            stops = "Non-stop" if (f.stops or 0) == 0 else f"{f.stops} stop(s)"
            dep = f.departure_time.replace("T", " ")
            arr = f.arrival_time.replace("T", " ")
            dur = ""
            if f.duration_minutes:
                h, m = divmod(int(f.duration_minutes), 60)
                dur = f" ({h}h {m}m)"
            lines.append(f"- **{f.airline}** — `{f.flight_number}`")
            lines.append(f"  - {dep} → {arr}{dur} • {stops}")
            lines.append(f"  - **Price:** ${f.price:,.2f}")
            if f.booking_url:
                lines.append(f"  - [Book this flight ↗]({f.booking_url})")
        lines.append("")

    # Hotels
    if itinerary.hotels:
        lines.append("## 🏨 Selected Hotel")
        for h in itinerary.hotels:
            stars = "★" * int(h.rating) + ("½" if (h.rating - int(h.rating)) >= 0.3 else "")
            lines.append(f"- **{h.name}** — {stars} ({h.rating}/5)")
            lines.append(f"  - {h.address}")
            if h.distance_from_center_km is not None:
                lines.append(f"  - {h.distance_from_center_km:.1f} km from city center")
            if h.amenities:
                lines.append(f"  - Amenities: {', '.join(h.amenities)}")
            lines.append(f"  - **${h.price_per_night:,.2f} / night**")
            if h.booking_url:
                lines.append(f"  - [Book this hotel ↗]({h.booking_url})")
        lines.append("")

    # Weather
    if itinerary.weather:
        lines.append("## 🌤️ Weather Forecast")
        for w in itinerary.weather:
            lines.append(
                f"- **{w.date}** — {w.conditions}, "
                f"{w.temperature_low:.0f}°C — {w.temperature_high:.0f}°C"
            )
        lines.append("")

    # Day-by-day
    if itinerary.daily_plans:
        lines.append("## 📅 Day-by-Day Itinerary")
        for dp in itinerary.daily_plans:
            header = f"### Day {dp.day}"
            if dp.date:
                header += f" — {dp.date}"
            lines.append(header)
            if dp.daily_budget:
                lines.append(f"_Daily budget: ${dp.daily_budget:,.2f}_")
            if not dp.activities:
                lines.append("_No activities planned._")
            else:
                for act in dp.activities:
                    cost = f" — *${act.estimated_cost:,.0f}*" if act.estimated_cost else ""
                    dur = f" _({act.duration_hours}h)_" if act.duration_hours else ""
                    lines.append(f"- **{act.name}**{dur}{cost}")
                    if act.description:
                        lines.append(f"  - {act.description}")
            lines.append("")

    # Recommendations
    if itinerary.recommendations:
        lines.append("## 💎 Hidden Gems & Local Tips")
        for r in itinerary.recommendations:
            lines.append(f"- {r}")
        lines.append("")

    # Validation
    if errors:
        lines.append("## ⚠️ Notes")
        for e in errors:
            lines.append(f"- {e}")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def formatter_agent(state: AgentState) -> dict:
    """Format the itinerary into a polished Markdown document — never JSON."""
    itinerary = state.get("itinerary")
    raw_errors = state.get("validation_errors", []) or []
    recommendations = state.get("recommendations", [])

    if not itinerary:
        return {"markdown_output": "❌ Failed to generate itinerary."}

    # Dedupe validation errors — the agentic loop can accumulate the same
    # message multiple times via operator.add on the state list.
    errors: list[str] = []
    seen: set[str] = set()
    for e in raw_errors:
        e_clean = (e or "").strip()
        if e_clean and e_clean not in seen:
            seen.add(e_clean)
            errors.append(e_clean)

    # Attach recommendations before serialising
    itinerary.recommendations = recommendations

    # Always compute the deterministic version first — it's our safety net.
    deterministic_md = _build_deterministic_markdown(itinerary, errors)

    # Try LLM for a more engaging rendering
    markdown = deterministic_md
    try:
        llm = get_llm()
        data_str = itinerary.model_dump_json(indent=2)
        prompt = (
            FORMATTER_PROMPT
            + "\n\nIMPORTANT: Output ONLY Markdown — never JSON, never code fences, "
              "never the raw data. Write in a friendly travel-blog tone with headings, "
              "bullet lists, and bold key facts."
            + f"\n\nData:\n{data_str}"
            + f"\n\nRecommendations: {recommendations}"
            + f"\n\nValidation Notes: {errors}"
        )
        response = llm.invoke(prompt)
        candidate = (response.content or "").strip()
        if candidate and not _looks_like_json(candidate):
            markdown = candidate
        else:
            logger.warning("Formatter LLM returned JSON-looking output — using deterministic fallback.")
    except Exception as e:
        logger.error(f"Formatter LLM failed: {e!r} — using deterministic fallback.")

    itinerary.markdown_itinerary = markdown
    logger.info(f"Formatter completed — {len(markdown)} chars of Markdown.")
    return {"markdown_output": markdown, "itinerary": itinerary}
