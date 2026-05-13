"""
Hotel Search Agent -- parallel branch.
Stores results in both 'hotels' and 'all_hotels'.
"""

import logging
from models.state import AgentState
from services.hotels import search_hotels

logger = logging.getLogger(__name__)


async def hotel_agent(state: AgentState) -> dict:
    """Search for hotels at the destination."""
    intent = state.get("intent")
    if not intent:
        logger.warning("No intent available -- skipping hotel search.")
        return {"hotels": [], "all_hotels": []}

    logger.info(f"Searching hotels in {intent.destination}")
    hotels = await search_hotels(intent.destination, intent.start_date, intent.end_date)
    logger.info(f"Found {len(hotels)} hotel options.")
    return {"hotels": hotels, "all_hotels": hotels}
