"""
test_shade_detection.py — Phase 4 backend tests

Covers:
  1. opencv_service.py  — unit tests for analyze_image() using synthetic images
  2. POST /api/shade/analyze — endpoint tests (real multipart uploads)

All tests use programmatically-generated images (no external files needed).
"""

import io
import pytest
import numpy as np
import cv2
from PIL import Image
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


# ── Image factory helpers ─────────────────────────────────────────────────────

def _make_jpeg_bytes(bgr_array: np.ndarray) -> bytes:
    """Encode a BGR numpy array to JPEG bytes."""
    ok, buf = cv2.imencode(".jpg", bgr_array)
    assert ok, "cv2.imencode failed in test helper"
    return buf.tobytes()


def _make_png_bytes(bgr_array: np.ndarray) -> bytes:
    """Encode a BGR numpy array to PNG bytes."""
    ok, buf = cv2.imencode(".png", bgr_array)
    assert ok, "cv2.imencode failed in test helper"
    return buf.tobytes()


def _solid_image(h: int, w: int, bgr: tuple) -> np.ndarray:
    """Create a solid-colour BGR image array."""
    return np.full((h, w, 3), bgr, dtype=np.uint8)


def _checkerboard(h: int, w: int, bgr_a: tuple, bgr_b: tuple) -> np.ndarray:
    """Create a half-and-half image: top half colour A, bottom half colour B."""
    arr = np.zeros((h, w, 3), dtype=np.uint8)
    arr[: h // 2, :] = bgr_a
    arr[h // 2 :, :] = bgr_b
    return arr


# Convenience colour constants (BGR)
BLACK  = (0,   0,   0)       # shade / shadow
WHITE  = (255, 255, 255)     # bright, not shaded
GREEN  = (0,   180,  60)     # vegetation
BLUE   = (200, 120,  30)     # sky-ish blue in BGR


# ── Unit tests: opencv_service ────────────────────────────────────────────────

from services.opencv_service import (
    analyze_image,
    _validate_image_bytes,
    _build_interpretation,
    _build_recommendations,
)
from fastapi import HTTPException


class TestValidateImageBytes:
    def test_rejects_oversized_file(self):
        big = b"x" * (11 * 1024 * 1024)   # 11 MB
        with pytest.raises(HTTPException) as exc:
            _validate_image_bytes(big, "photo.jpg")
        assert exc.value.status_code == 413

    def test_rejects_wrong_extension(self):
        with pytest.raises(HTTPException) as exc:
            _validate_image_bytes(b"data", "photo.gif")
        assert exc.value.status_code == 400
        assert "gif" in exc.value.detail.lower()

    def test_rejects_no_extension(self):
        with pytest.raises(HTTPException) as exc:
            _validate_image_bytes(b"data", "photonoext")
        assert exc.value.status_code == 400

    def test_rejects_corrupt_jpeg(self):
        with pytest.raises(HTTPException) as exc:
            _validate_image_bytes(b"not_an_image_at_all", "photo.jpg")
        assert exc.value.status_code == 400

    def test_accepts_valid_jpeg(self):
        img = _solid_image(10, 10, WHITE)
        data = _make_jpeg_bytes(img)
        # Should not raise
        _validate_image_bytes(data, "photo.jpg")

    def test_accepts_valid_png(self):
        img = _solid_image(10, 10, GREEN)
        data = _make_png_bytes(img)
        _validate_image_bytes(data, "photo.png")


class TestAnalyzeImageShadePct:
    """Verify shade detection on synthetic images."""

    def test_all_black_image_is_100pct_shade(self):
        img = _solid_image(100, 100, BLACK)
        result = analyze_image(_make_jpeg_bytes(img), "black.jpg")
        assert result["shade_percent"] == 100.0

    def test_all_white_image_has_low_shade(self):
        img = _solid_image(100, 100, WHITE)
        result = analyze_image(_make_jpeg_bytes(img), "white.jpg")
        # White = high Value, should give very low shade %
        assert result["shade_percent"] < 5.0

    def test_half_black_half_white_gives_approx_50pct_shade(self):
        img = _checkerboard(100, 100, BLACK, WHITE)
        result = analyze_image(_make_jpeg_bytes(img), "half.jpg")
        assert 45.0 <= result["shade_percent"] <= 55.0

    def test_shade_pct_in_range(self):
        img = _solid_image(50, 50, (50, 50, 50))   # dark grey
        result = analyze_image(_make_jpeg_bytes(img), "grey.jpg")
        assert 0.0 <= result["shade_percent"] <= 100.0


class TestAnalyzeImageGreenPct:
    """Verify green cover detection on synthetic images."""

    def test_solid_green_image_has_high_green_pct(self):
        img = _solid_image(100, 100, GREEN)
        result = analyze_image(_make_jpeg_bytes(img), "green.jpg")
        # Pure green should register as significant vegetation
        assert result["green_percent"] > 30.0

    def test_solid_white_has_zero_green(self):
        img = _solid_image(100, 100, WHITE)
        result = analyze_image(_make_jpeg_bytes(img), "white.jpg")
        assert result["green_percent"] < 5.0


class TestAnalyzeImageReturnShape:
    """Verify the returned dict has all required keys with correct types."""

    def test_all_keys_present(self):
        img = _solid_image(50, 50, WHITE)
        result = analyze_image(_make_jpeg_bytes(img), "test.jpg")
        required = {
            "shade_percent", "green_percent", "sky_percent",
            "sun_exposed_percent",
            "infrastructure_score", "shade_level",
            "width", "height", "total_pixels",
            "overlay_image",
            "interpretation", "recommendations",
        }
        assert required.issubset(result.keys())

    def test_shade_level_valid_value(self):
        img = _solid_image(50, 50, WHITE)
        result = analyze_image(_make_jpeg_bytes(img), "test.jpg")
        assert result["shade_level"] in ("Poor", "Moderate", "Good", "Excellent")

    def test_score_in_range(self):
        img = _solid_image(50, 50, GREEN)
        result = analyze_image(_make_jpeg_bytes(img), "test.jpg")
        assert 0.0 <= result["infrastructure_score"] <= 10.0

    def test_recommendations_non_empty(self):
        img = _solid_image(50, 50, BLACK)
        result = analyze_image(_make_jpeg_bytes(img), "test.jpg")
        assert isinstance(result["recommendations"], list)
        assert len(result["recommendations"]) > 0

    def test_recommendations_are_dicts_with_text_key(self):
        """Each recommendation is now a dict with at least a 'text' key."""
        img = _solid_image(50, 50, BLACK)
        result = analyze_image(_make_jpeg_bytes(img), "test.jpg")
        for rec in result["recommendations"]:
            assert isinstance(rec, dict), "recommendation should be a dict"
            assert "text" in rec, "recommendation dict must have 'text' key"
            assert "why" in rec, "recommendation dict must have 'why' key"
            assert "urgent" in rec, "recommendation dict must have 'urgent' key"
            assert isinstance(rec["text"], str) and len(rec["text"]) > 0

    def test_interpretation_is_string(self):
        img = _solid_image(50, 50, WHITE)
        result = analyze_image(_make_jpeg_bytes(img), "test.jpg")
        assert isinstance(result["interpretation"], str)
        assert len(result["interpretation"]) > 20

    def test_dimensions_match_image(self):
        img = _solid_image(64, 80, WHITE)
        result = analyze_image(_make_jpeg_bytes(img), "test.jpg")
        assert result["width"] == 80
        assert result["height"] == 64
        assert result["total_pixels"] == 64 * 80

    def test_percentages_sum_not_exceed_100(self):
        # shade + green + sky won't always sum to 100 (they can overlap in theory),
        # but each individually must be 0–100
        img = _solid_image(50, 50, GREEN)
        result = analyze_image(_make_jpeg_bytes(img), "test.jpg")
        for key in ("shade_percent", "green_percent", "sky_percent"):
            assert 0.0 <= result[key] <= 100.0, f"{key} out of range"

    def test_sun_exposed_percent_in_range(self):
        for bgr in (WHITE, BLACK, GREEN, BLUE):
            img = _solid_image(50, 50, bgr)
            result = analyze_image(_make_jpeg_bytes(img), "test.jpg")
            assert 0.0 <= result["sun_exposed_percent"] <= 100.0, (
                f"sun_exposed_percent out of range for {bgr}"
            )

    def test_overlay_image_is_nonempty_base64_string(self):
        img = _solid_image(50, 50, WHITE)
        result = analyze_image(_make_jpeg_bytes(img), "test.jpg")
        assert isinstance(result["overlay_image"], str)
        assert len(result["overlay_image"]) > 0

    def test_overlay_image_decodes_to_valid_png(self):
        """The overlay_image field must decode to a valid image via base64."""
        import base64
        img = _solid_image(80, 60, GREEN)
        result = analyze_image(_make_jpeg_bytes(img), "test.jpg")
        raw = base64.b64decode(result["overlay_image"])
        # PNG magic bytes: \x89PNG
        assert raw[:4] == b"\x89PNG", "overlay_image is not a valid PNG"

    def test_overlay_image_matches_analysis_dimensions(self):
        """Overlay image dimensions must match width/height returned in the result."""
        import base64
        from PIL import Image as PILImage
        img = _solid_image(64, 80, WHITE)
        result = analyze_image(_make_jpeg_bytes(img), "test.jpg")
        raw = base64.b64decode(result["overlay_image"])
        pil = PILImage.open(io.BytesIO(raw))
        assert pil.width  == result["width"]
        assert pil.height == result["height"]


class TestBuildInterpretation:
    """Unit tests for the interpretation text builder."""

    def test_high_shade_mentioned(self):
        text = _build_interpretation(shade=60, green=20, sky=10, sun=10, level="Good")
        assert "well-shaded" in text.lower() or "60%" in text

    def test_low_shade_mentioned(self):
        text = _build_interpretation(shade=5, green=5, sky=60, sun=30, level="Poor")
        assert "very little shade" in text.lower() or "5%" in text

    def test_level_appears_in_text(self):
        for level in ("Poor", "Moderate", "Good", "Excellent"):
            text = _build_interpretation(shade=10, green=10, sky=10, sun=70, level=level)
            assert level in text

    def test_high_sun_exposed_mentioned(self):
        text = _build_interpretation(shade=5, green=5, sky=5, sun=85, level="Poor")
        assert "85%" in text or "sun-exposed" in text.lower()

    def test_low_sun_exposed_not_mentioned(self):
        text = _build_interpretation(shade=50, green=20, sky=20, sun=10, level="Good")
        assert "sun-exposed" not in text.lower()


class TestBuildRecommendations:
    """Unit tests for the recommendations builder."""

    def test_all_levels_return_non_empty(self):
        for level in ("Poor", "Moderate", "Good", "Excellent"):
            recs = _build_recommendations(shade=20, green=20, sky=20, sun=40, level=level)
            assert len(recs) > 0

    def test_all_items_are_dicts(self):
        recs = _build_recommendations(shade=20, green=20, sky=20, sun=40, level="Poor")
        for r in recs:
            assert isinstance(r, dict)
            assert "text" in r and "why" in r and "urgent" in r

    def test_high_sky_adds_urgent_warning(self):
        recs = _build_recommendations(shade=5, green=5, sky=60, sun=30, level="Poor")
        # The first item should be the high-sky warning and marked urgent
        first = recs[0]
        assert "60%" in first["text"] or "sky" in first["text"].lower()
        assert first["urgent"] is True

    def test_normal_sky_no_urgent_warning(self):
        recs = _build_recommendations(shade=30, green=30, sky=20, sun=20, level="Good")
        assert not any(r["urgent"] for r in recs), "no recommendation should be urgent for normal sky"

    def test_high_sun_exposed_adds_tip(self):
        recs = _build_recommendations(shade=5, green=5, sky=5, sun=85, level="Poor")
        texts = " ".join(r["text"] for r in recs).lower()
        assert "reflective" in texts or "paving" in texts or "hard surface" in texts

    def test_low_vegetation_adds_tip(self):
        recs = _build_recommendations(shade=5, green=5, sky=5, sun=85, level="Poor")
        texts = " ".join(r["text"] for r in recs).lower()
        assert "vegetation" in texts or "planter" in texts or "tree" in texts


# ── Endpoint tests: POST /api/shade/analyze ───────────────────────────────────

class TestShadeEndpoint:

    def _post_image(self, img_array, filename="test.jpg", content_type="image/jpeg"):
        if filename.endswith(".png"):
            data = _make_png_bytes(img_array)
        else:
            data = _make_jpeg_bytes(img_array)
        return client.post(
            "/api/shade/analyze",
            files={"file": (filename, io.BytesIO(data), content_type)},
        )

    def test_jpeg_upload_returns_200(self):
        img = _solid_image(100, 100, GREEN)
        response = self._post_image(img)
        assert response.status_code == 200

    def test_png_upload_returns_200(self):
        img = _solid_image(100, 100, WHITE)
        response = self._post_image(img, "test.png", "image/png")
        assert response.status_code == 200

    def test_response_has_all_fields(self):
        img = _solid_image(80, 80, BLACK)
        response = self._post_image(img)
        data = response.json()
        for key in ("shade_percent", "green_percent", "sky_percent",
                    "sun_exposed_percent", "infrastructure_score", "shade_level",
                    "interpretation", "recommendations", "filename",
                    "overlay_image"):
            assert key in data, f"Missing key: {key}"

    def test_overlay_image_field_is_nonempty_string(self):
        img = _solid_image(60, 60, GREEN)
        response = self._post_image(img)
        data = response.json()
        assert isinstance(data["overlay_image"], str)
        assert len(data["overlay_image"]) > 0

    def test_recommendations_are_dicts(self):
        img = _solid_image(60, 60, WHITE)
        response = self._post_image(img)
        data = response.json()
        for rec in data["recommendations"]:
            assert isinstance(rec, dict)
            assert "text" in rec

    def test_filename_echoed_in_response(self):
        img = _solid_image(50, 50, WHITE)
        response = self._post_image(img, "mystreet.jpg")
        assert response.json()["filename"] == "mystreet.jpg"

    def test_no_file_returns_422(self):
        response = client.post("/api/shade/analyze")
        assert response.status_code == 422

    def test_wrong_extension_returns_400(self):
        gif_data = b"GIF89a\x01\x00\x01\x00\x00\xff\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x00;"
        response = client.post(
            "/api/shade/analyze",
            files={"file": ("photo.gif", io.BytesIO(gif_data), "image/gif")},
        )
        assert response.status_code == 400

    def test_corrupt_file_returns_400(self):
        response = client.post(
            "/api/shade/analyze",
            files={"file": ("broken.jpg", io.BytesIO(b"this is not an image"), "image/jpeg")},
        )
        assert response.status_code == 400

    def test_dark_image_has_high_shade_pct(self):
        img = _solid_image(100, 100, BLACK)
        response = self._post_image(img)
        assert response.json()["shade_percent"] > 90.0

    def test_green_image_has_high_green_pct(self):
        img = _solid_image(100, 100, GREEN)
        response = self._post_image(img)
        assert response.json()["green_percent"] > 30.0

    def test_score_range(self):
        img = _solid_image(100, 100, WHITE)
        response = self._post_image(img)
        score = response.json()["infrastructure_score"]
        assert 0.0 <= score <= 10.0
