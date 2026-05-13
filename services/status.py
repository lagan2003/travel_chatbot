"""
Aggregated probe of each external dependency, used by GET /status.
Each probe must never raise — it returns a status dict.
"""

from __future__ import annotations

import asyncio
import logging
import os

from services import flights, hotels, weather
from services.cache import cache_stats

logger = logging.getLogger(__name__)


async def _llm_status() -> dict:
    """Cheapest possible probe: just check that the key is configured."""
    key = os.getenv("GROQ_API_KEY", "")
    configured = bool(key) and not key.startswith("your_")
    return {
        "name": "llm",
        "provider": "Groq",
        "model": os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),
        "configured": configured,
        "live": configured,
        "note": "" if configured else "GROQ_API_KEY missing",
    }


async def probe_all() -> dict:
    flights_r, hotels_r, weather_r, llm_r = await asyncio.gather(
        flights.is_available(),
        hotels.is_available(),
        weather.is_available(),
        _llm_status(),
        return_exceptions=False,
    )
    statuses = [llm_r, flights_r, hotels_r, weather_r]
    healthy = sum(1 for s in statuses if s.get("live"))
    return {
        "overall": "healthy" if healthy == len(statuses) else ("degraded" if healthy else "down"),
        "healthy_services": healthy,
        "total_services": len(statuses),
        "services": statuses,
        "cache": cache_stats(),
    }
