"""
test_geocoding.py — Unit tests for weather_service geocoding logic

All tests that involve network calls mock httpx.get so they:
  - run offline
  - are deterministic
  - are fast

Tests cover:
  1. _normalise()      — whitespace, casing, alias substitution
  2. geocode_city()    — India preference, state detection, error messages
  3. Various Indian cities across all major scenarios from the requirements
"""

import pytest
from unittest.mock import patch, MagicMock
from fastapi import HTTPException

from services.weather_service import _normalise, geocode_city, _ALIASES, _INDIAN_STATES


# ── Helper ────────────────────────────────────────────────────────────────────

def _mock_geocoding_response(results: list) -> MagicMock:
    """Build a mock httpx Response that returns the given result list."""
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = {"results": results} if results else {}
    return mock_resp


def _india_result(name, admin1, lat=17.0, lon=78.0):
    return {"name": name, "admin1": admin1, "country": "India",
            "latitude": lat, "longitude": lon, "feature_code": "PPL"}


def _foreign_result(name, admin1, country, lat=40.0, lon=-74.0):
    return {"name": name, "admin1": admin1, "country": country,
            "latitude": lat, "longitude": lon, "feature_code": "PPL"}


# ── 1. _normalise() tests ─────────────────────────────────────────────────────

class TestNormalise:
    def test_strips_leading_trailing_spaces(self):
        canonical, note = _normalise("  Hyderabad  ")
        assert canonical == "Hyderabad"
        assert note is None

    def test_collapses_internal_spaces(self):
        # "New  Delhi" (double space) → collapses to "New Delhi" → alias fires → "Delhi"
        canonical, note = _normalise("New  Delhi")
        assert canonical == "Delhi"
        assert note == "New Delhi → Delhi"

    def test_alias_bombay_to_mumbai(self):
        canonical, note = _normalise("Bombay")
        assert canonical == "Mumbai"
        assert note == "Bombay → Mumbai"

    def test_alias_bangalore_to_bengaluru(self):
        canonical, note = _normalise("bangalore")
        assert canonical == "Bengaluru"
        assert note == "bangalore → Bengaluru"

    def test_alias_calcutta_to_kolkata(self):
        canonical, note = _normalise("Calcutta")
        assert canonical == "Kolkata"
        assert note == "Calcutta → Kolkata"

    def test_alias_madras_to_chennai(self):
        canonical, note = _normalise("Madras")
        assert canonical == "Chennai"

    def test_alias_mysore_to_mysuru(self):
        canonical, note = _normalise("Mysore")
        assert canonical == "Mysuru"

    def test_alias_poona_to_pune(self):
        canonical, note = _normalise("Poona")
        assert canonical == "Pune"

    def test_alias_simla_to_shimla(self):
        canonical, note = _normalise("Simla")
        assert canonical == "Shimla"

    def test_alias_baroda_to_vadodara(self):
        canonical, note = _normalise("Baroda")
        assert canonical == "Vadodara"

    def test_alias_cochin_to_kochi(self):
        canonical, note = _normalise("Cochin")
        assert canonical == "Kochi"

    def test_alias_trivandrum_to_thiruvananthapuram(self):
        canonical, note = _normalise("Trivandrum")
        assert canonical == "Thiruvananthapuram"

    def test_alias_new_delhi_to_delhi(self):
        canonical, note = _normalise("New Delhi")
        assert canonical == "Delhi"

    def test_no_alias_for_modern_names(self):
        for city in ["Hyderabad", "Chennai", "Mumbai", "Bengaluru", "Kolkata"]:
            canonical, note = _normalise(city)
            assert canonical == city
            assert note is None

    def test_all_alias_keys_are_lowercase(self):
        for key in _ALIASES:
            assert key == key.lower(), f"Alias key '{key}' is not lowercase"


# ── 2. geocode_city() tests ───────────────────────────────────────────────────

class TestGeocodeCityIndiaPreference:
    """When multiple results exist, India should be preferred."""

    def test_prefers_india_over_foreign(self):
        """If Bangalore returns Pakistan first but Bengaluru returns India,
        the alias maps Bangalore→Bengaluru and then India is chosen."""
        mock = _mock_geocoding_response([
            _india_result("Bengaluru", "Karnataka", lat=12.97, lon=77.56),
            _foreign_result("Bangalore Town", "Sindh", "Pakistan"),
        ])
        with patch("services.weather_service.httpx.get", return_value=mock):
            result = geocode_city("Bangalore")   # triggers alias → Bengaluru
        assert result["country"] == "India"
        assert result["city_name"] == "Bengaluru"
        assert result["alias_note"] == "Bangalore → Bengaluru"

    def test_falls_back_to_global_when_no_india(self):
        """If nothing in India exists, the first global result is used."""
        mock = _mock_geocoding_response([
            _foreign_result("Springfield", "Illinois", "United States"),
        ])
        with patch("services.weather_service.httpx.get", return_value=mock):
            result = geocode_city("Springfield")
        assert result["country"] == "United States"

    def test_india_result_not_first_still_preferred(self):
        """India result at position 2 should beat foreign result at position 1."""
        mock = _mock_geocoding_response([
            _foreign_result("Patna", "Scotland", "United Kingdom"),
            _india_result("Patna", "Bihar", lat=25.61, lon=85.14),
        ])
        with patch("services.weather_service.httpx.get", return_value=mock):
            result = geocode_city("Patna")
        assert result["country"] == "India"
        assert result["admin1"] == "Bihar"


class TestGeocodeCityAliases:
    """Alias substitution end-to-end through geocode_city."""

    def test_bombay_resolves_to_mumbai(self):
        mock = _mock_geocoding_response([
            _india_result("Mumbai", "Maharashtra", lat=19.07, lon=72.87),
        ])
        with patch("services.weather_service.httpx.get", return_value=mock):
            result = geocode_city("Bombay")
        assert result["city_name"] == "Mumbai"
        assert result["alias_note"] == "Bombay → Mumbai"

    def test_calcutta_resolves_to_kolkata(self):
        mock = _mock_geocoding_response([
            _india_result("Kolkata", "West Bengal", lat=22.57, lon=88.37),
        ])
        with patch("services.weather_service.httpx.get", return_value=mock):
            result = geocode_city("Calcutta")
        assert result["city_name"] == "Kolkata"
        assert result["alias_note"] == "Calcutta → Kolkata"

    def test_allahabad_resolves_to_prayagraj(self):
        mock = _mock_geocoding_response([
            _india_result("Prayagraj", "Uttar Pradesh", lat=25.46, lon=81.84),
        ])
        with patch("services.weather_service.httpx.get", return_value=mock):
            result = geocode_city("Allahabad")
        assert result["city_name"] == "Prayagraj"


class TestGeocodeCityStateName:
    """State/territory names should return 422 with guidance."""

    def test_telangana_returns_422(self):
        mock = _mock_geocoding_response([])   # no results
        with patch("services.weather_service.httpx.get", return_value=mock):
            with pytest.raises(HTTPException) as exc_info:
                geocode_city("Telangana")
        assert exc_info.value.status_code == 422
        assert "state" in exc_info.value.detail.lower()
        assert "Hyderabad" in exc_info.value.detail

    def test_karnataka_returns_422(self):
        mock = _mock_geocoding_response([])
        with patch("services.weather_service.httpx.get", return_value=mock):
            with pytest.raises(HTTPException) as exc_info:
                geocode_city("Karnataka")
        assert exc_info.value.status_code == 422
        assert "Bengaluru" in exc_info.value.detail

    def test_maharashtra_returns_422(self):
        mock = _mock_geocoding_response([])
        with patch("services.weather_service.httpx.get", return_value=mock):
            with pytest.raises(HTTPException) as exc_info:
                geocode_city("Maharashtra")
        assert exc_info.value.status_code == 422
        assert "Mumbai" in exc_info.value.detail

    def test_rajasthan_returns_422(self):
        mock = _mock_geocoding_response([])
        with patch("services.weather_service.httpx.get", return_value=mock):
            with pytest.raises(HTTPException) as exc_info:
                geocode_city("Rajasthan")
        assert exc_info.value.status_code == 422
        assert "Jaipur" in exc_info.value.detail

    def test_state_name_case_insensitive(self):
        mock = _mock_geocoding_response([])
        with patch("services.weather_service.httpx.get", return_value=mock):
            with pytest.raises(HTTPException) as exc_info:
                geocode_city("TELANGANA")
        assert exc_info.value.status_code == 422


class TestGeocodeCityErrors:
    """Unknown places and API failures return appropriate errors."""

    def test_unknown_place_returns_404(self):
        mock = _mock_geocoding_response([])
        with patch("services.weather_service.httpx.get", return_value=mock):
            with pytest.raises(HTTPException) as exc_info:
                geocode_city("Xyznonexistent")
        assert exc_info.value.status_code == 404
        # Should include a helpful tip
        assert "could not be found" in exc_info.value.detail.lower()

    def test_network_error_returns_502(self):
        import httpx as _httpx
        with patch("services.weather_service.httpx.get",
                   side_effect=_httpx.RequestError("timeout")):
            with pytest.raises(HTTPException) as exc_info:
                geocode_city("Hyderabad")
        assert exc_info.value.status_code == 502

    def test_empty_results_key_handled(self):
        """Geocoding API returning {} (no 'results' key) is treated as not found."""
        mock = MagicMock()
        mock.raise_for_status = MagicMock()
        mock.json.return_value = {}   # no 'results' key at all
        with patch("services.weather_service.httpx.get", return_value=mock):
            with pytest.raises(HTTPException) as exc_info:
                geocode_city("Xyzunknown")
        assert exc_info.value.status_code == 404


class TestGeocodeCityIndianCities:
    """Spot-checks that well-known Indian cities resolve correctly when the API
    returns them. These tests verify the routing logic, not the live API."""

    @pytest.mark.parametrize("city,state", [
        ("Hyderabad",   "Telangana"),
        ("Warangal",    "Telangana"),
        ("Nizamabad",   "Telangana"),
        ("Karimnagar",  "Telangana"),
        ("Gangtok",     "Sikkim"),
        ("Shillong",    "Meghalaya"),
        ("Guwahati",    "Assam"),
        ("Coimbatore",  "Tamil Nadu"),
        ("Mysuru",      "Karnataka"),
        ("Bhopal",      "Madhya Pradesh"),
        ("Patna",       "Bihar"),
        ("Jaipur",      "Rajasthan"),
        ("Lucknow",     "Uttar Pradesh"),
        ("Ahmedabad",   "Gujarat"),
        ("Bengaluru",   "Karnataka"),
        ("Chennai",     "Tamil Nadu"),
        ("Mumbai",      "Maharashtra"),
        ("Delhi",       "National Capital Territory of Delhi"),
        ("Kolkata",     "West Bengal"),
    ])
    def test_indian_city_returns_india(self, city, state):
        mock = _mock_geocoding_response([
            _india_result(city, state),
        ])
        with patch("services.weather_service.httpx.get", return_value=mock):
            result = geocode_city(city)
        assert result["country"] == "India"
        assert result["city_name"] == city
        assert result["alias_note"] is None   # no alias used
