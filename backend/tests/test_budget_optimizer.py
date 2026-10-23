"""
test_budget_optimizer.py — Phase 5 backend tests

All tests are purely local — no network, no mocking needed.
"""
import pytest
from fastapi.testclient import TestClient
from main import app
from routers.budget_optimizer import _optimize, _CATALOGUE

client = TestClient(app)


# ── Unit tests: _optimize() ───────────────────────────────────────────────────

class TestOptimizeFunction:

    def test_returns_non_empty_for_large_budget(self):
        selected, cost, score = _optimize(50.0, "mixed")
        assert len(selected) > 0
        assert cost <= 50.0
        assert score > 0

    def test_cost_does_not_exceed_budget(self):
        for budget in [1.0, 5.0, 10.0, 50.0, 100.0]:
            selected, cost, _ = _optimize(budget, "mixed")
            assert cost <= budget + 0.01   # float tolerance

    def test_returns_empty_for_tiny_budget(self):
        selected, cost, score = _optimize(0.1, "residential")
        assert len(selected) == 0
        assert cost == 0.0
        assert score == 0

    def test_area_type_filters_applicable_interventions(self):
        # "park" area should not include "cool_roof" (not in park list)
        selected, _, _ = _optimize(100.0, "park")
        selected_ids = {i["id"] for i in selected}
        assert "cool_roof" not in selected_ids

    def test_greedy_picks_high_value_density_first(self):
        # tree_planting: score=4, cost=0.5 → density=8.0 (highest)
        # With a budget of 0.5 we can only afford tree_planting
        selected, _, _ = _optimize(0.5, "mixed")
        assert len(selected) == 1
        assert selected[0]["id"] == "tree_planting"

    def test_all_area_types_work(self):
        for area in ("residential", "commercial", "mixed", "park"):
            selected, cost, score = _optimize(20.0, area)
            # Should always find something in a ₹20L budget
            assert len(selected) > 0


# ── Endpoint tests: POST /api/budget/optimize ────────────────────────────────

class TestBudgetEndpoint:

    def test_valid_request_returns_200(self):
        response = client.post("/api/budget/optimize", json={
            "budget_lakhs": 10.0,
            "area_type": "mixed",
            "city": "Hyderabad",
        })
        assert response.status_code == 200

    def test_response_has_required_fields(self):
        response = client.post("/api/budget/optimize", json={
            "budget_lakhs": 10.0,
            "area_type": "mixed",
        })
        data = response.json()
        for key in ("selected_interventions", "total_cost_lakhs", "budget_lakhs",
                    "remaining_lakhs", "total_cooling_score",
                    "expected_temp_reduction_c", "roi_summary", "all_interventions"):
            assert key in data, f"Missing key: {key}"

    def test_cost_within_budget(self):
        response = client.post("/api/budget/optimize", json={
            "budget_lakhs": 15.0,
            "area_type": "residential",
        })
        data = response.json()
        assert data["total_cost_lakhs"] <= data["budget_lakhs"]

    def test_remaining_equals_budget_minus_cost(self):
        response = client.post("/api/budget/optimize", json={
            "budget_lakhs": 20.0,
            "area_type": "commercial",
        })
        data = response.json()
        expected = round(data["budget_lakhs"] - data["total_cost_lakhs"], 2)
        assert abs(data["remaining_lakhs"] - expected) < 0.01

    def test_expected_temp_reduction_positive(self):
        response = client.post("/api/budget/optimize", json={
            "budget_lakhs": 10.0,
            "area_type": "park",
        })
        assert response.json()["expected_temp_reduction_c"] > 0

    def test_too_small_budget_returns_400(self):
        response = client.post("/api/budget/optimize", json={
            "budget_lakhs": 0.01,
            "area_type": "residential",
        })
        assert response.status_code == 400

    def test_zero_budget_returns_422(self):
        response = client.post("/api/budget/optimize", json={
            "budget_lakhs": 0,
            "area_type": "mixed",
        })
        assert response.status_code == 422   # pydantic gt=0 validation

    def test_invalid_area_type_returns_422(self):
        response = client.post("/api/budget/optimize", json={
            "budget_lakhs": 10.0,
            "area_type": "rooftop",   # not a valid Literal
        })
        assert response.status_code == 422

    def test_all_interventions_have_selected_flag(self):
        response = client.post("/api/budget/optimize", json={
            "budget_lakhs": 5.0,
            "area_type": "mixed",
        })
        for item in response.json()["all_interventions"]:
            assert "selected" in item
            assert isinstance(item["selected"], bool)
