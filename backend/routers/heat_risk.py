"""
heat_risk.py — Heat Risk Analysis router (Phase 1)

Endpoint:
    GET /api/heat-risk?city=<name>

Scoring logic (total 0–10, then clamped):
┌─────────────────────────────────────────────────────────────────┐
│ Temperature band              │ Points                          │
│  < 27 °C                      │ 0.0  (comfortable)             │
│  27–32 °C                     │ 2.0  (warm)                    │
│  32–37 °C                     │ 3.5  (hot)                     │
│  37–42 °C                     │ 4.5  (very hot)                │
│  > 42 °C                      │ 5.0  (dangerous)               │
├─────────────────────────────────────────────────────────────────┤
│ Humidity modifier             │ Points                          │
│  < 40 %                       │ +0.0                           │
│  40–60 %                      │ +0.5                           │
│  60–75 %                      │ +1.5                           │
│  > 75 %                       │ +2.5                           │
├─────────────────────────────────────────────────────────────────┤
│ Wind speed modifier           │ Points                          │
│  > 20 km/h                    │ −0.5 (light cooling effect)    │
├─────────────────────────────────────────────────────────────────┤
│ Heat-index bonus              │ Points                          │
│  apparent_temp > temp + 4 °C  │ +0.5                           │
└─────────────────────────────────────────────────────────────────┘

Final score → level:
  0.0–3.0  → Low      (green)
  3.1–5.5  → Moderate (yellow)
  5.6–7.5  → High     (orange)
  7.6–10.0 → Extreme  (red)
"""

from fastapi import APIRouter, Query
from services.weather_service import geocode_city, fetch_current_weather

router = APIRouter(prefix="/api/heat-risk", tags=["Heat Risk"])


# ── Score explanation (pure, no formula change) ───────────────────────────────

def _build_score_explanation(
    temperature: float,
    apparent_temperature: float,
    humidity: float,
    wind_speed: float,
    score: float,
) -> dict:
    """
    Return a plain breakdown of how the score was assembled from its four
    components, derived from the *same* inputs already used by compute_heat_score.
    No new computation — only surfaces what the scoring formula already did.
    """
    # Mirror the exact same band logic as compute_heat_score — no changes.
    if temperature < 27:
        temp_pts = 0.0
        temp_band = "< 27 °C (comfortable)"
    elif temperature < 32:
        temp_pts = 2.0
        temp_band = "27–32 °C (warm)"
    elif temperature < 37:
        temp_pts = 3.5
        temp_band = "32–37 °C (hot)"
    elif temperature < 42:
        temp_pts = 4.5
        temp_band = "37–42 °C (very hot)"
    else:
        temp_pts = 5.0
        temp_band = "> 42 °C (dangerous)"

    if humidity < 40:
        hum_pts = 0.0
    elif humidity < 60:
        hum_pts = 0.5
    elif humidity < 75:
        hum_pts = 1.5
    else:
        hum_pts = 2.5

    wind_pts = -0.5 if wind_speed > 20 else 0.0
    hi_bonus = 0.5 if apparent_temperature > temperature + 4 else 0.0

    return {
        "temperature_points": temp_pts,
        "temperature_band":   temp_band,
        "humidity_points":    hum_pts,
        "wind_reduction":     wind_pts,
        "heat_index_bonus":   hi_bonus,
        "total":              score,
        "note": (
            "Heuristic score only — not a validated scientific index. "
            "Temperature band is the dominant factor (0–5 pts); "
            "humidity adds 0–2.5 pts; wind > 20 km/h gives −0.5 pts; "
            "apparent temperature well above actual adds 0.5 pts."
        ),
    }

# ── Recommendations library ───────────────────────────────────────────────────
# Each level maps to a short list of practical, actionable tips.
_RECOMMENDATIONS: dict[str, list[str]] = {
    "Low": [
        "Conditions are comfortable. Normal outdoor activity is fine.",
        "Stay hydrated — drink water regularly even if you don't feel thirsty.",
        "Apply sunscreen (SPF 30+) if spending extended time outdoors.",
    ],
    "Moderate": [
        "Limit strenuous outdoor activity, especially between 11 AM and 3 PM.",
        "Drink at least 2–3 litres of water throughout the day.",
        "Wear light-coloured, loose-fitting clothing and a hat.",
        "Seek shade during peak sun hours.",
        "Check on elderly neighbours or young children who may be vulnerable.",
    ],
    "High": [
        "Avoid outdoor exposure between 11 AM and 4 PM if possible.",
        "Drink water every 30 minutes — do not wait until you feel thirsty.",
        "Never leave children or pets in parked vehicles.",
        "Use wet towels or cool water on wrists and neck to reduce body temperature.",
        "Watch for heat exhaustion signs: heavy sweating, weakness, cold/pale skin, nausea.",
        "Close curtains and blinds on sun-facing windows to keep indoors cool.",
    ],
    "Extreme": [
        "STAY INDOORS in air-conditioned or well-ventilated spaces.",
        "Drink at least 4 litres of water; include ORS or electrolyte drinks.",
        "Avoid ALL outdoor activity — risk of heatstroke is very high.",
        "Heatstroke warning: if someone stops sweating, has hot/red/dry skin, "
        "or loses consciousness, call 108 (emergency) immediately.",
        "Wet your clothing and use fans to aid evaporative cooling.",
        "Elderly people, infants, and outdoor workers are at greatest risk — check on them.",
        "Local cooling centres / community halls may be open — find your nearest one.",
    ],
}


# ── Scoring function (pure, easily unit-tested) ───────────────────────────────

def compute_heat_score(
    temperature: float,
    apparent_temperature: float,
    humidity: float,
    wind_speed: float,
) -> tuple[float, str, str]:
    """
    Compute a heat-exposure risk score from weather variables.

    Returns:
        (score, level, color)  e.g. (6.5, "High", "orange")
    """
    score = 0.0

    # 1. Temperature band (dominant component, 0–5 pts)
    if temperature < 27:
        score += 0.0
    elif temperature < 32:
        score += 2.0
    elif temperature < 37:
        score += 3.5
    elif temperature < 42:
        score += 4.5
    else:
        score += 5.0

    # 2. Humidity modifier (0–2.5 pts)
    if humidity < 40:
        score += 0.0
    elif humidity < 60:
        score += 0.5
    elif humidity < 75:
        score += 1.5
    else:
        score += 2.5

    # 3. Wind speed modifier (slight cooling relief)
    if wind_speed > 20:
        score -= 0.5

    # 4. Heat-index bonus (apparent temperature well above actual = more stress)
    if apparent_temperature > temperature + 4:
        score += 0.5

    # Clamp to [0, 10]
    score = max(0.0, min(10.0, score))
    score = round(score, 1)

    # Map score to level + UI colour
    if score <= 3.0:
        level, color = "Low", "green"
    elif score <= 5.5:
        level, color = "Moderate", "yellow"
    elif score <= 7.5:
        level, color = "High", "orange"
    else:
        level, color = "Extreme", "red"

    return score, level, color


# ── Endpoint ──────────────────────────────────────────────────────────────────

@router.get(
    "",
    summary="Analyse heat-exposure risk for a city",
    response_description="Weather data, risk score, level, and safety recommendations",
)
def get_heat_risk(
    city: str = Query(
        ...,
        min_length=2,
        max_length=100,
        description="Name of an Indian city, e.g. 'Hyderabad', 'Delhi', 'Chennai'",
        examples=["Hyderabad", "Delhi", "Chennai"],
    )
):
    """
    1. Geocode the city name → latitude & longitude (Open-Meteo Geocoding API).
    2. Fetch current weather variables (Open-Meteo Forecast API).
    3. Compute a heat-exposure risk score (0–10) and safety level.
    4. Return structured JSON with weather data, risk, and recommendations.
    """
    # Step 1 — Geocode
    location = geocode_city(city)

    # Step 2 — Weather (includes hourly list via weather["hourly"])
    weather = fetch_current_weather(location["latitude"], location["longitude"])

    # Step 3 — Score
    score, level, color = compute_heat_score(
        temperature=weather["temperature"],
        apparent_temperature=weather["apparent_temperature"],
        humidity=weather["humidity"],
        wind_speed=weather["wind_speed"],
    )

    # Step 4 — Score explanation (surfaces the formula breakdown; no new logic)
    score_explanation = _build_score_explanation(
        temperature=weather["temperature"],
        apparent_temperature=weather["apparent_temperature"],
        humidity=weather["humidity"],
        wind_speed=weather["wind_speed"],
        score=score,
    )

    # Step 5 — Respond
    # weather["hourly"] is a list[dict] or [] — passed through as "forecast"
    return {
        "city": location["city_name"],
        "state": location["admin1"],
        "country": location["country"],
        "latitude": location["latitude"],
        "longitude": location["longitude"],
        # alias_note is non-null when the user typed an old/alternate name,
        # e.g. "Bangalore → Bengaluru". The frontend displays a clarification.
        "alias_note": location.get("alias_note"),
        "weather": {
            "temperature":          weather["temperature"],
            "apparent_temperature": weather["apparent_temperature"],
            "humidity":             weather["humidity"],
            "wind_speed":           weather["wind_speed"],
        },
        "risk": {
            "score": score,
            "level": level,
            "color": color,
        },
        "score_explanation": score_explanation,
        "forecast": weather.get("hourly", []),
        "recommendations": _RECOMMENDATIONS[level],
    }
