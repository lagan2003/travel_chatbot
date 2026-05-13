"""
Weather service.
Attempts a real OpenWeatherMap 5-day/3-hour forecast call. Caches results.
Falls back to deterministic mock data if the key/key-host is missing or fails.
"""

import os
import logging
from collections import defaultdict
from datetime import datetime, timedelta
from typing import List

import httpx

from models.schemas import WeatherForecast
from services.cache import cached, http_retry

logger = logging.getLogger(__name__)

OWM_FORECAST_URL = "https://api.openweathermap.org/data/2.5/forecast"


def _has_real_key() -> bool:
    k = os.getenv("GOOGLE_WEATHER_API_KEY", "")
    return bool(k) and k not in {"your_google_weather_api_key", "your_openweather_api_key", "mock"}


@http_retry
async def _call_openweather(destination: str, api_key: str) -> dict:
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            OWM_FORECAST_URL,
            params={"q": destination, "appid": api_key, "units": "metric"},
            timeout=10.0,
        )
        resp.raise_for_status()
        return resp.json()


def _aggregate_to_daily(payload: dict, start_date: str, duration_days: int) -> List[WeatherForecast]:
    """OWM returns 3-hour slots. Bucket by day, take min/max/mode-condition."""
    by_day: dict[str, dict] = defaultdict(lambda: {"highs": [], "lows": [], "conds": []})
    for entry in payload.get("list", []):
        dt_txt = entry.get("dt_txt", "")
        date = dt_txt.split(" ")[0]
        main = entry.get("main", {})
        weather = (entry.get("weather") or [{}])[0]
        by_day[date]["highs"].append(main.get("temp_max", main.get("temp", 0)))
        by_day[date]["lows"].append(main.get("temp_min", main.get("temp", 0)))
        cond = weather.get("main") or "Clear"
        by_day[date]["conds"].append(cond)

    try:
        start = datetime.strptime(start_date, "%Y-%m-%d")
    except (ValueError, TypeError):
        start = datetime.now()

    out: List[WeatherForecast] = []
    for i in range(max(1, duration_days)):
        d = (start + timedelta(days=i)).strftime("%Y-%m-%d")
        bucket = by_day.get(d)
        if bucket and bucket["highs"]:
            cond = max(set(bucket["conds"]), key=bucket["conds"].count)
            out.append(WeatherForecast(
                date=d,
                temperature_high=round(max(bucket["highs"]), 1),
                temperature_low=round(min(bucket["lows"]), 1),
                conditions=cond,
            ))
        else:
            out.append(_synth_day(d, i))
    return out


def _synth_day(date_str: str, idx: int) -> WeatherForecast:
    conditions = ["Sunny", "Partly Cloudy", "Light Rain", "Clear", "Cloudy"]
    return WeatherForecast(
        date=date_str,
        temperature_high=25.0 + (idx % 5),
        temperature_low=15.0 + (idx % 3),
        conditions=conditions[idx % len(conditions)],
    )


def _mock_weather(start_date_str: str, duration_days: int) -> List[WeatherForecast]:
    try:
        start = datetime.strptime(start_date_str, "%Y-%m-%d")
    except (ValueError, TypeError):
        start = datetime.now()
    return [
        _synth_day((start + timedelta(days=i)).strftime("%Y-%m-%d"), i)
        for i in range(max(1, duration_days))
    ]


@cached(prefix="weather", ttl=1800)
async def get_weather(destination: str, start_date: str, duration_days: int) -> List[WeatherForecast]:
    """Fetch a daily forecast for `destination` over `duration_days`."""
    if not _has_real_key():
        logger.info("Using MOCK weather data (no OpenWeatherMap key).")
        return _mock_weather(start_date, duration_days)

    api_key = os.getenv("GOOGLE_WEATHER_API_KEY", "")
    try:
        payload = await _call_openweather(destination, api_key)
        forecasts = _aggregate_to_daily(payload, start_date, duration_days)
        if forecasts:
            logger.info(f"OpenWeather returned {len(forecasts)} day(s) for {destination}.")
            return forecasts
        logger.warning("OpenWeather returned no usable rows — falling back to mock.")
    except httpx.HTTPStatusError as e:
        logger.warning(f"OpenWeather HTTP {e.response.status_code}: {e.response.text[:120]} — using mock.")
    except Exception as e:
        logger.warning(f"OpenWeather call failed: {e!r} — using mock.")

    return _mock_weather(start_date, duration_days)


async def is_available() -> dict:
    """Health probe used by /status."""
    if not _has_real_key():
        return {"name": "weather", "configured": False, "live": False, "note": "no API key"}
    try:
        await _call_openweather("London", os.getenv("GOOGLE_WEATHER_API_KEY", ""))
        return {"name": "weather", "configured": True, "live": True}
    except Exception as e:
        return {"name": "weather", "configured": True, "live": False, "note": str(e)[:120]}
