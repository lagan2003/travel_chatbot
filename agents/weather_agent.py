"""
Weather Agent — parallel branch.
Fetches weather forecast for the destination + travel dates.
"""

import logging
from models.state import AgentState
from services.weather import get_weather

logger = logging.getLogger(__name__)


async def weather_agent(state: AgentState) -> dict:
    """Fetch weather forecast for the destination during the trip dates."""
    intent = state.get("intent")
    if not intent:
        logger.warning("No intent available — skipping weather fetch.")
        return {"weather": []}

    logger.info(f"Fetching weather for {intent.destination}, {intent.duration_days} days")
    weather = await get_weather(intent.destination, intent.start_date, intent.duration_days)
    logger.info(f"Got {len(weather)} days of weather data.")
    return {"weather": weather}
