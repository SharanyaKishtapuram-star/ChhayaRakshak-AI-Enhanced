"""
shade_detection.py — Shade & Infrastructure Detection router (Phase 4)

Endpoint:
    POST /api/shade/analyze

Accepts a multipart image upload, runs OpenCV analysis, and returns:
    shade_percent, green_percent, sky_percent,
    infrastructure_score (0–10), shade_level, interpretation, recommendations.

Upload constraints:
    • Max size : 10 MB
    • Formats  : JPEG, PNG, WebP
    • Field name: "file"
"""

from fastapi import APIRouter, File, UploadFile, HTTPException
from services.opencv_service import analyze_image, ALLOWED_EXTENSIONS

router = APIRouter(prefix="/api/shade", tags=["Shade Detection"])

# The set of MIME types FastAPI will accept without rejecting at the framework level.
# Actual validation (including corrupt-file detection) is done inside analyze_image().
_ACCEPTED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp", "application/octet-stream"}


@router.post(
    "/analyze",
    summary="Analyse shade and green cover in an uploaded image",
    response_description=(
        "Shade %, green cover %, sky %, infrastructure score, "
        "quality level, interpretation, and recommendations"
    ),
)
async def analyze_shade(
    file: UploadFile = File(
        ...,
        description="Street or area photo (JPEG / PNG / WebP, max 10 MB)",
    )
):
    """
    Upload a street, park, or neighbourhood photo and receive:

    - **shade_percent**: % of the image covered by shadow/shade (dark pixels)
    - **green_percent**: % of the image showing vegetation (green hue pixels)
    - **sky_percent**: % of the image showing open sky (blue hue pixels)
    - **infrastructure_score**: 0–10 composite score (higher = better cooling)
    - **shade_level**: Poor / Moderate / Good / Excellent
    - **interpretation**: plain-English summary of what was found
    - **recommendations**: actionable urban-heat interventions for this area

    Analysis is performed entirely with OpenCV (offline, no external API).
    """
    # Quick MIME-type pre-check (some browsers send "application/octet-stream")
    ct = (file.content_type or "").lower()
    if ct and ct not in _ACCEPTED_CONTENT_TYPES:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Unexpected content type '{ct}'. "
                "Please upload a JPEG, PNG, or WebP image."
            ),
        )

    # Read file bytes (validation & analysis happen inside analyze_image)
    try:
        data = await file.read()
    except Exception:
        raise HTTPException(
            status_code=400,
            detail="Failed to read the uploaded file. Please try again.",
        )

    filename = file.filename or "upload.jpg"
    result = analyze_image(data, filename)

    return {
        "filename": filename,
        **result,
    }
