"""
opencv_service.py — Image analysis for shade and green cover detection (Phase 4)

All analysis is done with OpenCV (no external API, no internet needed).

─────────────────────────────────────────────────────────────────────────────
ANALYSIS METHODS
─────────────────────────────────────────────────────────────────────────────

Images are converted to HSV (Hue, Saturation, Value) colour space.
HSV is better than RGB for separating colours because it isolates brightness
(Value) from colour (Hue/Saturation).

1. Shade / Shadow detection
   Dark pixels (V < 80 out of 255) are counted as shaded.
   This captures building shadows, tree canopy shadows, and covered structures.
   Threshold is intentionally conservative: we do not flag night photos, only
   genuinely dark-value pixels present in a typically lit outdoor scene.
   LIMITATION: cannot distinguish tree-canopy shade from building shadow or
   dark-painted surfaces (black cars, dark walls also trigger this mask).

2. Green cover detection
   Pixels where Hue is in the "green" band (35–85°, scaled 0–179 in OpenCV)
   AND Saturation > 40 (to exclude grey/white haze) are counted as vegetation.
   LIMITATION: yellowed/dry vegetation may be missed; blue-green water or paint
   near the hue boundary can be mis-classified as vegetation.

3. Sky detection
   Pixels where Hue is in the blue band (90–130°, scaled 0–179) AND
   Saturation > 50 AND Value > 100 are counted as sky.
   High sky % + low shade % → very exposed, hot urban area.
   LIMITATION: overcast/grey sky is not detected.

4. Sun-exposed surface estimation
   Pixels not classified as shade, vegetation, or sky are treated as
   potentially sun-exposed hard surfaces (concrete, asphalt, rooftops).
   sun_exposed_percent = max(0, 100 − shade − green − sky).
   LIMITATION: this is a residual estimate, not a direct measurement. It
   includes any pixels that fall outside the three colour/brightness masks.

5. Colour overlay generation
   A semi-transparent overlay is painted on a copy of the original image:
     • Blue   tint  → sky pixels
     • Green  tint  → vegetation pixels
     • Grey   tint  → shade/shadow pixels
     • Orange tint  → estimated sun-exposed surface pixels
   The overlay is returned as a base64-encoded PNG string.

6. Infrastructure assessment (0–10 score)
   Combines shade %, green %, and sky % into a "coolness" score.
   Higher = more natural cooling infrastructure present.

7. Shade quality level  (derived from infrastructure score)
   Poor (0–2.5), Moderate (2.6–5.0), Good (5.1–7.5), Excellent (7.6–10)
─────────────────────────────────────────────────────────────────────────────
"""

import base64
import io
from PIL import Image
import numpy as np
import cv2
from fastapi import HTTPException

# ── Constants ────────────────────────────────────────────────────────────────

MAX_FILE_BYTES = 10 * 1024 * 1024          # 10 MB
ALLOWED_MIME_TYPES = {"image/jpeg", "image/png", "image/webp"}
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}

# HSV thresholds (OpenCV uses H: 0–179, S: 0–255, V: 0–255)
SHADE_V_MAX    = 80     # Value below this = shadow/shade
GREEN_H_MIN    = 35     # Hue lower bound for green (scaled: 35/360*179 ≈ 17)
GREEN_H_MAX    = 85     # Hue upper bound for green (scaled: 85/360*179 ≈ 42)
GREEN_S_MIN    = 40     # Minimum saturation to distinguish from grey
SKY_H_MIN      = 90     # Hue lower bound for sky blue (scaled 0–179)
SKY_H_MAX      = 130    # Hue upper bound for sky blue
SKY_S_MIN      = 50     # Minimum saturation for sky

# Resize large images before analysis to cap processing time
ANALYSIS_MAX_DIM = 1024   # pixels on longest side


def _validate_image_bytes(data: bytes, filename: str) -> None:
    """
    Validate that the uploaded bytes are within size limit and that the file
    can be decoded as a real image by PIL.

    Raises HTTP 400 for invalid/corrupt files.
    Raises HTTP 413 for files exceeding the size limit.
    """
    if len(data) > MAX_FILE_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"File too large ({len(data) // 1024} KB). Maximum allowed is 10 MB.",
        )

    ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Unsupported file type '{ext}'. "
                "Please upload a JPEG, PNG, or WebP image."
            ),
        )

    try:
        img = Image.open(io.BytesIO(data))
        img.verify()   # detect truncated / corrupt files
    except Exception:
        raise HTTPException(
            status_code=400,
            detail="The uploaded file could not be read as an image. "
                   "Please check that it is a valid JPEG, PNG, or WebP file.",
        )


def _load_bgr_and_hsv(data: bytes) -> tuple[np.ndarray, np.ndarray, tuple[int, int]]:
    """
    Decode image bytes to BGR and HSV arrays.
    Resizes if the image is larger than ANALYSIS_MAX_DIM on either dimension.

    Returns (bgr_array, hsv_array, (height, width)).
    """
    arr = np.frombuffer(data, dtype=np.uint8)
    bgr = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if bgr is None:
        raise HTTPException(
            status_code=400,
            detail="OpenCV could not decode the image. "
                   "Please ensure it is a valid, non-corrupt image file.",
        )

    h, w = bgr.shape[:2]
    if max(h, w) > ANALYSIS_MAX_DIM:
        scale = ANALYSIS_MAX_DIM / max(h, w)
        new_w, new_h = int(w * scale), int(h * scale)
        bgr = cv2.resize(bgr, (new_w, new_h), interpolation=cv2.INTER_AREA)
        h, w = new_h, new_w

    return bgr, cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV), (h, w)


def _build_overlay(
    bgr: np.ndarray,
    shade_mask: np.ndarray,
    green_mask: np.ndarray,
    sky_mask: np.ndarray,
    sun_mask: np.ndarray,
) -> str:
    """
    Paint a semi-transparent colour overlay on the original image to indicate
    which pixels belong to each detected category.

    Colour legend (BGR):
        Grey   (120,120,120) → shade/shadow
        Green  ( 40,180, 40) → vegetation
        Blue   (200,100, 30) → sky
        Orange ( 30,120,220) → estimated sun-exposed surface

    The overlay is alpha-blended at 50% opacity over a slightly darkened
    version of the original image so the scene context is still visible.

    Returns a base64-encoded PNG string suitable for an <img src="data:..."> tag.
    """
    # Darken the original slightly so coloured regions pop
    base = (bgr * 0.65).astype(np.uint8)
    overlay = base.copy()

    alpha = 0.55   # tint opacity

    # BGR colour values for each category
    SHADE_COLOUR = np.array([120, 120, 120], dtype=np.uint8)   # grey
    GREEN_COLOUR = np.array([ 30, 160,  30], dtype=np.uint8)   # green
    SKY_COLOUR   = np.array([200,  80,  20], dtype=np.uint8)   # blue (BGR)
    SUN_COLOUR   = np.array([ 20, 110, 220], dtype=np.uint8)   # orange (BGR)

    for mask, colour in (
        (shade_mask, SHADE_COLOUR),
        (green_mask, GREEN_COLOUR),
        (sky_mask,   SKY_COLOUR),
        (sun_mask,   SUN_COLOUR),
    ):
        region = mask.astype(bool)
        overlay[region] = (
            base[region] * (1 - alpha) + colour * alpha
        ).astype(np.uint8)

    ok, buf = cv2.imencode(".png", overlay)
    if not ok:
        return ""
    return base64.b64encode(buf.tobytes()).decode("ascii")


def analyze_image(data: bytes, filename: str) -> dict:
    """
    Run shade, green cover, sky, and sun-exposed surface analysis on the
    uploaded image bytes.

    Returns a dict with:
        shade_percent         float  0–100
        green_percent         float  0–100
        sky_percent           float  0–100
        sun_exposed_percent   float  0–100  (residual estimate)
        infrastructure_score  float  0–10
        shade_level           str    Poor / Moderate / Good / Excellent
        width                 int    pixels (after resize if applied)
        height                int    pixels (after resize if applied)
        total_pixels          int
        overlay_image         str    base64-encoded PNG with colour overlay
        recommendations       list[str]
        interpretation        str    one-paragraph plain-English summary
    """
    _validate_image_bytes(data, filename)
    bgr, hsv, (h, w) = _load_bgr_and_hsv(data)

    total = h * w

    # ── 1. Shade detection ────────────────────────────────────────────────────
    # Dark pixels: low Value channel regardless of hue
    shade_mask = cv2.inRange(hsv, (0, 0, 0), (179, 255, SHADE_V_MAX))
    shade_pixels = int(cv2.countNonZero(shade_mask))
    shade_pct = round(shade_pixels / total * 100, 1)

    # ── 2. Green cover detection ──────────────────────────────────────────────
    green_mask = cv2.inRange(
        hsv,
        (GREEN_H_MIN, GREEN_S_MIN, 40),
        (GREEN_H_MAX, 255, 255),
    )
    green_pixels = int(cv2.countNonZero(green_mask))
    green_pct = round(green_pixels / total * 100, 1)

    # ── 3. Sky detection ──────────────────────────────────────────────────────
    sky_mask = cv2.inRange(
        hsv,
        (SKY_H_MIN, SKY_S_MIN, 100),
        (SKY_H_MAX, 255, 255),
    )
    sky_pixels = int(cv2.countNonZero(sky_mask))
    sky_pct = round(sky_pixels / total * 100, 1)

    # ── 4. Sun-exposed surface estimation ────────────────────────────────────
    # Residual: pixels not captured by shade, green, or sky masks are treated
    # as unclassified / potentially sun-exposed surfaces (may be paved ground,
    # soil, mulch, stone, building walls, vehicles, or anything else that does
    # not match the three colour/brightness masks above).
    # NOTE: shade and green masks can overlap — dark green foliage satisfies
    # both V<80 (shade) and the green hue/saturation criteria simultaneously,
    # so those pixels are counted in both shade_pct and green_pct.  As a result
    # this formula can double-subtract overlapping pixels, making sun_pct a
    # slight underestimate of the true residual pixel count.
    sun_pct = round(max(0.0, 100.0 - shade_pct - green_pct - sky_pct), 1)

    # Build a boolean sun-exposed mask for the overlay: pixels that are
    # not shade AND not green AND not sky.
    not_shade = cv2.bitwise_not(shade_mask)
    not_green = cv2.bitwise_not(green_mask)
    not_sky   = cv2.bitwise_not(sky_mask)
    sun_mask  = cv2.bitwise_and(cv2.bitwise_and(not_shade, not_green), not_sky)

    # ── 5. Infrastructure score ───────────────────────────────────────────────
    # Shade (max 5 pts): more shade = cooler
    shade_score = min(5.0, shade_pct / 10.0)

    # Green (max 3 pts): more vegetation = better
    green_score = min(3.0, green_pct / 10.0)

    # Sky penalty (max −1 pt): very open sky = hot and exposed
    sky_penalty = min(1.0, sky_pct / 40.0)

    infra_score = round(max(0.0, min(10.0, shade_score + green_score - sky_penalty + 1.0)), 1)
    # +1 baseline so even minimal shade/green areas don't score 0

    # ── 6. Shade quality level ────────────────────────────────────────────────
    if infra_score <= 2.5:
        level = "Poor"
    elif infra_score <= 5.0:
        level = "Moderate"
    elif infra_score <= 7.5:
        level = "Good"
    else:
        level = "Excellent"

    # ── 7. Colour overlay ─────────────────────────────────────────────────────
    overlay_b64 = _build_overlay(bgr, shade_mask, green_mask, sky_mask, sun_mask)

    # ── 8. Interpretation ─────────────────────────────────────────────────────
    interpretation = _build_interpretation(shade_pct, green_pct, sky_pct, sun_pct, level)

    # ── 9. Recommendations ────────────────────────────────────────────────────
    recommendations = _build_recommendations(shade_pct, green_pct, sky_pct, sun_pct, level)

    return {
        "shade_percent":        shade_pct,
        "green_percent":        green_pct,
        "sky_percent":          sky_pct,
        "sun_exposed_percent":  sun_pct,
        "infrastructure_score": infra_score,
        "shade_level":          level,
        "width":                w,
        "height":               h,
        "total_pixels":         total,
        "overlay_image":        overlay_b64,
        "interpretation":       interpretation,
        "recommendations":      recommendations,
    }


# ── Interpretation text ───────────────────────────────────────────────────────

def _build_interpretation(
    shade: float, green: float, sky: float, sun: float, level: str
) -> str:
    parts = []

    if shade >= 50:
        parts.append(f"The area is well-shaded ({shade}% of the image is in shadow or shade)")
    elif shade >= 25:
        parts.append(f"Partial shade is present ({shade}% shaded)")
    else:
        parts.append(f"Very little shade is visible ({shade}% shaded)")

    if green >= 30:
        parts.append(f"strong green cover ({green}% vegetation)")
    elif green >= 10:
        parts.append(f"moderate vegetation ({green}%)")
    else:
        parts.append(f"minimal vegetation ({green}%)")

    if sky >= 40:
        parts.append(f"a large open sky ({sky}%), indicating high sun exposure")
    elif sky >= 20:
        parts.append(f"some open sky ({sky}%)")
    else:
        parts.append(f"limited direct sky view ({sky}%)")

    summary = f"{parts[0]}, with {parts[1]} and {parts[2]}. "

    if sun >= 40:
        summary += (
            f"Approximately {sun}% of the image consists of unclassified pixels "
            f"(not detected as shade, vegetation, or sky) — these may include paved "
            f"surfaces, soil, mulch, stone, building materials, or other areas that do "
            f"not match the colour or brightness thresholds of the other categories. "
        )
    elif sun >= 15:
        summary += (
            f"Around {sun}% of pixels are estimated as sun-exposed surface. "
        )

    summary += f"Overall shade infrastructure quality: {level}."
    return summary


# ── Recommendations ───────────────────────────────────────────────────────────

_RECOMMENDATIONS: dict[str, list[str]] = {
    "Poor": [
        "Plant trees along roadsides and footpaths to create natural canopy cover.",
        "Install shade sails or pergolas over pedestrian areas and bus stops.",
        "Use reflective or cool-roof coatings on building surfaces to reduce heat absorption.",
        "Create green corridors by planting climbing plants on building walls.",
        "Establish misting stations or cool water points for pedestrians.",
        "Prioritise tree-planting in this area under urban heat-island mitigation schemes.",
    ],
    "Moderate": [
        "Increase tree canopy density to improve shade continuity.",
        "Add shade structures at pedestrian waiting areas (bus stops, markets).",
        "Encourage rooftop gardens and vertical green walls on nearby buildings.",
        "Maintain and water existing vegetation — dry trees lose 30–40% of their cooling effect.",
        "Consider permeable paving to reduce surface heat retention.",
    ],
    "Good": [
        "Maintain existing trees and shade structures — regular pruning keeps canopy healthy.",
        "Fill shade gaps by planting fast-growing native species in exposed patches.",
        "Ensure shade coverage extends to frequently used paths and resting areas during peak sun hours (10 AM–4 PM).",
        "Compost fallen leaves on-site to enrich soil and reduce watering needs.",
    ],
    "Excellent": [
        "This area has good natural cooling infrastructure — prioritise its maintenance.",
        "Document and share this green design as a model for other urban areas.",
        "Ensure irrigation systems are in place to sustain vegetation during summer droughts.",
        "Regular canopy surveys will catch disease or storm damage early.",
    ],
}


def _build_recommendations(
    shade: float, green: float, sky: float, sun: float, level: str
) -> list[str]:
    """
    Each recommendation is paired with a brief rationale so users understand
    why it is being suggested for this specific image's conditions.
    """
    # Base recommendations are level-specific
    base = list(_RECOMMENDATIONS[level])
    recs = []

    # ── Condition-driven contextual tips (inserted first) ─────────────────────

    if sky > 50:
        recs.append({
            "text": (
                f"{sky}% of the image is open sky — this area is highly exposed to "
                "direct sunlight. Immediate shade interventions are recommended."
            ),
            "why": "High open-sky percentage means minimal overhead obstruction, "
                   "resulting in full solar radiation reaching ground level.",
            "urgent": True,
        })

    if sun >= 40:
        recs.append({
            "text": (
                f"Approx. {sun}% of the image is unclassified surface (not shade, vegetation, "
                "or sky). If this area contains hard paving or concrete, light-coloured or "
                "reflective materials can significantly reduce surface temperatures."
            ),
            "why": "Hard paved surfaces absorb solar energy and re-radiate it as heat "
                   "throughout the day, intensifying the urban heat island effect. "
                   "This recommendation applies where paved surfaces are present; "
                   "soil, mulch, or organic cover already have lower heat retention.",
            "urgent": False,
        })

    if green < 10 and level in ("Poor", "Moderate"):
        recs.append({
            "text": (
                "Vegetation cover is very low. Even small planters, street trees, or "
                "green walls can meaningfully lower local air temperature."
            ),
            "why": f"Only {green}% of the image shows green pixels. Vegetation cools "
                   "through evapotranspiration and by blocking direct solar radiation.",
            "urgent": False,
        })

    if shade < 15 and green < 15:
        recs.append({
            "text": (
                "Both shade and vegetation are minimal. Consider adding shade sails, "
                "pergolas, or canopy structures as a faster alternative to tree-planting."
            ),
            "why": "Structural shade works immediately while trees take years to mature.",
            "urgent": False,
        })

    # ── Base level recommendations ────────────────────────────────────────────
    for text in base:
        recs.append({"text": text, "why": None, "urgent": False})

    return recs
