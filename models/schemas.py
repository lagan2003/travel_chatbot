"""
Pydantic schemas for the AI Travel Planner.
Every data structure flowing through the pipeline is validated here.
"""

from typing import List, Optional, Dict, Any, Literal
from pydantic import BaseModel, Field


IntentLabel = Literal["ITINERARY", "FLIGHT_ONLY", "HOTEL_ONLY", "CHAT"]


class IntentClassification(BaseModel):
    """Top-level routing label produced by the intent classifier agent."""
    intent: IntentLabel = Field(description="Which downstream subgraph to dispatch to")
    confidence: float = Field(default=0.7, ge=0.0, le=1.0)
    needs_clarification: bool = Field(default=False)
    reasoning: str = Field(default="")


class CriticVerdict(BaseModel):
    """Output of the critic agent inside the agentic loop."""
    verdict: Literal["APPROVE", "REVISE"] = Field(default="APPROVE")
    issues: List[str] = Field(default_factory=list)
    revision_hint: str = Field(default="")


class IntentExtraction(BaseModel):
    """Structured travel intent extracted from the user's natural-language query."""
    destination: str = Field(description="The destination city or country")
    source: str = Field(description="The origin city or country")
    start_date: str = Field(description="The start date of the trip (YYYY-MM-DD)", default="")
    end_date: str = Field(description="The end date of the trip (YYYY-MM-DD)", default="")
    budget: float = Field(description="The total budget for the trip in USD", default=0.0)
    duration_days: int = Field(description="Duration of the trip in days", default=5)
    travelers: int = Field(description="Number of travelers", default=1)
    travel_class: str = Field(
        description="Preferred travel class: economy | business | first | luxury | budget",
        default="economy",
    )
    preferences: List[str] = Field(
        description="List of user preferences (e.g., 'luxury', 'museums', 'nature')",
        default_factory=list,
    )


class Flight(BaseModel):
    airline: str
    flight_number: str
    departure_time: str
    arrival_time: str
    price: float
    duration_minutes: Optional[int] = None
    stops: int = 0
    booking_url: Optional[str] = None
    recommended: bool = False
    cabin_class: str = "economy"


class Hotel(BaseModel):
    name: str
    rating: float
    price_per_night: float
    address: str
    amenities: List[str] = Field(default_factory=list)
    distance_from_center_km: Optional[float] = None
    booking_url: Optional[str] = None
    recommended: bool = False


class WeatherForecast(BaseModel):
    date: str
    temperature_high: float
    temperature_low: float
    conditions: str


class Activity(BaseModel):
    name: str
    description: str
    estimated_cost: float
    duration_hours: float


class DailyPlan(BaseModel):
    day: int
    date: str
    hotel: Optional[Hotel] = None
    activities: List[Activity] = Field(default_factory=list)
    meals: List[Dict[str, Any]] = Field(default_factory=list)
    daily_budget: float = 0.0


class FullItinerary(BaseModel):
    intent: IntentExtraction
    flights: List[Flight] = Field(default_factory=list)
    hotels: List[Hotel] = Field(default_factory=list)
    weather: List[WeatherForecast] = Field(default_factory=list)
    daily_plans: List[DailyPlan] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)
    total_estimated_cost: float = 0.0
    markdown_itinerary: str = ""


# ─── NLP query schemas for the dedicated Flight/Hotel pages ───

class FlightQueryExtract(BaseModel):
    """Structured extraction from a free-form flight query."""
    source: str = ""
    destination: str = ""
    date_phrase: str = Field(default="", description="Raw date phrase if present: 'next weekend', 'Friday'…")
    departure_date: str = Field(default="", description="YYYY-MM-DD if a hard date was extracted")
    cabin_class: str = "economy"
    max_price: Optional[float] = None
    time_of_day: str = Field(default="", description="morning | afternoon | evening | night | ''")
    non_stop: bool = False


class HotelQueryExtract(BaseModel):
    """Structured extraction from a free-form hotel query."""
    destination: str = ""
    check_in: str = ""
    check_out: str = ""
    max_price_per_night: Optional[float] = None
    min_rating: Optional[float] = None
    amenities: List[str] = Field(default_factory=list)
    style: str = Field(default="", description="luxury | budget | business | family | romantic | beach…")
