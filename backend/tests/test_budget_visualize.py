"""
test_budget_visualize.py — Tests for POST /api/budget/visualize

The endpoint uses generate_content(response_modalities=['IMAGE', 'TEXT']),
NOT generate_images() which is Vertex AI / Enterprise-only and fails with
"This method is only supported in Gemini Enterprise Agent Platform mode."

Covers:
  • 503  — GEMINI_API_KEY missing / placeholder / blank
  • 200  — Happy path: image bytes in inline_data.data
  • 200  — Fallback: first model returns no image, second succeeds
  • 429  — Quota / rate-limit error (with and without retry hint)
  • 401  — Invalid API key
  • 502  — Network / connection error
  • 422  — Safety filter keyword in exception
  • 500  — Enterprise-mode error exhausts all models
  • 422  — Pydantic validation: empty IDs / invalid area_type / missing field
  • _extract_image_part unit-tests
  • _build_prompt unit-tests
"""

import base64
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from main import app

client = TestClient(app)

# ── Shared fixtures ───────────────────────────────────────────────────────────

_VALID_PAYLOAD = {
    "selected_intervention_ids": ["tree_planting", "cool_roof"],
    "area_type": "residential",
    "city": "Hyderabad",
    "expected_temp_reduction_c": 2.5,
}

_PNG_1x1 = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00"
    b"\x00\x11\x00\x01\x04\xd3l\xef\x00\x00\x00\x00IEND\xaeB`\x82"
)


def _make_generate_content_response(image_bytes=_PNG_1x1, mime_type="image/png"):
    """
    Mirror the generate_content response shape used by the endpoint:
        response.candidates[0].content.parts[i].inline_data.data  (bytes)
        response.candidates[0].content.parts[i].inline_data.mime_type  (str)
    """
    inline   = SimpleNamespace(data=image_bytes, mime_type=mime_type)
    part     = SimpleNamespace(inline_data=inline, text=None)
    content  = SimpleNamespace(parts=[part])
    candidate = SimpleNamespace(content=content)
    return SimpleNamespace(candidates=[candidate])


def _make_text_only_response():
    """A response with no image part — triggers fallback to next model."""
    part      = SimpleNamespace(inline_data=None, text="No image available.")
    content   = SimpleNamespace(parts=[part])
    candidate = SimpleNamespace(content=content)
    return SimpleNamespace(candidates=[candidate])


def _make_empty_candidates_response():
    """A response with no candidates at all."""
    return SimpleNamespace(candidates=[])


# ── No-key tests ──────────────────────────────────────────────────────────────

class TestVisualizeNoKey:
    """503 when GEMINI_API_KEY is absent, set to the placeholder, or blank."""

    def test_missing_key_returns_503(self, monkeypatch):
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        resp = client.post("/api/budget/visualize", json=_VALID_PAYLOAD)
        assert resp.status_code == 503
        assert "GEMINI_API_KEY" in resp.json()["detail"]

    def test_placeholder_key_returns_503(self, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEY", "your_gemini_api_key_here")
        resp = client.post("/api/budget/visualize", json=_VALID_PAYLOAD)
        assert resp.status_code == 503

    def test_empty_key_returns_503(self, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEY", "   ")
        resp = client.post("/api/budget/visualize", json=_VALID_PAYLOAD)
        assert resp.status_code == 503


# ── Happy-path tests ──────────────────────────────────────────────────────────

class TestVisualizeHappyPath:
    """200 with base64-encoded image when generate_content succeeds."""

    def test_returns_200_with_image(self, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEY", "fake_key_abc123")
        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = _make_generate_content_response()

        with patch("routers.budget_visualize.genai") as mock_genai:
            mock_genai.Client.return_value = mock_client
            resp = client.post("/api/budget/visualize", json=_VALID_PAYLOAD)

        assert resp.status_code == 200
        body = resp.json()
        assert "image_base64" in body
        assert "mime_type" in body
        assert "prompt_used" in body
        assert "model_used" in body

    def test_image_is_valid_base64(self, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEY", "fake_key_abc123")
        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = _make_generate_content_response()

        with patch("routers.budget_visualize.genai") as mock_genai:
            mock_genai.Client.return_value = mock_client
            resp = client.post("/api/budget/visualize", json=_VALID_PAYLOAD)

        assert base64.b64decode(resp.json()["image_base64"]) == _PNG_1x1

    def test_prompt_contains_intervention_phrases(self, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEY", "fake_key_abc123")
        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = _make_generate_content_response()

        with patch("routers.budget_visualize.genai") as mock_genai:
            mock_genai.Client.return_value = mock_client
            resp = client.post("/api/budget/visualize", json=_VALID_PAYLOAD)

        prompt = resp.json()["prompt_used"]
        assert "tree" in prompt or "shade trees" in prompt
        assert "reflective" in prompt or "roof" in prompt

    def test_city_appears_in_prompt(self, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEY", "fake_key_abc123")
        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = _make_generate_content_response()

        with patch("routers.budget_visualize.genai") as mock_genai:
            mock_genai.Client.return_value = mock_client
            resp = client.post("/api/budget/visualize", json=_VALID_PAYLOAD)

        assert "Hyderabad" in resp.json()["prompt_used"]

    def test_no_city_is_fine(self, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEY", "fake_key_abc123")
        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = _make_generate_content_response()

        with patch("routers.budget_visualize.genai") as mock_genai:
            mock_genai.Client.return_value = mock_client
            resp = client.post("/api/budget/visualize", json={**_VALID_PAYLOAD, "city": None})

        assert resp.status_code == 200

    def test_uses_generate_content_not_generate_images(self, monkeypatch):
        """Regression guard: generate_images must never be called."""
        monkeypatch.setenv("GEMINI_API_KEY", "fake_key_abc123")
        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = _make_generate_content_response()

        with patch("routers.budget_visualize.genai") as mock_genai:
            mock_genai.Client.return_value = mock_client
            client.post("/api/budget/visualize", json=_VALID_PAYLOAD)

        mock_client.models.generate_content.assert_called_once()
        mock_client.models.generate_images.assert_not_called()

    def test_model_fallback_on_no_image_in_first_model(self, monkeypatch):
        """First model returns text-only (no inline_data); second returns image."""
        monkeypatch.setenv("GEMINI_API_KEY", "fake_key_abc123")
        mock_client = MagicMock()
        mock_client.models.generate_content.side_effect = [
            _make_text_only_response(),          # → ValueError → try next
            _make_generate_content_response(),   # → success
        ]

        with patch("routers.budget_visualize.genai") as mock_genai:
            mock_genai.Client.return_value = mock_client
            resp = client.post("/api/budget/visualize", json=_VALID_PAYLOAD)

        assert resp.status_code == 200
        assert mock_client.models.generate_content.call_count == 2


# ── Quota tests ───────────────────────────────────────────────────────────────

class TestVisualizeQuota:
    """429 when Gemini returns a rate-limit / quota error."""

    def test_429_quota_error(self, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEY", "fake_key_abc123")
        mock_client = MagicMock()
        mock_client.models.generate_content.side_effect = Exception(
            "429 RESOURCE_EXHAUSTED: quota exceeded"
        )

        with patch("routers.budget_visualize.genai") as mock_genai:
            mock_genai.Client.return_value = mock_client
            resp = client.post("/api/budget/visualize", json=_VALID_PAYLOAD)

        assert resp.status_code == 429
        assert "quota" in resp.json()["detail"].lower()

    def test_429_includes_wait_hint_when_present(self, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEY", "fake_key_abc123")
        mock_client = MagicMock()
        mock_client.models.generate_content.side_effect = Exception(
            "429 RESOURCE_EXHAUSTED. Please retry in 1h35m12.3s. quota exceeded"
        )

        with patch("routers.budget_visualize.genai") as mock_genai:
            mock_genai.Client.return_value = mock_client
            resp = client.post("/api/budget/visualize", json=_VALID_PAYLOAD)

        assert resp.status_code == 429
        assert "1h35m" in resp.json()["detail"]


# ── Auth error tests ──────────────────────────────────────────────────────────

class TestVisualizeAuthError:
    def test_invalid_key_returns_401(self, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEY", "invalid_key")
        mock_client = MagicMock()
        mock_client.models.generate_content.side_effect = Exception(
            "401 UNAUTHENTICATED: API key not valid"
        )

        with patch("routers.budget_visualize.genai") as mock_genai:
            mock_genai.Client.return_value = mock_client
            resp = client.post("/api/budget/visualize", json=_VALID_PAYLOAD)

        assert resp.status_code == 401


# ── Network error tests ───────────────────────────────────────────────────────

class TestVisualizeNetworkError:
    def test_connection_error_returns_502(self, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEY", "fake_key_abc123")
        mock_client = MagicMock()
        mock_client.models.generate_content.side_effect = Exception(
            "Connection timeout: network unreachable"
        )

        with patch("routers.budget_visualize.genai") as mock_genai:
            mock_genai.Client.return_value = mock_client
            resp = client.post("/api/budget/visualize", json=_VALID_PAYLOAD)

        assert resp.status_code == 502


# ── Safety filter tests ───────────────────────────────────────────────────────

class TestVisualizeSafetyFilter:
    def test_safety_keyword_returns_422(self, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEY", "fake_key_abc123")
        mock_client = MagicMock()
        mock_client.models.generate_content.side_effect = Exception(
            "Response was blocked due to safety filters"
        )

        with patch("routers.budget_visualize.genai") as mock_genai:
            mock_genai.Client.return_value = mock_client
            resp = client.post("/api/budget/visualize", json=_VALID_PAYLOAD)

        assert resp.status_code == 422
        assert "safety" in resp.json()["detail"].lower()


# ── Enterprise-mode guard ─────────────────────────────────────────────────────

class TestEnterpriseError:
    """The old 'Enterprise mode' generate_images error must exhaust all models → 500."""

    def test_enterprise_error_exhausts_models_returns_500(self, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEY", "fake_key_abc123")
        mock_client = MagicMock()
        mock_client.models.generate_content.side_effect = Exception(
            "This method is only supported in Gemini Enterprise Agent Platform mode"
        )

        with patch("routers.budget_visualize.genai") as mock_genai:
            mock_genai.Client.return_value = mock_client
            resp = client.post("/api/budget/visualize", json=_VALID_PAYLOAD)

        assert resp.status_code == 500
        # All 4 models in _IMAGE_MODELS tried
        assert mock_client.models.generate_content.call_count == 4


# ── Pydantic validation tests ─────────────────────────────────────────────────

class TestVisualizeValidation:
    def test_empty_intervention_list_rejected(self, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEY", "fake_key_abc123")
        resp = client.post("/api/budget/visualize",
                           json={**_VALID_PAYLOAD, "selected_intervention_ids": []})
        assert resp.status_code == 422

    def test_invalid_area_type_rejected(self, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEY", "fake_key_abc123")
        resp = client.post("/api/budget/visualize",
                           json={**_VALID_PAYLOAD, "area_type": "jungle"})
        assert resp.status_code == 422

    def test_missing_intervention_ids_rejected(self, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEY", "fake_key_abc123")
        resp = client.post("/api/budget/visualize", json={"area_type": "mixed"})
        assert resp.status_code == 422


# ── _extract_image_part unit-tests ────────────────────────────────────────────

class TestExtractImagePart:
    def test_extracts_bytes_and_mime(self):
        from routers.budget_visualize import _extract_image_part
        data, mime = _extract_image_part(_make_generate_content_response())
        assert data == _PNG_1x1
        assert mime == "image/png"

    def test_text_only_response_raises_value_error(self):
        from routers.budget_visualize import _extract_image_part
        with pytest.raises(ValueError, match="No image data"):
            _extract_image_part(_make_text_only_response())

    def test_empty_candidates_raises_value_error(self):
        from routers.budget_visualize import _extract_image_part
        with pytest.raises(ValueError, match="No candidates"):
            _extract_image_part(_make_empty_candidates_response())

    def test_defaults_mime_to_png_when_none(self):
        from routers.budget_visualize import _extract_image_part
        inline    = SimpleNamespace(data=_PNG_1x1, mime_type=None)
        part      = SimpleNamespace(inline_data=inline, text=None)
        content   = SimpleNamespace(parts=[part])
        candidate = SimpleNamespace(content=content)
        _, mime   = _extract_image_part(SimpleNamespace(candidates=[candidate]))
        assert mime == "image/png"


# ── _build_prompt unit-tests ──────────────────────────────────────────────────

class TestBuildPrompt:
    def _req(self, **kwargs):
        from routers.budget_visualize import VisualizeRequest
        defaults = dict(
            selected_intervention_ids=["tree_planting", "cool_roof"],
            area_type="residential",
            city=None,
            expected_temp_reduction_c=None,
        )
        defaults.update(kwargs)
        return VisualizeRequest(**defaults)

    def test_prompt_contains_area_context(self):
        from routers.budget_visualize import _build_prompt
        assert "commercial district" in _build_prompt(self._req(area_type="commercial"))

    def test_prompt_skips_unknown_intervention_ids(self):
        from routers.budget_visualize import _build_prompt
        prompt = _build_prompt(self._req(selected_intervention_ids=["nonexistent_id"]))
        assert "urban cooling greening interventions" in prompt

    def test_temp_reduction_in_prompt(self):
        from routers.budget_visualize import _build_prompt
        assert "3.0" in _build_prompt(self._req(expected_temp_reduction_c=3.0))

    def test_city_in_prompt(self):
        from routers.budget_visualize import _build_prompt
        assert "Chennai" in _build_prompt(self._req(city="Chennai"))

    def test_no_city_no_crash(self):
        from routers.budget_visualize import _build_prompt
        assert "photorealistic" in _build_prompt(self._req(city=None))
