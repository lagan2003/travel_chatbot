"""
NLP extraction utilities for the dedicated Flight & Hotel pages.

Strategy: do cheap regex extraction first (always works, never makes a network
call), then ask the LLM only for the fuzzy bits we couldn't pin down. LLM result
is merged on top of the regex pass; if the LLM fails we still return the regex
extraction.
"""

from __future__ import annotations

import logging
import re
from datetime import datetime, timedelta
from typing import Optional

from models.schemas import FlightQueryExtract, HotelQueryExtract
from services.llm import generate_structured_data

logger = logging.getLogger(__name__)


# ─── Regex helpers ───
# Capture the city + everything after it that looks like a city token; let
# `_trim_city` strip the trailing filler tokens.
_FROM_TO_RE = re.compile(r"\bfrom\s+([\w .\-]+?)\s+to\s+([\w .\-]+?)(?=$|[^\w .\-])", re.IGNORECASE)
_TO_RE      = re.compile(r"\bto\s+([\w .\-]+?)(?=$|[^\w .\-])", re.IGNORECASE)
_IN_RE      = re.compile(r"\b(?:in|at|near)\s+([\w .\-]+?)(?=$|[^\w .\-])", re.IGNORECASE)

# Words that, when seen as the next token, indicate the city name has ended.
_CITY_STOP_TOKENS = {
    "next", "this", "today", "tomorrow", "under", "below", "less", "max", "maximum",
    "with", "without", "in", "on", "at", "near", "by", "before", "after", "for",
    "from", "to", "cheap", "cheapest", "budget", "luxury", "business", "first",
    "economy", "premium", "family", "romantic", "honeymoon", "beach", "kid",
    "pool", "spa", "gym", "breakfast", "wifi", "wi-fi", "parking", "pet", "bar",
    "shuttle", "star", "stars", "night", "nights", "morning", "afternoon",
    "evening", "red-eye", "non-stop", "nonstop", "direct",
    "january", "february", "march", "april", "may", "june", "july", "august",
    "september", "october", "november", "december",
    "jan", "feb", "mar", "apr", "jun", "jul", "aug", "sep", "oct", "nov", "dec",
    "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday",
    "mon", "tue", "wed", "thu", "fri", "sat", "sun",
    "weekend", "week", "month",
    "the",
    "dollar", "dollars", "rupee", "rupees", "euro", "euros", "pound", "pounds",
    "usd", "inr", "eur", "gbp", "yen", "rmb",
}


_DATE_LIKE = re.compile(r"^\d{1,4}([\-/]\d{1,4}){0,2}$")
_CONNECTORS = {"and", "a", "the", "for", "of", "&", "or"}


def _trim_city(name: str) -> str:
    """Drop trailing tokens that are clearly not part of the city name."""
    if not name:
        return name
    tokens = name.strip().split()
    # Iteratively trim from the right while the last token looks like filler.
    while tokens:
        last = tokens[-1].lower().strip(",.;:")
        if (last in _CITY_STOP_TOKENS
                or last in _CONNECTORS
                or _DATE_LIKE.match(last)
                or last.startswith("$")
                or last == ""):
            tokens.pop()
            continue
        break
    return " ".join(tokens).strip(" ,.;:")


def _extract_city(text: str, regex: re.Pattern, group_idx: int = 1) -> str:
    m = regex.search(text)
    if not m:
        return ""
    return _trim_city(m.group(group_idx))
_PRICE_UNDER_RE = re.compile(r"under\s*[₹$€£]?\s*(\d[\d,]*\.?\d*)\s*(k|K|usd|inr|eur|gbp)?", re.IGNORECASE)
_PRICE_BELOW_RE = re.compile(r"(?:less than|below|max(?:imum)?)\s*[₹$€£]?\s*(\d[\d,]*\.?\d*)\s*(k|K)?", re.IGNORECASE)
_RATING_RE = re.compile(r"(\d(?:\.\d)?)\s*[-–\s]?star", re.IGNORECASE)
_DATE_ISO_RE = re.compile(r"\b(20\d{2}-\d{2}-\d{2})\b")


def _parse_price(value: str, suffix: Optional[str]) -> float:
    n = float(value.replace(",", ""))
    if suffix and suffix.lower() == "k":
        n *= 1000
    return n


def _phrase_to_date(phrase: str) -> str:
    """Map a vague date phrase to YYYY-MM-DD (best effort)."""
    p = phrase.lower()
    today = datetime.now()
    if "today" in p:
        return today.strftime("%Y-%m-%d")
    if "tomorrow" in p:
        return (today + timedelta(days=1)).strftime("%Y-%m-%d")
    if "next weekend" in p:
        days_until_sat = (5 - today.weekday()) % 7 + 7
        return (today + timedelta(days=days_until_sat)).strftime("%Y-%m-%d")
    if "this weekend" in p:
        days_until_sat = (5 - today.weekday()) % 7
        return (today + timedelta(days=days_until_sat or 7)).strftime("%Y-%m-%d")
    if "next week" in p:
        return (today + timedelta(days=7)).strftime("%Y-%m-%d")
    if "next month" in p:
        return (today + timedelta(days=30)).strftime("%Y-%m-%d")
    weekdays = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
    for i, wd in enumerate(weekdays):
        if wd in p:
            delta = (i - today.weekday()) % 7
            return (today + timedelta(days=delta or 7)).strftime("%Y-%m-%d")
    return ""


def _detect_time_of_day(q: str) -> str:
    p = q.lower()
    for label in ("morning", "afternoon", "evening", "night"):
        if label in p:
            return label
    if "red-eye" in p or "red eye" in p:
        return "night"
    return ""


def _detect_class(q: str) -> str:
    p = q.lower()
    if "first class" in p or "first-class" in p:
        return "first"
    if "business" in p:
        return "business"
    if "premium econ" in p or "premium-econ" in p:
        return "premium economy"
    if "luxury" in p:
        return "luxury"
    if "budget" in p or "cheap" in p or "cheapest" in p:
        return "budget"
    return "economy"


def _extract_max_price(q: str) -> Optional[float]:
    for re_ in (_PRICE_UNDER_RE, _PRICE_BELOW_RE):
        m = re_.search(q)
        if m:
            return _parse_price(m.group(1), m.group(2) if m.lastindex and m.lastindex >= 2 else None)
    return None


# ─── Flight extraction ───

_FLIGHT_LLM_PROMPT = """Extract a flight search intent from the user query. Return only the schema fields.
- Map vague dates (e.g. "next weekend", "Friday") into both `date_phrase` (raw) and `departure_date` (YYYY-MM-DD).
- `cabin_class` ∈ {{economy, premium economy, business, first}}.
- If the user said "cheap"/"cheapest"/"budget" set cabin_class=economy and infer a low max_price.
- `time_of_day` ∈ {{morning, afternoon, evening, night, ""}}.
- `non_stop` true only if user said "non-stop" / "direct".

User Query: {query}
"""


def extract_flight_query(query: str) -> FlightQueryExtract:
    base = FlightQueryExtract()

    m = _FROM_TO_RE.search(query)
    if m:
        base.source = _trim_city(m.group(1))
        base.destination = _trim_city(m.group(2))
    else:
        dest = _extract_city(query, _TO_RE)
        if dest:
            base.destination = dest

    iso = _DATE_ISO_RE.search(query)
    if iso:
        base.departure_date = iso.group(1)
    base.time_of_day = _detect_time_of_day(query)
    base.cabin_class = _detect_class(query)
    base.max_price = _extract_max_price(query)
    base.non_stop = bool(re.search(r"\b(non[- ]?stop|direct)\b", query, re.IGNORECASE))

    llm_out = generate_structured_data(_FLIGHT_LLM_PROMPT.format(query=query), FlightQueryExtract)
    if llm_out:
        # Prefer regex when present (more reliable), fill gaps from LLM
        merged = base.model_dump()
        for k, v in llm_out.model_dump().items():
            if not merged.get(k) and v:
                merged[k] = v
        base = FlightQueryExtract(**merged)
    else:
        logger.info("Flight NLP: LLM extraction skipped/failed — using regex pass only.")

    if not base.departure_date:
        # Backfill from date_phrase or default to 14 days from now
        if base.date_phrase:
            base.departure_date = _phrase_to_date(base.date_phrase) or ""
        if not base.departure_date:
            base.departure_date = (datetime.now() + timedelta(days=14)).strftime("%Y-%m-%d")

    base.cabin_class = (base.cabin_class or "economy").lower()
    return base


# ─── Hotel extraction ───

_HOTEL_LLM_PROMPT = """Extract a hotel search intent from the user query. Return only the schema fields.
- destination: the city (no country needed).
- amenities: list literal amenities ("pool", "spa", "beachfront", "free wifi", "breakfast", etc.).
- style ∈ {{luxury, budget, business, family, romantic, beach, ""}}.
- max_price_per_night: numeric USD if mentioned.
- min_rating: 0–5 if a star count is mentioned (e.g. "4 star").
- check_in / check_out: YYYY-MM-DD if dates given, else empty.

User Query: {query}
"""

_AMENITY_KEYWORDS = {
    "pool": "Pool", "spa": "Spa", "gym": "Gym", "beach": "Beachfront",
    "breakfast": "Breakfast included", "wifi": "Free WiFi", "wi-fi": "Free WiFi",
    "parking": "Parking", "pet": "Pet friendly", "kid": "Family rooms",
    "family": "Family rooms", "bar": "Bar", "shuttle": "Airport shuttle",
}


def extract_hotel_query(query: str) -> HotelQueryExtract:
    base = HotelQueryExtract()

    base.destination = _extract_city(query, _IN_RE)
    if not base.destination:
        base.destination = _extract_city(query, _TO_RE)

    base.max_price_per_night = _extract_max_price(query)
    rm = _RATING_RE.search(query)
    if rm:
        try:
            base.min_rating = float(rm.group(1))
        except ValueError:
            pass

    q_low = query.lower()
    for kw, label in _AMENITY_KEYWORDS.items():
        if kw in q_low and label not in base.amenities:
            base.amenities.append(label)

    if "luxury" in q_low or "5 star" in q_low or "five star" in q_low:
        base.style = "luxury"
    elif "budget" in q_low or "cheap" in q_low:
        base.style = "budget"
    elif "family" in q_low or "kid" in q_low:
        base.style = "family"
    elif "business" in q_low:
        base.style = "business"
    elif "romantic" in q_low or "honeymoon" in q_low:
        base.style = "romantic"

    iso_dates = _DATE_ISO_RE.findall(query)
    if iso_dates:
        base.check_in = iso_dates[0]
        if len(iso_dates) > 1:
            base.check_out = iso_dates[1]

    llm_out = generate_structured_data(_HOTEL_LLM_PROMPT.format(query=query), HotelQueryExtract)
    if llm_out:
        merged = base.model_dump()
        for k, v in llm_out.model_dump().items():
            if not merged.get(k) and v:
                merged[k] = v
        # union amenities — case-insensitive dedupe, keep original casing
        if llm_out.amenities:
            seen: dict[str, str] = {}
            for a in (*base.amenities, *llm_out.amenities):
                seen.setdefault(a.lower(), a)
            merged["amenities"] = list(seen.values())
        base = HotelQueryExtract(**merged)
    else:
        logger.info("Hotel NLP: LLM extraction skipped/failed — using regex pass only.")

    return base
