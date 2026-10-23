"""
budget_visualize.py — AI Budget Visualization router

Endpoint:
    POST /api/budget/visualize

Accepts the result of a budget optimization (selected interventions +
area type + optional city) and generates a photorealistic illustration
of what the area could look like after the cooling interventions are
implemented, using the Google Gemini image-generation API.

The image is returned as a base64-encoded PNG/JPEG string so the frontend
can display it with a data: URI — no server-side file storage required.

━━ API used ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  client.models.generate_content(model, contents, config=GenerateContentConfig(
      response_modalities=['IMAGE', 'TEXT']
  ))

  The image bytes are in: response.candidates[0].content.parts[i].inline_data
  where inline_data.mime_type and inline_data.data (bytes) are the outputs.

  NOTE: client.models.generate_images() is Vertex AI / Enterprise-only and
  raises "This method is only supported in Gemini Enterprise Agent Platform
  mode, not in Gemini Developer API mode." with a standard Developer API key.
  The correct path for Developer API keys is generate_content with
  response_modalities=['IMAGE'].

━━ Error handling ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  • No GEMINI_API_KEY              → 503 with setup instructions
  • Quota / rate-limit (429)       → 429 with clear message and wait hint
  • Image filtered by safety AI    → 422 with reason
  • Network error                  → 502
  • Any other Gemini error         → 500

━━ Privacy / security ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  • The prompt is constructed entirely from server-side catalogue labels and
    the user-supplied area type + city strings (both already accepted by the
    existing /api/budget/optimize endpoint).
  • No user health data or session IDs are sent to the image API.
  • The API key is read from GEMINI_API_KEY env var — never returned to client.
"""

import os
import base64
from typing import Literal, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from dotenv import load_dotenv

try:
    from google import genai
    from google.genai import types as gtypes
except ImportError:  # pragma: no cover
    genai = None  # type: ignore[assignment]
    gtypes = None  # type: ignore[assignment]

load_dotenv()

router = APIRouter(prefix="/api/budget", tags=["Budget Optimizer"])


# ── Human-readable labels for the prompt ─────────────────────────────────────
# Maps catalogue IDs to natural-language phrases used to build the image prompt.
_INTERVENTION_PHRASES: dict[str, str] = {
    "tree_planting":    "rows of native shade trees lining the streets",
    "cool_roof":        "buildings with bright reflective white rooftop coatings",
    "shade_sails":      "colourful tensile shade sails over pedestrian walkways",
    "green_wall":       "lush vertical green walls of climbing plants on building facades",
    "misting_station":  "fine-mist cooling stations at street corners",
    "permeable_paving": "light-coloured permeable paving surfaces absorbing rainwater",
    "rooftop_garden":   "rooftop gardens with plants, grass, and small trees",
    "urban_park":       "a vibrant urban pocket park with trees, benches, and greenery",
    "cool_pavement":    "roads and pavements coated with reflective light-coloured material",
    "water_body":       "a small decorative pond or fountain surrounded by greenery",
}

_AREA_CONTEXT: dict[str, str] = {
    "residential": "a residential neighbourhood in an Indian city",
    "commercial":  "a busy commercial district in an Indian city",
    "mixed":       "a mixed-use urban area in an Indian city",
    "park":        "a public park and green space in an Indian city",
}


# ── Pydantic models ───────────────────────────────────────────────────────────

class VisualizeRequest(BaseModel):
    selected_intervention_ids: List[str] = Field(
        ...,
        min_length=1,
        description="List of intervention IDs from the budget optimisation result",
        examples=[["tree_planting", "cool_roof", "shade_sails"]],
    )
    area_type: Literal["residential", "commercial", "mixed", "park"] = Field(
        "mixed",
        description="Area type selected by the user",
    )
    city: Optional[str] = Field(
        None,
        max_length=100,
        description="Optional city name for contextual detail in the prompt",
    )
    expected_temp_reduction_c: Optional[float] = Field(
        None,
        description="Expected temperature reduction — used in prompt for context",
    )


class VisualizeResponse(BaseModel):
    image_base64: str
    mime_type: str
    prompt_used: str
    model_used: str


# ── Helpers ───────────────────────────────────────────────────────────────────

def _build_prompt(req: VisualizeRequest) -> str:
    """
    Construct a detailed, safe image-generation prompt from the
    optimisation result.  All content is derived from the server-side
    catalogue — no user free-text is interpolated.
    """
    phrases = [
        _INTERVENTION_PHRASES[iid]
        for iid in req.selected_intervention_ids
        if iid in _INTERVENTION_PHRASES
    ]

    area_ctx = _AREA_CONTEXT.get(req.area_type, "an urban area in an Indian city")
    city_str = f" in {req.city.strip()}" if req.city and req.city.strip() else ""
    temp_str = (
        f"  The improvements are expected to reduce ambient temperature by "
        f"{req.expected_temp_reduction_c:.1f} °C."
        if req.expected_temp_reduction_c
        else ""
    )

    interventions_text = (
        "\n".join(f"  • {p}" for p in phrases)
        if phrases
        else "  • urban cooling greening interventions"
    )

    prompt = (
        f"A photorealistic digital illustration of {area_ctx}{city_str} "
        f"after urban heat-island cooling interventions have been implemented.\n\n"
        f"The scene shows:\n"
        f"{interventions_text}\n\n"
        f"The overall atmosphere is green, cool, shaded, and pleasant — a transformation "
        f"from a hot, grey urban environment into a liveable, climate-adapted city."
        f"{temp_str}\n\n"
        f"Style: detailed architectural illustration, bright natural lighting, "
        f"realistic proportions, clean and professional, suitable for a government "
        f"urban-planning proposal document."
    )
    return prompt


def _get_gemini_key() -> str:
    """Return the API key or raise a 503 with clear setup instructions."""
    key = os.getenv("GEMINI_API_KEY", "").strip()
    if not key or key == "your_gemini_api_key_here":
        raise HTTPException(
            status_code=503,
            detail=(
                "GEMINI_API_KEY is not configured. "
                "Add your Gemini API key to backend/.env to enable AI visualisation. "
                "Get a free key at https://aistudio.google.com/app/apikey"
            ),
        )
    return key


def _extract_image_part(response) -> tuple[bytes, str]:
    """
    Extract the first image part from a generate_content response.

    The image bytes live at:
        response.candidates[0].content.parts[i].inline_data.data
    with MIME type at:
        response.candidates[0].content.parts[i].inline_data.mime_type

    Returns (image_bytes, mime_type) or raises ValueError if no image found.
    """
    candidates = getattr(response, "candidates", None) or []
    if not candidates:
        raise ValueError("No candidates in response")

    parts = getattr(candidates[0].content, "parts", None) or []
    for part in parts:
        inline = getattr(part, "inline_data", None)
        if inline is not None:
            data = getattr(inline, "data", None)
            mime = getattr(inline, "mime_type", None) or "image/png"
            if data:
                return data, mime

    raise ValueError("No image data found in response parts")


# ── Preferred models (ordered by quality / availability) ─────────────────────
# All entries use generate_content with response_modalities=['IMAGE'].
# generate_images() is Vertex AI only and fails on Developer API keys.
_IMAGE_MODELS = [
    "models/gemini-2.5-flash-image",
    "models/gemini-3.1-flash-image",
    "models/gemini-3.1-flash-lite-image",
    "models/gemini-3-pro-image",
]


# ── Endpoint ─────────────────────────────────────────────────────────────────

@router.post(
    "/visualize",
    response_model=VisualizeResponse,
    summary="Generate an AI visualisation of the cooling interventions",
    response_description="Base64-encoded image, MIME type, and prompt used",
)
def visualize_budget(req: VisualizeRequest):
    """
    Generate a photorealistic illustration of what the selected area would look
    like after the recommended cooling interventions are implemented.

    Uses generate_content with response_modalities=['IMAGE'] — the correct
    Developer API path.  generate_images() is Vertex AI only and is not used.

    Requires GEMINI_API_KEY to be set in backend/.env.
    Returns HTTP 503 with setup instructions if the key is missing.
    Returns HTTP 429 with a wait hint if the free-tier quota is exceeded.
    """
    api_key = _get_gemini_key()
    prompt  = _build_prompt(req)

    if genai is None:  # pragma: no cover
        raise HTTPException(
            status_code=503,
            detail="google-genai package is not installed on this server.",
        )

    last_error: Exception | None = None

    for model_name in _IMAGE_MODELS:
        try:
            client = genai.Client(api_key=api_key)
            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=gtypes.GenerateContentConfig(
                    response_modalities=["IMAGE", "TEXT"],
                ),
            )

            image_bytes, mime_type = _extract_image_part(response)

            image_b64 = base64.b64encode(image_bytes).decode("utf-8")

            return VisualizeResponse(
                image_base64=image_b64,
                mime_type=mime_type,
                prompt_used=prompt,
                model_used=model_name,
            )

        except HTTPException:
            raise  # propagate 503 directly

        except Exception as exc:
            err_str = str(exc).lower()
            last_error = exc

            # Rate limit — return immediately, don't try next model
            if "429" in err_str or "quota" in err_str or "resource_exhausted" in err_str:
                # Try to extract the wait hint from the error message
                import re
                wait_match = re.search(r'retry[^\d]*(\d+h\d+m[\d.]+s|\d+m[\d.]+s|\d+s)', str(exc), re.I)
                wait_hint = f" Please retry in {wait_match.group(1)}." if wait_match else " Please wait a few minutes and try again."
                raise HTTPException(
                    status_code=429,
                    detail=(
                        "Gemini API free-tier quota exceeded for image generation."
                        f"{wait_hint} "
                        "To remove limits, upgrade your Google AI plan at "
                        "https://ai.google.dev/gemini-api/docs/rate-limits"
                    ),
                )

            # Auth error
            if "401" in err_str or "403" in err_str or "api_key" in err_str or "permission" in err_str:
                raise HTTPException(
                    status_code=401,
                    detail="Invalid Gemini API key. Please check GEMINI_API_KEY in backend/.env.",
                )

            # Network error
            if any(w in err_str for w in ("connect", "timeout", "network", "unreachable")):
                raise HTTPException(
                    status_code=502,
                    detail="Could not reach the Gemini API. Please check your internet connection.",
                )

            # Safety block from finish_reason
            if "safety" in err_str or "blocked" in err_str or "recitation" in err_str:
                raise HTTPException(
                    status_code=422,
                    detail=(
                        "The AI image generation was blocked by safety filters for this prompt. "
                        "Try a different area type or fewer interventions."
                    ),
                )

            # Model not found / not supported — try next model
            if (
                "404" in err_str
                or "not found" in err_str
                or "not supported" in err_str
                or "enterprise" in err_str
                or "no image data" in err_str
                or "no candidates" in err_str
            ):
                continue

            # Unknown error — stop
            raise HTTPException(
                status_code=500,
                detail=f"Image generation error: {exc}",
            )

    # All models exhausted
    detail = (
        f"All image generation models failed. Last error: {last_error}"
        if last_error
        else "Image generation unavailable."
    )
    raise HTTPException(status_code=500, detail=detail)
