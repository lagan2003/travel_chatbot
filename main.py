"""
FastAPI backend — full set of endpoints:

  /health                — basic liveness probe
  /status                — per-service health (LLM + flights + hotels + weather)
  /plan                  — run the full multi-agent pipeline
  /select                — re-run pipeline with the user's chosen flight + hotel
  /filter                — deterministic NLP filter over flights & hotels
  /flights/search        — dedicated NLP flight search
  /hotels/search         — dedicated NLP hotel search
  /chat/stream           — token-stream a single Groq response
  /trips, /trips/{id}    — CRUD for saved trips
"""

from __future__ import annotations

import logging
import re
from typing import List, Optional

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Agentic AI Travel Planner",
    description="Multi-agent travel planning powered by LangGraph + Groq",
    version="1.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Request / Response models ───

class QueryRequest(BaseModel):
    query: str
    source: Optional[str] = None
    destination: Optional[str] = None


class FlightOption(BaseModel):
    airline: str
    flight_number: str
    departure_time: str
    arrival_time: str
    price: float
    duration_minutes: Optional[int] = None
    stops: int = 0
    cabin_class: str = "economy"
    recommended: bool = False
    booking_url: Optional[str] = None


class HotelOption(BaseModel):
    name: str
    rating: float
    price_per_night: float
    address: str
    amenities: List[str] = []
    distance_from_center_km: Optional[float] = None
    recommended: bool = False
    booking_url: Optional[str] = None


class QueryResponse(BaseModel):
    markdown_output: str
    validation_errors: List[str]
    total_cost: float
    recommendations: List[str]
    all_flights: List[FlightOption]
    all_hotels: List[HotelOption]
    source: str
    destination: str


class FilterRequest(BaseModel):
    filter_query: str
    flights: List[FlightOption]
    hotels: List[HotelOption]


class FilterResponse(BaseModel):
    filtered_flights: List[FlightOption]
    filtered_hotels: List[HotelOption]
    explanation: str


class SelectRequest(BaseModel):
    flight_index: int
    hotel_index: int
    all_flights: List[FlightOption]
    all_hotels: List[HotelOption]
    query: str
    source: str
    destination: str


class NLPFlightRequest(BaseModel):
    query: str


class NLPFlightResponse(BaseModel):
    extracted: dict
    flights: List[FlightOption]
    explanation: str


class NLPHotelRequest(BaseModel):
    query: str


class NLPHotelResponse(BaseModel):
    extracted: dict
    hotels: List[HotelOption]
    explanation: str


class ChatRequest(BaseModel):
    prompt: str


class SaveTripRequest(BaseModel):
    title: Optional[str] = None
    payload: dict


# ─── Lazy init ───

_workflow = None


def _get_workflow():
    global _workflow
    if _workflow is None:
        from workflows.graph import create_travel_workflow
        _workflow = create_travel_workflow()
    return _workflow


def _flight_to_option(f) -> FlightOption:
    return FlightOption(**f.model_dump())


def _hotel_to_option(h) -> HotelOption:
    return HotelOption(**h.model_dump())


# ─── Health + Status ───

@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/status")
async def status():
    from services.status import probe_all
    return await probe_all()


# ─── Main pipeline ───

@app.post("/plan", response_model=QueryResponse)
async def plan_trip(request: QueryRequest):
    enriched_query = request.query
    src = (request.source or "").strip()
    dest = (request.destination or "").strip()

    if src and src.lower() not in enriched_query.lower():
        enriched_query += f" from {src}"
    if dest and dest.lower() not in enriched_query.lower():
        enriched_query += f" to {dest}"

    logger.info(f"Received query: {enriched_query!r}")
    try:
        workflow = _get_workflow()

        initial_state = {
            "query": enriched_query,
            "explicit_source": src or None,
            "explicit_destination": dest or None,
            "classification": None,
            "route": None,
            "intent": None,
            "flights": [], "hotels": [],
            "all_flights": [], "all_hotels": [],
            "weather": [],
            "original_budget": 0.0,
            "daily_activity_budget": 0.0,
            "itinerary": None,
            "recommendations": [],
            "markdown_output": "",
            "validation_errors": [],
            "revision_hint": "",
            "loop_count": 0,
            "critic_verdict": None,
        }

        result = await workflow.ainvoke(initial_state)

        itinerary = result.get("itinerary")
        cost = itinerary.total_estimated_cost if itinerary else 0.0
        intent = result.get("intent")

        all_flights_raw = result.get("all_flights") or result.get("flights", [])
        all_hotels_raw = result.get("all_hotels") or result.get("hotels", [])

        return QueryResponse(
            markdown_output=result.get("markdown_output", ""),
            validation_errors=result.get("validation_errors", []),
            total_cost=cost,
            recommendations=result.get("recommendations", []),
            all_flights=[_flight_to_option(f) for f in all_flights_raw],
            all_hotels=[_hotel_to_option(h) for h in all_hotels_raw],
            source=intent.source if intent else (src or ""),
            destination=intent.destination if intent else (dest or ""),
        )
    except Exception as e:
        logger.exception("Pipeline failed")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/select", response_model=QueryResponse)
async def select_options(request: SelectRequest):
    logger.info(
        f"User selected flight #{request.flight_index}, hotel #{request.hotel_index} "
        f"for {request.source} -> {request.destination}"
    )

    if request.flight_index < 0 or request.flight_index >= len(request.all_flights):
        raise HTTPException(status_code=400, detail="Invalid flight index")
    if request.hotel_index < 0 or request.hotel_index >= len(request.all_hotels):
        raise HTTPException(status_code=400, detail="Invalid hotel index")

    chosen_flight = request.all_flights[request.flight_index]
    chosen_hotel = request.all_hotels[request.hotel_index]

    try:
        workflow = _get_workflow()
        enriched_query = (
            f"{request.query} from {request.source} to {request.destination}. "
            f"User selected flight: {chosen_flight.airline} ({chosen_flight.flight_number}) at ${chosen_flight.price}. "
            f"User selected hotel: {chosen_hotel.name} at ${chosen_hotel.price_per_night}/night."
        )

        initial_state = {
            "query": enriched_query,
            "explicit_source": request.source,
            "explicit_destination": request.destination,
            "classification": None,
            "route": None,
            "intent": None,
            "flights": [], "hotels": [],
            "all_flights": [], "all_hotels": [],
            "weather": [],
            "original_budget": 0.0,
            "daily_activity_budget": 0.0,
            "itinerary": None,
            "recommendations": [],
            "markdown_output": "",
            "validation_errors": [],
            "revision_hint": "",
            "loop_count": 0,
            "critic_verdict": None,
        }

        result = await workflow.ainvoke(initial_state)

        itinerary = result.get("itinerary")
        cost = itinerary.total_estimated_cost if itinerary else 0.0
        intent = result.get("intent")

        return QueryResponse(
            markdown_output=result.get("markdown_output", ""),
            validation_errors=result.get("validation_errors", []),
            total_cost=cost,
            recommendations=result.get("recommendations", []),
            all_flights=[_flight_to_option(f) for f in result.get("all_flights", [])],
            all_hotels=[_hotel_to_option(h) for h in result.get("all_hotels", [])],
            source=intent.source if intent else request.source,
            destination=intent.destination if intent else request.destination,
        )
    except Exception as e:
        logger.exception("Select pipeline failed")
        raise HTTPException(status_code=500, detail=str(e))


# ─── Filter (deterministic NLP over a server-side list) ───

@app.post("/filter", response_model=FilterResponse)
async def filter_options(request: FilterRequest):
    q = request.filter_query.lower()
    flights = request.flights
    hotels = request.hotels
    filtered_flights = flights
    filtered_hotels = hotels
    explanation = ""

    if any(kw in q for kw in ["cheapest", "lowest price", "budget flight", "cheap"]):
        if flights:
            min_price = min(f.price for f in flights)
            filtered_flights = [f for f in flights if f.price == min_price]
            explanation = f"Showing the cheapest flight at ${min_price:.2f}."

    elif any(kw in q for kw in ["most expensive", "premium", "luxury flight"]):
        if flights:
            max_price = max(f.price for f in flights)
            filtered_flights = [f for f in flights if f.price == max_price]
            explanation = f"Showing the premium flight at ${max_price:.2f}."

    elif "non-stop" in q or "nonstop" in q or "direct" in q:
        filtered_flights = [f for f in flights if f.stops == 0]
        if not filtered_flights:
            filtered_flights = flights
        explanation = "Showing non-stop flights."

    elif "morning" in q:
        filtered_flights = [f for f in flights if "T0" in f.departure_time or "T10" in f.departure_time or "T11" in f.departure_time]
        if not filtered_flights:
            filtered_flights = flights
        explanation = "Showing morning departure flights."

    elif "evening" in q or "night" in q:
        filtered_flights = [f for f in flights if any(f"T{h}" in f.departure_time for h in ["18", "19", "20", "21", "22", "23"])]
        if not filtered_flights:
            filtered_flights = flights
        explanation = "Showing evening/night departure flights."

    if any(kw in q for kw in ["cheapest hotel", "budget hotel", "cheap hotel"]):
        if hotels:
            min_price = min(h.price_per_night for h in hotels)
            filtered_hotels = [h for h in hotels if h.price_per_night == min_price]
            explanation += f" Cheapest hotel at ${min_price:.2f}/night."

    elif any(kw in q for kw in ["best rated", "top rated", "highest rated", "best hotel"]):
        if hotels:
            max_rating = max(h.rating for h in hotels)
            filtered_hotels = [h for h in hotels if h.rating == max_rating]
            explanation += f" Showing top-rated hotel ({max_rating} stars)."

    elif any(kw in q for kw in ["luxury hotel", "5 star", "five star", "premium hotel"]):
        filtered_hotels = [h for h in hotels if h.rating >= 4.5]
        if not filtered_hotels:
            filtered_hotels = hotels
        explanation += " Showing luxury/high-rated hotels."

    elif "under" in q:
        m = re.search(r"under\s*\$?(\d+)", q)
        if m:
            threshold = float(m.group(1))
            filtered_hotels = [h for h in hotels if h.price_per_night <= threshold]
            if not filtered_hotels:
                filtered_hotels = hotels
                explanation += f" No hotels under ${threshold}. Showing all."
            else:
                explanation += f" Hotels under ${threshold}/night."

    if not explanation:
        explanation = "Showing all available options."

    return FilterResponse(
        filtered_flights=filtered_flights,
        filtered_hotels=filtered_hotels,
        explanation=explanation,
    )


# ─── Dedicated NLP flight search ───

@app.post("/flights/search", response_model=NLPFlightResponse)
async def flights_search(req: NLPFlightRequest):
    from services.nlp import extract_flight_query
    from services.flights import search_flights

    extracted = extract_flight_query(req.query)

    if not extracted.destination:
        raise HTTPException(status_code=422, detail="Could not infer a destination from the query.")
    if not extracted.source:
        extracted.source = "your city"

    raw = await search_flights(extracted.source, extracted.destination, extracted.departure_date)

    result = list(raw)
    if extracted.max_price is not None:
        result = [f for f in result if f.price <= extracted.max_price]
    if extracted.non_stop:
        result = [f for f in result if f.stops == 0]
    if extracted.time_of_day:
        bands = {
            "morning":   range(5, 12),
            "afternoon": range(12, 17),
            "evening":   range(17, 21),
            "night":     [21, 22, 23, 0, 1, 2, 3, 4],
        }
        allowed = set(bands.get(extracted.time_of_day, []))

        def hr(t: str) -> int:
            try:
                return int(t.split("T")[1][:2]) if "T" in t else int(t[:2])
            except (ValueError, IndexError):
                return -1
        result = [f for f in result if hr(f.departure_time) in allowed]

    if extracted.cabin_class in {"business", "first"}:
        for f in result:
            f.cabin_class = extracted.cabin_class
            f.price = round(f.price * (2.4 if extracted.cabin_class == "business" else 3.5), 2)
    if not result:
        result = raw
        explanation = ("Filters were too restrictive — showing all available options for "
                       f"{extracted.source} → {extracted.destination}.")
    else:
        explanation = (f"{len(result)} flight(s) for {extracted.source} → {extracted.destination} "
                       f"on {extracted.departure_date} "
                       f"({extracted.cabin_class}).")

    return NLPFlightResponse(
        extracted=extracted.model_dump(),
        flights=[_flight_to_option(f) for f in result],
        explanation=explanation,
    )


# ─── Dedicated NLP hotel search ───

@app.post("/hotels/search", response_model=NLPHotelResponse)
async def hotels_search(req: NLPHotelRequest):
    from services.nlp import extract_hotel_query
    from services.hotels import search_hotels

    extracted = extract_hotel_query(req.query)
    if not extracted.destination:
        raise HTTPException(status_code=422, detail="Could not infer a destination from the query.")

    raw = await search_hotels(extracted.destination, extracted.check_in, extracted.check_out)
    result = list(raw)

    if extracted.max_price_per_night is not None:
        result = [h for h in result if h.price_per_night <= extracted.max_price_per_night]
    if extracted.min_rating is not None:
        result = [h for h in result if h.rating >= extracted.min_rating]
    if extracted.amenities:
        wanted = {a.lower() for a in extracted.amenities}
        result = [h for h in result if {a.lower() for a in h.amenities} & wanted]
    if extracted.style == "luxury":
        result = sorted(result, key=lambda h: (-h.rating, h.price_per_night))
    elif extracted.style == "budget":
        result = sorted(result, key=lambda h: (h.price_per_night, -h.rating))

    if not result:
        result = raw
        explanation = f"Filters too restrictive — showing all hotels in {extracted.destination}."
    else:
        explanation = f"{len(result)} hotel(s) in {extracted.destination}."

    return NLPHotelResponse(
        extracted=extracted.model_dump(),
        hotels=[_hotel_to_option(h) for h in result],
        explanation=explanation,
    )


# ─── Streaming chat ───

@app.post("/chat/stream")
async def chat_stream(req: ChatRequest):
    from services.llm import get_llm

    async def gen():
        llm = get_llm()
        try:
            for chunk in llm.stream(req.prompt):
                content = getattr(chunk, "content", "") or ""
                if content:
                    yield content
        except Exception as e:
            logger.exception("Streaming failed")
            yield f"\n\n[stream error: {e}]"

    return StreamingResponse(gen(), media_type="text/plain")


# ─── Saved trips ───

@app.post("/trips")
async def save_trip(req: SaveTripRequest):
    from services.storage import save_trip as _save
    record = {**req.payload, "title": req.title or req.payload.get("title")}
    trip_id = _save(record)
    return {"id": trip_id, "status": "saved"}


@app.get("/trips")
async def list_trips_endpoint():
    from services.storage import list_trips
    return list_trips()


@app.get("/trips/{trip_id}")
async def get_trip_endpoint(trip_id: str):
    from services.storage import get_trip
    trip = get_trip(trip_id)
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    return trip


@app.delete("/trips/{trip_id}")
async def delete_trip_endpoint(trip_id: str):
    from services.storage import delete_trip
    ok = delete_trip(trip_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Trip not found")
    return {"status": "deleted"}
