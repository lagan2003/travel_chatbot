"""
Hotel search service.

Hotel APIs (Booking.com / Hotels.com via RapidAPI) all require paid plans, so we
synthesize a realistic pool of options for the destination — including
amenities, ratings, distance from city center, and price band — and mark the
best-value option as recommended. If a real key is supplied we'll try the
RapidAPI endpoint and gracefully fall back on failure.
"""

from __future__ import annotations

import hashlib
import logging
import os
import random
from typing import List

import httpx

from models.schemas import Hotel
from services.cache import cached, http_retry

logger = logging.getLogger(__name__)

RAPIDAPI_HOST = "hotels-com-provider.p.rapidapi.com"
RAPIDAPI_URL = f"https://{RAPIDAPI_HOST}/v2/hotels/search"

_AMENITY_POOL = [
    "Free WiFi", "Pool", "Spa", "Gym", "Restaurant", "Bar", "Breakfast included",
    "Airport shuttle", "Pet friendly", "Family rooms", "EV charging",
    "Beachfront", "Mountain view", "Rooftop lounge", "Co-working space",
    "24-hour reception", "Room service", "Parking",
]

_TIER_TEMPLATES = [
    # (prefix, rating_range, price_range, amenities_count)
    ("Hostel",              (3.4, 4.0), (35, 75),    3),
    ("Budget Inn",          (3.6, 4.2), (60, 110),   4),
    ("Comfort Suites",      (3.9, 4.4), (95, 160),   5),
    ("Grand Plaza",         (4.2, 4.6), (140, 230),  7),
    ("Boutique",            (4.3, 4.7), (170, 280),  6),
    ("Business Tower",      (4.0, 4.5), (130, 210),  5),
    ("Family Resort",       (4.2, 4.7), (180, 320),  8),
    ("Luxury Collection",   (4.5, 4.9), (300, 520),  9),
    ("Sky Penthouse",       (4.6, 5.0), (420, 780), 10),
]


def _has_real_key() -> bool:
    k = os.getenv("HOTEL_API_KEY", "")
    return bool(k) and k not in {"your_hotel_api_key", "mock"}


def _seed(destination: str) -> int:
    return int(hashlib.md5(destination.lower().encode()).hexdigest()[:8], 16)


def _synth_hotels(destination: str, count: int = 8) -> List[Hotel]:
    rng = random.Random(_seed(destination))
    chosen = rng.sample(_TIER_TEMPLATES, k=min(count, len(_TIER_TEMPLATES)))
    hotels: List[Hotel] = []
    for prefix, (r_lo, r_hi), (p_lo, p_hi), amen_n in chosen:
        rating = round(rng.uniform(r_lo, r_hi), 1)
        price = round(rng.uniform(p_lo, p_hi), 2)
        amens = rng.sample(_AMENITY_POOL, k=min(amen_n, len(_AMENITY_POOL)))
        dist = round(rng.uniform(0.3, 9.5), 1)
        street_no = rng.randint(1, 240)
        street = rng.choice(["Main St", "Beach Rd", "Park Ave", "Riverside Blvd",
                             "Old Town Sq", "Hilltop Dr", "Market St"])
        name = f"{prefix} {destination}"
        hotels.append(Hotel(
            name=name,
            rating=rating,
            price_per_night=price,
            address=f"{street_no} {street}, {destination}",
            amenities=amens,
            distance_from_center_km=dist,
            booking_url=f"https://www.booking.com/searchresults.html?ss={destination.replace(' ', '+')}",
        ))
    hotels.sort(key=lambda h: h.price_per_night)
    # Mark best value (rating-to-price ratio, weighting toward higher rating)
    if hotels:
        scored = sorted(
            enumerate(hotels),
            key=lambda x: -(x[1].rating ** 2 / max(x[1].price_per_night, 1)),
        )
        hotels[scored[0][0]].recommended = True
    return hotels


@http_retry
async def _call_rapidapi(destination: str, key: str) -> dict:
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            RAPIDAPI_URL,
            params={"q": destination, "domain": "US", "locale": "en_US"},
            headers={"X-RapidAPI-Key": key, "X-RapidAPI-Host": RAPIDAPI_HOST},
            timeout=10.0,
        )
        resp.raise_for_status()
        return resp.json()


def _parse_rapidapi(payload: dict, destination: str) -> List[Hotel]:
    """Best-effort parse of the hotels-com-provider response."""
    rows = (payload.get("properties")
            or payload.get("data", {}).get("body", {}).get("searchResults", {}).get("results")
            or [])
    hotels: List[Hotel] = []
    for r in rows[:10]:
        try:
            name = r.get("name") or r.get("hotelName") or "Unknown"
            rating_raw = r.get("reviews", {}).get("score") or r.get("starRating") or 4.0
            rating = float(rating_raw) if isinstance(rating_raw, (int, float, str)) else 4.0
            if rating > 5:  # normalize 10-scale → 5-scale
                rating = round(rating / 2, 1)
            price = r.get("price", {}).get("lead", {}).get("amount") or r.get("ratePlan", {}).get("price", {}).get("exactCurrent")
            if not price:
                continue
            hotels.append(Hotel(
                name=str(name),
                rating=float(rating),
                price_per_night=float(price),
                address=r.get("neighborhood", {}).get("name", destination),
                amenities=[],
                distance_from_center_km=None,
                booking_url=f"https://www.booking.com/searchresults.html?ss={destination.replace(' ', '+')}",
            ))
        except (TypeError, ValueError, KeyError):
            continue
    return hotels


@cached(prefix="hotels", ttl=900)
async def search_hotels(destination: str, check_in: str, check_out: str) -> List[Hotel]:
    if _has_real_key():
        try:
            payload = await _call_rapidapi(destination, os.getenv("HOTEL_API_KEY", ""))
            hotels = _parse_rapidapi(payload, destination)
            if hotels:
                hotels.sort(key=lambda h: h.price_per_night)
                if hotels:
                    hotels[0].recommended = True
                logger.info(f"Hotels API returned {len(hotels)} hotel(s) for {destination}.")
                return hotels
            logger.warning("Hotels API returned no usable rows — falling back to synth.")
        except Exception as e:
            logger.warning(f"Hotels API call failed: {e!r} — falling back to synth.")
    else:
        logger.info("Using MOCK hotel data (no Hotel API key).")
    return _synth_hotels(destination)


async def is_available() -> dict:
    if not _has_real_key():
        return {"name": "hotels", "configured": False, "live": False, "note": "no Hotel API key"}
    try:
        await _call_rapidapi("London", os.getenv("HOTEL_API_KEY", ""))
        return {"name": "hotels", "configured": True, "live": True}
    except Exception as e:
        return {"name": "hotels", "configured": True, "live": False, "note": str(e)[:120]}
