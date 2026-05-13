"""
Flight Search Agent -- parallel branch.
Stores results in both 'flights' and 'all_flights'.
"""

import logging
from models.state import AgentState
from services.flights import search_flights

logger = logging.getLogger(__name__)


async def flight_agent(state: AgentState) -> dict:
    """Search for flights based on the extracted intent."""
    intent = state.get("intent")
    if not intent:
        logger.warning("No intent available -- skipping flight search.")
        return {"flights": [], "all_flights": []}

    logger.info(f"Searching flights: {intent.source} -> {intent.destination}")
    flights = await search_flights(intent.source, intent.destination, intent.start_date)
    logger.info(f"Found {len(flights)} flight options.")
    # Store in both: 'flights' will be narrowed by budget, 'all_flights' preserved for UI
    return {"flights": flights, "all_flights": flights}
