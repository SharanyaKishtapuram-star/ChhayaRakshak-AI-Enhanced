"""
weather_service.py — Open-Meteo API wrapper (Phase 1, enhanced)

Two free, no-key-required APIs are used:
  1. Open-Meteo Geocoding API  — converts a place name to lat/lon
  2. Open-Meteo Forecast API   — fetches current weather variables

Key improvements over the original:
  • Fetches top-5 candidates and prefers results in India over other countries.
  • Applies an alias map for old/alternate names (Bombay→Mumbai, etc.) and
    common English spelling variants (Bangalore→Bengaluru).
  • Detects Indian state names and returns a 422 with guidance instead of 404.
  • Trims and normalises whitespace/casing before querying.
  • Returns richer error messages that tell the user what to try instead.
"""

import httpx
from fastapi import HTTPException

# ── API base URLs ────────────────────────────────────────────────────────────
GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
WEATHER_URL   = "https://api.open-meteo.com/v1/forecast"

# Weather variables requested from Open-Meteo
CURRENT_VARS = [
    "temperature_2m",         # actual air temperature (°C)
    "apparent_temperature",   # feels-like / heat index (°C)
    "relative_humidity_2m",   # relative humidity (%)
    "wind_speed_10m",         # wind speed at 10 m (km/h)
]

# Hourly variables for the forecast timeline
HOURLY_VARS = [
    "temperature_2m",         # hourly air temperature (°C)
    "apparent_temperature",   # hourly feels-like temperature (°C)
]

REQUEST_TIMEOUT = 10

# ── Alias map: old / alternate / misspelled names → canonical modern name ────
# Keys must be lowercase. Values are the canonical spelling Open-Meteo knows.
_ALIASES: dict[str, str] = {
    # Renamed cities
    "bombay":        "Mumbai",
    "calcutta":      "Kolkata",
    "madras":        "Chennai",
    "allahabad":     "Prayagraj",
    "benares":       "Varanasi",
    "bangalore":     "Bengaluru",
    "mysore":        "Mysuru",
    "cuttack":       "Cuttack",   # already correct, keep for safety
    "pondicherry":   "Puducherry",
    "trivandrum":    "Thiruvananthapuram",
    "calicut":       "Kozhikode",
    "trichur":       "Thrissur",
    "cochin":        "Kochi",
    "poona":         "Pune",
    "baroda":        "Vadodara",
    "simla":         "Shimla",
    "mussoorie":     "Mussoorie",  # already correct
    "ooty":          "Udhagamandalam",
    "ujjain":        "Ujjain",     # already correct
    # Common English respellings
    "new delhi":     "Delhi",
    "new bombay":    "Navi Mumbai",
    "navi mumbai":   "Navi Mumbai",
}

# ── Indian state names (used to detect state-name queries) ───────────────────
# All lowercase. When a query matches one of these and geocoding finds nothing,
# we return a helpful 422 instead of a generic 404.
_INDIAN_STATES: set[str] = {
    "andhra pradesh", "arunachal pradesh", "assam", "bihar", "chhattisgarh",
    "goa", "gujarat", "haryana", "himachal pradesh", "jharkhand",
    "karnataka", "kerala", "madhya pradesh", "maharashtra", "manipur",
    "meghalaya", "mizoram", "nagaland", "odisha", "punjab",
    "rajasthan", "sikkim", "tamil nadu", "telangana", "tripura",
    "uttar pradesh", "uttarakhand", "west bengal",
    # Union territories
    "delhi", "jammu and kashmir", "ladakh", "chandigarh",
    "puducherry", "andaman and nicobar", "lakshadweep",
    "dadra and nagar haveli", "daman and diu",
}

# Representative cities for each state — shown in guidance when user enters a state name.
_STATE_CAPITAL: dict[str, str] = {
    "andhra pradesh":   "Visakhapatnam",
    "arunachal pradesh":"Itanagar",
    "assam":            "Guwahati",
    "bihar":            "Patna",
    "chhattisgarh":     "Raipur",
    "goa":              "Panaji",
    "gujarat":          "Ahmedabad",
    "haryana":          "Gurugram",
    "himachal pradesh": "Shimla",
    "jharkhand":        "Ranchi",
    "karnataka":        "Bengaluru",
    "kerala":           "Kochi",
    "madhya pradesh":   "Bhopal",
    "maharashtra":      "Mumbai",
    "manipur":          "Imphal",
    "meghalaya":        "Shillong",
    "mizoram":          "Aizawl",
    "nagaland":         "Kohima",
    "odisha":           "Bhubaneswar",
    "punjab":           "Chandigarh",
    "rajasthan":        "Jaipur",
    "sikkim":           "Gangtok",
    "tamil nadu":       "Chennai",
    "telangana":        "Hyderabad",
    "tripura":          "Agartala",
    "uttar pradesh":    "Lucknow",
    "uttarakhand":      "Dehradun",
    "west bengal":      "Kolkata",
    "delhi":            "Delhi",
    "jammu and kashmir":"Srinagar",
    "ladakh":           "Leh",
    "chandigarh":       "Chandigarh",
    "puducherry":       "Puducherry",
    "andaman and nicobar":"Port Blair",
    "lakshadweep":      "Kavaratti",
    "dadra and nagar haveli":"Silvassa",
    "daman and diu":    "Daman",
}


def _normalise(query: str) -> tuple[str, str | None]:
    """
    Strip surrounding whitespace, collapse internal whitespace, and check the
    alias map.

    Returns:
        (canonical_query, alias_note)
        alias_note is None if no substitution was made, or a human-readable
        string like "Bangalore → Bengaluru" if it was.
    """
    cleaned = " ".join(query.strip().split())   # collapse internal spaces
    lower   = cleaned.lower()
    if lower in _ALIASES:
        canonical  = _ALIASES[lower]
        alias_note = f"{cleaned} → {canonical}"
        return canonical, alias_note
    return cleaned, None


def geocode_city(city: str) -> dict:
    """
    Convert a place name to latitude and longitude using the Open-Meteo
    Geocoding API, with India-preference ranking.

    Strategy:
      1. Normalise the query (whitespace, alias substitution).
      2. Fetch up to 5 candidates from Open-Meteo.
      3. Among the candidates, prefer any result whose country is India.
         If no India result exists, use the global top result.
      4. If no results at all, check whether the query is an Indian state name
         and return a 422 with guidance; otherwise return a 404.

    Returns a dict with keys:
        city_name, latitude, longitude, country, admin1,
        query_used (what was actually searched),
        alias_note (None or "old → new" string).

    Raises:
        HTTP 404 if the place cannot be found.
        HTTP 422 if the query is an Indian state name (needs a city).
        HTTP 502 if the upstream API is unreachable.
    """
    canonical, alias_note = _normalise(city)

    try:
        response = httpx.get(
            GEOCODING_URL,
            params={
                "name":     canonical,
                "count":    5,          # fetch more so we can prefer India
                "language": "en",
                "format":   "json",
            },
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()
    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=502,
            detail=(
                "Could not reach the geocoding service. "
                "Please check your internet connection and try again."
            ),
        )

    data    = response.json()
    results = data.get("results") or []

    if not results:
        # No match at all — check if it's a state name
        lower = canonical.lower()
        if lower in _INDIAN_STATES:
            capital = _STATE_CAPITAL.get(lower, "a major city")
            raise HTTPException(
                status_code=422,
                detail=(
                    f"'{canonical}' is a state/territory, not a city. "
                    f"Please enter a specific city, e.g. '{capital}'."
                ),
            )
        raise HTTPException(
            status_code=404,
            detail=(
                f"'{canonical}' could not be found. "
                "Check the spelling or try a nearby major city. "
                "Tip: use the modern name (e.g. 'Bengaluru' instead of 'Bangalore', "
                "'Mumbai' instead of 'Bombay')."
            ),
        )

    # Prefer India results; fall back to global top
    india_results = [r for r in results if r.get("country") == "India"]
    chosen = india_results[0] if india_results else results[0]

    return {
        "city_name":  chosen.get("name", canonical),
        "latitude":   chosen["latitude"],
        "longitude":  chosen["longitude"],
        "country":    chosen.get("country", ""),
        "admin1":     chosen.get("admin1", ""),    # state / province
        "query_used": canonical,
        "alias_note": alias_note,
    }


def fetch_current_weather(latitude: float, longitude: float) -> dict:
    """
    Fetch current weather and today's hourly forecast for a lat/lon pair
    from the Open-Meteo Forecast API (single HTTP request).

    Returns a dict with keys:
        temperature, apparent_temperature, humidity, wind_speed
            — current observations, unchanged from before.
        hourly
            — list of up to 24 dicts, each with:
                  time (ISO-8601 string, IST), temperature, apparent_temperature.
              Returns [] if the hourly block is absent or malformed so that
              callers are never broken by a missing forecast.

    Raises HTTP 502 if the upstream API is unreachable or returns bad data.
    """
    try:
        response = httpx.get(
            WEATHER_URL,
            params={
                "latitude":      latitude,
                "longitude":     longitude,
                "current":       ",".join(CURRENT_VARS),
                "hourly":        ",".join(HOURLY_VARS),
                "timezone":      "Asia/Kolkata",
                "forecast_days": 1,
            },
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()
    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=502,
            detail=(
                "Could not reach the weather service. "
                "Please check your internet connection and try again."
            ),
        )

    data = response.json()

    try:
        current = data["current"]
        current_result = {
            "temperature":          current["temperature_2m"],
            "apparent_temperature": current["apparent_temperature"],
            "humidity":             current["relative_humidity_2m"],
            "wind_speed":           current["wind_speed_10m"],
        }
    except (KeyError, TypeError) as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Unexpected response format from the weather service: {exc}",
        )

    # Parse hourly forecast — fail gracefully with [] rather than raising.
    hourly_result: list[dict] = []
    try:
        h = data["hourly"]
        times       = h["time"]
        temps       = h["temperature_2m"]
        feels_like  = h["apparent_temperature"]
        hourly_result = [
            {
                "time":                 times[i],
                "temperature":          temps[i],
                "apparent_temperature": feels_like[i],
            }
            for i in range(len(times))
        ]
    except (KeyError, TypeError, IndexError):
        hourly_result = []

    return {**current_result, "hourly": hourly_result}
