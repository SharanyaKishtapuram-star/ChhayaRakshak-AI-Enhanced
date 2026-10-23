"""
budget_optimizer.py — Cooling Intervention Budget Optimizer (Phase 5)

Endpoint:
    POST /api/budget/optimize

Uses a local greedy knapsack algorithm (no OR-Tools, no external API).
The intervention catalogue is hardcoded with realistic Indian cost and
cooling-impact estimates. All computation is done in Python — no network calls.

Request body:
    {
      "budget_lakhs": 10.0,        ← budget in Indian Rupees Lakhs (1 Lakh = 100,000 ₹)
      "area_type": "residential",  ← residential | commercial | mixed | park
      "city": "Hyderabad"          ← optional, used for context in output
    }

Response:
    {
      "selected_interventions": [...],
      "total_cost_lakhs": 9.5,
      "total_cooling_score": 18,
      "expected_temp_reduction_c": 2.1,
      "roi_summary": "...",
      "all_interventions": [...]  ← full catalogue with selected flags
    }

Scoring logic:
    Each intervention has a cost_lakhs and a cooling_score (1–10).
    We use a greedy approach: sort by cooling_score/cost_lakhs (value density),
    then pick interventions until budget is exhausted.
    Expected temperature reduction is estimated at 0.12 °C per cooling point.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Literal

router = APIRouter(prefix="/api/budget", tags=["Budget Optimizer"])


# ── Intervention catalogue ────────────────────────────────────────────────────
# cost_lakhs: cost in Indian Rupees Lakhs per unit
# cooling_score: 1–10 heat reduction effectiveness
# units: what one "unit" of this intervention represents
# applicable: which area types this intervention suits

_CATALOGUE = [
    {
        "id": "tree_planting",
        "name": "Tree Planting (per 10 trees)",
        "description": "Native shade trees along roads and open spaces. Each 10-tree cluster provides canopy cover and evaporative cooling.",
        "cost_lakhs": 0.5,
        "cooling_score": 4,
        "units": "cluster of 10 trees",
        "applicable": ["residential", "commercial", "mixed", "park"],
        "co_benefits": "Air purification, biodiversity, carbon sequestration",
        "image_tag": "tree_planting",
    },
    {
        "id": "cool_roof",
        "name": "Cool Roof Coating (per 500 m²)",
        "description": "Reflective white or light-coloured roof coating reduces roof surface temperature by 20–30 °C.",
        "cost_lakhs": 1.5,
        "cooling_score": 5,
        "units": "500 m² roof area",
        "applicable": ["residential", "commercial", "mixed"],
        "co_benefits": "Reduced AC load, lower electricity bills",
        "image_tag": "cool_roof",
    },
    {
        "id": "shade_sails",
        "name": "Shade Sails / Pergolas (per installation)",
        "description": "Tensile fabric shades over pedestrian areas, markets, and bus stops.",
        "cost_lakhs": 2.0,
        "cooling_score": 5,
        "units": "installation covering ~200 m²",
        "applicable": ["commercial", "mixed", "park"],
        "co_benefits": "Pedestrian comfort, reduced heat illness risk",
        "image_tag": "shade_sails",
    },
    {
        "id": "green_wall",
        "name": "Vertical Green Wall (per 50 m²)",
        "description": "Climbing plants on building facades reduce surface temperature and provide insulation.",
        "cost_lakhs": 3.0,
        "cooling_score": 4,
        "units": "50 m² wall section",
        "applicable": ["residential", "commercial", "mixed"],
        "co_benefits": "Aesthetic improvement, noise reduction",
        "image_tag": "green_wall",
    },
    {
        "id": "misting_station",
        "name": "Misting Station (per unit)",
        "description": "Fine water mist at pedestrian hotspots. Immediate 3–5 °C localised cooling.",
        "cost_lakhs": 1.0,
        "cooling_score": 3,
        "units": "1 misting station",
        "applicable": ["commercial", "mixed", "park"],
        "co_benefits": "Immediate heat relief for pedestrians",
        "image_tag": "misting_station",
    },
    {
        "id": "permeable_paving",
        "name": "Permeable Paving (per 1000 m²)",
        "description": "Replaces impervious surfaces with water-permeable materials. Reduces urban heat island effect by retaining moisture.",
        "cost_lakhs": 8.0,
        "cooling_score": 6,
        "units": "1000 m² surface area",
        "applicable": ["residential", "commercial", "mixed", "park"],
        "co_benefits": "Flood reduction, groundwater recharge",
        "image_tag": "permeable_paving",
    },
    {
        "id": "rooftop_garden",
        "name": "Rooftop Garden (per 200 m²)",
        "description": "Green roof with soil and vegetation. Insulates building and reduces ambient temperature.",
        "cost_lakhs": 5.0,
        "cooling_score": 7,
        "units": "200 m² rooftop",
        "applicable": ["residential", "commercial", "mixed"],
        "co_benefits": "Food production potential, biodiversity, stormwater management",
        "image_tag": "rooftop_garden",
    },
    {
        "id": "urban_park",
        "name": "Urban Park / Green Pocket (per unit)",
        "description": "Convert a vacant lot or parking space into a small green park with trees, grass, and seating.",
        "cost_lakhs": 15.0,
        "cooling_score": 9,
        "units": "one park (~0.5 acres)",
        "applicable": ["residential", "mixed", "park"],
        "co_benefits": "Recreation, mental health, community space",
        "image_tag": "urban_park",
    },
    {
        "id": "cool_pavement",
        "name": "Cool Pavement Coating (per 1000 m²)",
        "description": "Reflective coating on road or pavement surface reduces ground temperature by 5–10 °C.",
        "cost_lakhs": 3.5,
        "cooling_score": 4,
        "units": "1000 m² pavement",
        "applicable": ["residential", "commercial", "mixed"],
        "co_benefits": "Reduced tyre wear, safer driving in heat",
        "image_tag": "cool_pavement",
    },
    {
        "id": "water_body",
        "name": "Water Feature / Pond (per installation)",
        "description": "Small pond, fountain, or water channel. Evaporative cooling lowers nearby air temperature by 2–4 °C.",
        "cost_lakhs": 10.0,
        "cooling_score": 8,
        "units": "one water body (~100 m²)",
        "applicable": ["residential", "park", "mixed"],
        "co_benefits": "Aesthetics, habitat for birds and insects",
        "image_tag": "water_body",
    },
]


# ── Request / Response models ─────────────────────────────────────────────────

class OptimizeRequest(BaseModel):
    budget_lakhs: float = Field(
        ..., gt=0, le=500,
        description="Available budget in Indian Rupees Lakhs (1 Lakh = ₹1,00,000)",
        examples=[10.0]
    )
    area_type: Literal["residential", "commercial", "mixed", "park"] = Field(
        "mixed",
        description="Type of urban area being improved"
    )
    city: str = Field(
        "",
        max_length=100,
        description="City name for context (optional)"
    )


# ── Optimizer ─────────────────────────────────────────────────────────────────

def _optimize(budget: float, area_type: str) -> tuple[list, float, int]:
    """
    Greedy fractional-knapsack selection.

    1. Filter catalogue to interventions applicable for area_type.
    2. Sort by cooling_score / cost_lakhs descending (value density).
    3. Pick whole units until budget is exhausted.

    Returns (selected_list, total_cost, total_score).
    """
    applicable = [
        i for i in _CATALOGUE
        if area_type in i["applicable"]
    ]
    # Sort by value density (cooling per rupee lakh)
    applicable.sort(key=lambda x: x["cooling_score"] / x["cost_lakhs"], reverse=True)

    selected = []
    remaining = budget
    total_score = 0

    for item in applicable:
        if item["cost_lakhs"] <= remaining:
            selected.append(item)
            remaining -= item["cost_lakhs"]
            total_score += item["cooling_score"]

    total_cost = round(budget - remaining, 2)
    return selected, total_cost, total_score


# ── Endpoint ──────────────────────────────────────────────────────────────────

@router.post(
    "/optimize",
    summary="Recommend cooling interventions within a budget",
    response_description="Selected interventions, costs, expected temperature reduction",
)
def optimize_budget(req: OptimizeRequest):
    """
    Select the highest-impact cooling interventions within the given budget
    using a greedy value-density algorithm.

    No external APIs are used — all calculations are local.
    """
    selected, total_cost, total_score = _optimize(req.budget_lakhs, req.area_type)

    if not selected:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Budget of ₹{req.budget_lakhs} Lakhs is too small for any intervention "
                f"in a '{req.area_type}' area. The cheapest intervention costs "
                f"₹{min(i['cost_lakhs'] for i in _CATALOGUE if req.area_type in i['applicable'])} Lakhs."
            ),
        )

    # 0.12 °C per cooling point is a conservative urban heat island mitigation estimate
    expected_temp_reduction = round(total_score * 0.12, 1)

    # Build full catalogue with selected flag for UI
    selected_ids = {i["id"] for i in selected}
    all_interventions = [
        {**item, "selected": item["id"] in selected_ids}
        for item in _CATALOGUE
        if req.area_type in item["applicable"]
    ]

    city_str = f" in {req.city}" if req.city.strip() else ""
    roi_summary = (
        f"Investing ₹{total_cost} Lakhs{city_str} on {len(selected)} cooling intervention(s) "
        f"is estimated to reduce ambient temperature by up to {expected_temp_reduction} °C, "
        f"improving outdoor comfort and reducing heat-illness risk for residents."
    )

    return {
        "selected_interventions": selected,
        "total_cost_lakhs":       total_cost,
        "budget_lakhs":           req.budget_lakhs,
        "remaining_lakhs":        round(req.budget_lakhs - total_cost, 2),
        "total_cooling_score":    total_score,
        "expected_temp_reduction_c": expected_temp_reduction,
        "roi_summary":            roi_summary,
        "area_type":              req.area_type,
        "city":                   req.city,
        "all_interventions":      all_interventions,
    }
