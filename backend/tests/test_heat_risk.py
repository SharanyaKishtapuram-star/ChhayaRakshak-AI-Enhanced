"""
test_heat_risk.py — Phase 1 backend tests

Covers:
  1. compute_heat_score() — pure unit tests, no network
  2. GET /api/heat-risk  — endpoint tests with mocked weather service
"""

from unittest.mock import patch
from fastapi.testclient import TestClient
from main import app
from routers.heat_risk import compute_heat_score

client = TestClient(app)


# ── Unit tests: scoring logic ─────────────────────────────────────────────────

class TestComputeHeatScore:
    """All combinations of temperature bands, humidity, wind and heat-index."""

    def test_low_score_cool_dry(self):
        score, level, color = compute_heat_score(
            temperature=22.0, apparent_temperature=21.0, humidity=35.0, wind_speed=10.0
        )
        assert score == 0.0
        assert level == "Low"
        assert color == "green"

    def test_moderate_warm_moderate_humidity(self):
        score, level, color = compute_heat_score(
            temperature=30.0, apparent_temperature=31.0, humidity=55.0, wind_speed=10.0
        )
        # temp=30 → +2.0, humidity=55 → +0.5 = 2.5 → Low boundary, but ≤ 3.0
        assert level == "Low"
        assert score == 2.5

    def test_moderate_band(self):
        score, level, color = compute_heat_score(
            temperature=30.0, apparent_temperature=31.0, humidity=65.0, wind_speed=10.0
        )
        # temp=30 → +2.0, humidity=65 → +1.5 = 3.5 → Moderate
        assert level == "Moderate"
        assert color == "yellow"
        assert score == 3.5

    def test_high_band(self):
        score, level, color = compute_heat_score(
            temperature=35.0, apparent_temperature=36.0, humidity=65.0, wind_speed=10.0
        )
        # temp=35 → +3.5, humidity=65 → +1.5 = 5.0 → Moderate (≤5.5)
        assert level == "Moderate"
        assert score == 5.0

    def test_high_band_with_heat_index(self):
        score, level, color = compute_heat_score(
            temperature=35.0, apparent_temperature=40.0, humidity=65.0, wind_speed=10.0
        )
        # temp=35 → +3.5, humidity=65 → +1.5, apparent bonus +0.5 = 5.5 → Moderate
        assert level == "Moderate"
        assert score == 5.5

    def test_high_level(self):
        score, level, color = compute_heat_score(
            temperature=38.0, apparent_temperature=39.0, humidity=65.0, wind_speed=10.0
        )
        # temp=38 → +4.5, humidity=65 → +1.5 = 6.0 → High
        assert level == "High"
        assert color == "orange"
        assert score == 6.0

    def test_extreme_level(self):
        score, level, color = compute_heat_score(
            temperature=43.0, apparent_temperature=44.0, humidity=80.0, wind_speed=5.0
        )
        # temp=43 → +5.0, humidity=80 → +2.5 = 7.5 → still High (boundary)
        # apparent bonus: 44 > 43+4? No (only +1) → no bonus
        assert level == "High"
        assert score == 7.5

    def test_extreme_level_full(self):
        score, level, color = compute_heat_score(
            temperature=43.0, apparent_temperature=48.0, humidity=80.0, wind_speed=5.0
        )
        # temp=43 → +5.0, humidity=80 → +2.5, apparent 48>43+4 → +0.5 = 8.0 → Extreme
        assert level == "Extreme"
        assert color == "red"
        assert score == 8.0

    def test_wind_cooling_modifier(self):
        score_calm, _, _ = compute_heat_score(
            temperature=35.0, apparent_temperature=36.0, humidity=65.0, wind_speed=10.0
        )
        score_windy, _, _ = compute_heat_score(
            temperature=35.0, apparent_temperature=36.0, humidity=65.0, wind_speed=25.0
        )
        # Windy should score 0.5 less
        assert score_windy == score_calm - 0.5

    def test_score_clamped_at_ten(self):
        score, _, _ = compute_heat_score(
            temperature=50.0, apparent_temperature=60.0, humidity=90.0, wind_speed=0.0
        )
        assert score <= 10.0

    def test_score_clamped_at_zero(self):
        score, _, _ = compute_heat_score(
            temperature=10.0, apparent_temperature=8.0, humidity=20.0, wind_speed=50.0
        )
        assert score >= 0.0


# ── Endpoint tests: mocked weather service ────────────────────────────────────

_MOCK_LOCATION = {
    "city_name":  "Hyderabad",
    "latitude":   17.38,
    "longitude":  78.47,
    "country":    "India",
    "admin1":     "Telangana",
    "query_used": "Hyderabad",
    "alias_note": None,
}

_MOCK_LOCATION_ALIASED = {
    "city_name":  "Mumbai",
    "latitude":   19.07,
    "longitude":  72.87,
    "country":    "India",
    "admin1":     "Maharashtra",
    "query_used": "Mumbai",
    "alias_note": "Bombay → Mumbai",
}

# Two hourly entries are enough — the endpoint zips the lists so we just need
# the structure to match what fetch_current_weather now returns.
_MOCK_HOURLY = [
    {"time": "2024-05-01T10:00", "temperature": 36.0, "apparent_temperature": 38.5},
    {"time": "2024-05-01T11:00", "temperature": 38.0, "apparent_temperature": 40.0},
]

_MOCK_WEATHER_HOT = {
    "temperature": 38.0,
    "apparent_temperature": 40.0,
    "humidity": 70.0,
    "wind_speed": 10.0,
    "hourly": _MOCK_HOURLY,
}


class TestHeatRiskEndpoint:

    def test_successful_response_structure(self):
        with (
            patch("routers.heat_risk.geocode_city", return_value=_MOCK_LOCATION),
            patch("routers.heat_risk.fetch_current_weather", return_value=_MOCK_WEATHER_HOT),
        ):
            response = client.get("/api/heat-risk?city=Hyderabad")

        assert response.status_code == 200
        data = response.json()

        # Top-level keys
        assert data["city"] == "Hyderabad"
        assert data["state"] == "Telangana"
        assert data["country"] == "India"
        assert "weather" in data
        assert "risk" in data
        assert "recommendations" in data

    def test_weather_fields_present(self):
        with (
            patch("routers.heat_risk.geocode_city", return_value=_MOCK_LOCATION),
            patch("routers.heat_risk.fetch_current_weather", return_value=_MOCK_WEATHER_HOT),
        ):
            response = client.get("/api/heat-risk?city=Hyderabad")

        weather = response.json()["weather"]
        assert "temperature" in weather
        assert "apparent_temperature" in weather
        assert "humidity" in weather
        assert "wind_speed" in weather

    def test_risk_fields_present(self):
        with (
            patch("routers.heat_risk.geocode_city", return_value=_MOCK_LOCATION),
            patch("routers.heat_risk.fetch_current_weather", return_value=_MOCK_WEATHER_HOT),
        ):
            response = client.get("/api/heat-risk?city=Hyderabad")

        risk = response.json()["risk"]
        assert "score" in risk
        assert "level" in risk
        assert "color" in risk
        assert risk["level"] in ("Low", "Moderate", "High", "Extreme")

    def test_recommendations_non_empty(self):
        with (
            patch("routers.heat_risk.geocode_city", return_value=_MOCK_LOCATION),
            patch("routers.heat_risk.fetch_current_weather", return_value=_MOCK_WEATHER_HOT),
        ):
            response = client.get("/api/heat-risk?city=Hyderabad")

        recs = response.json()["recommendations"]
        assert isinstance(recs, list)
        assert len(recs) > 0

    def test_forecast_field_present_and_is_list(self):
        """Response must include 'forecast' as a list (may be empty)."""
        with (
            patch("routers.heat_risk.geocode_city", return_value=_MOCK_LOCATION),
            patch("routers.heat_risk.fetch_current_weather", return_value=_MOCK_WEATHER_HOT),
        ):
            response = client.get("/api/heat-risk?city=Hyderabad")

        data = response.json()
        assert "forecast" in data, "Response missing 'forecast' key"
        assert isinstance(data["forecast"], list)
        # With our mock, the two hourly entries should be present
        assert len(data["forecast"]) == 2
        first = data["forecast"][0]
        assert "time" in first
        assert "temperature" in first
        assert "apparent_temperature" in first

    def test_score_explanation_field_present(self):
        """Response must include 'score_explanation' with required keys."""
        with (
            patch("routers.heat_risk.geocode_city", return_value=_MOCK_LOCATION),
            patch("routers.heat_risk.fetch_current_weather", return_value=_MOCK_WEATHER_HOT),
        ):
            response = client.get("/api/heat-risk?city=Hyderabad")

        data = response.json()
        assert "score_explanation" in data, "Response missing 'score_explanation' key"
        se = data["score_explanation"]
        for key in ("temperature_points", "temperature_band", "humidity_points",
                    "wind_reduction", "heat_index_bonus", "total", "note"):
            assert key in se, f"score_explanation missing key: {key}"

    def test_score_explanation_total_matches_risk_score(self):
        """score_explanation['total'] must equal risk['score']."""
        with (
            patch("routers.heat_risk.geocode_city", return_value=_MOCK_LOCATION),
            patch("routers.heat_risk.fetch_current_weather", return_value=_MOCK_WEATHER_HOT),
        ):
            response = client.get("/api/heat-risk?city=Hyderabad")

        data = response.json()
        assert data["score_explanation"]["total"] == data["risk"]["score"]

    def test_forecast_graceful_when_hourly_empty(self):
        """If fetch_current_weather returns hourly=[], forecast must be []."""
        mock_weather_no_hourly = {
            "temperature": 38.0,
            "apparent_temperature": 40.0,
            "humidity": 70.0,
            "wind_speed": 10.0,
            "hourly": [],
        }
        with (
            patch("routers.heat_risk.geocode_city", return_value=_MOCK_LOCATION),
            patch("routers.heat_risk.fetch_current_weather", return_value=mock_weather_no_hourly),
        ):
            response = client.get("/api/heat-risk?city=Hyderabad")

        data = response.json()
        assert response.status_code == 200
        assert data["forecast"] == []

    def test_missing_city_param_returns_422(self):
        """FastAPI should return 422 Unprocessable Entity if city is omitted."""
        response = client.get("/api/heat-risk")
        assert response.status_code == 422

    def test_city_too_short_returns_422(self):
        response = client.get("/api/heat-risk?city=A")
        assert response.status_code == 422

    def test_404_propagated_for_unknown_city(self):
        from fastapi import HTTPException
        with patch(
            "routers.heat_risk.geocode_city",
            side_effect=HTTPException(status_code=404, detail="City not found"),
        ):
            response = client.get("/api/heat-risk?city=Nonexistentcity")
        assert response.status_code == 404

    def test_alias_note_in_response_when_old_name_used(self):
        """When an alias is resolved (e.g. Bombay→Mumbai), alias_note is non-null."""
        with (
            patch("routers.heat_risk.geocode_city", return_value=_MOCK_LOCATION_ALIASED),
            patch("routers.heat_risk.fetch_current_weather", return_value=_MOCK_WEATHER_HOT),
        ):
            response = client.get("/api/heat-risk?city=Bombay")
        assert response.status_code == 200
        data = response.json()
        assert data["city"] == "Mumbai"
        assert data["alias_note"] == "Bombay → Mumbai"

    def test_state_name_returns_422(self):
        """Entering a state name should return 422 with helpful guidance."""
        from fastapi import HTTPException
        with patch(
            "routers.heat_risk.geocode_city",
            side_effect=HTTPException(
                status_code=422,
                detail="'Telangana' is a state/territory, not a city. Please enter a specific city, e.g. 'Hyderabad'.",
            ),
        ):
            response = client.get("/api/heat-risk?city=Telangana")
        assert response.status_code == 422
        assert "Hyderabad" in response.json()["detail"]
