"""
test_assistant.py — AI Assistant backend tests

All Gemini calls are mocked — no real API calls, no key required.

Covers original tests plus:
  • Health-profile integration: personalised context is passed to ask_gemini
  • Missing / deleted profile falls back to generic response (no error)
  • Blank / whitespace session_id treated as no session
  • Profile with only 'none' condition produces no actionable context
  • profile_active flag is True only when a real profile was resolved
  • Context builder unit-tests (_build_health_context, _get_health_context)

Limitation fixes (added):
  • Limitation 1 – on-mount validation: profile lookup works at any point, not
    just after a question (verified via direct _get_health_context calls)
  • Limitation 2 – profile deleted between questions returns profile_active=False
    on the next ask without breaking the current question
  • Limitation 2 – profile updated between questions uses the NEW profile data
  • Limitation 3 – localisation is purely frontend; no backend changes needed
    (verified: backend returns profile_active regardless of language)
"""
import pytest
from unittest.mock import patch, MagicMock, call
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from main import app
from services.gemini_service import GeminiServiceError
from database.db import Base, get_db
from database.models import HealthProfile
from routers.assistant import _build_health_context, _get_health_context

# ── In-memory SQLite override (isolated per-test via function-scoped fixture) ─

_TEST_DB_URL = "sqlite://"   # pure in-memory, vanishes after each test

@pytest.fixture()
def db_session():
    """Provide a fresh in-memory SQLite session and override the app dependency."""
    engine = create_engine(
        _TEST_DB_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,   # ensures all sessions share the same connection
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    session = TestingSessionLocal()
    try:
        # Override the FastAPI dependency so the endpoint uses our test DB
        app.dependency_overrides[get_db] = lambda: session
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)
        app.dependency_overrides.pop(get_db, None)


@pytest.fixture()
def api_client(db_session):
    """TestClient that uses the in-memory DB session."""
    return TestClient(app)


def _make_profile(
    db,
    session_id: str = "test-session-abc",
    age_group: str = "60+",
    conditions: str = "cardiovascular,diabetes",
    outdoor_worker: bool = True,
) -> HealthProfile:
    """Insert a minimal health profile row and return it."""
    p = HealthProfile(
        session_id=session_id,
        consent_given=True,
        age_group=age_group,
        conditions=conditions,
        outdoor_worker=outdoor_worker,
    )
    db.add(p)
    db.commit()
    db.refresh(p)
    return p


_MOCK_ANSWER = "Stay hydrated and avoid direct sunlight between 11 AM and 4 PM."

# ── Status endpoint (no DB changes needed) ────────────────────────────────────

class TestAssistantStatus:

    def test_status_endpoint_returns_200(self):
        response = TestClient(app).get("/api/assistant/status")
        assert response.status_code == 200

    def test_status_has_configured_field(self):
        response = TestClient(app).get("/api/assistant/status")
        data = response.json()
        assert "configured" in data
        assert isinstance(data["configured"], bool)

    def test_status_has_supported_languages(self):
        response = TestClient(app).get("/api/assistant/status")
        langs = response.json()["supported_languages"]
        assert "en" in langs
        assert "hi" in langs
        assert "te" in langs

    def test_status_unconfigured_when_no_key(self):
        with patch.dict("os.environ", {"GEMINI_API_KEY": ""}, clear=False):
            response = TestClient(app).get("/api/assistant/status")
        assert response.json()["configured"] is False

    def test_status_configured_when_key_present(self):
        with patch.dict("os.environ", {"GEMINI_API_KEY": "real-looking-key-abc123"}, clear=False):
            response = TestClient(app).get("/api/assistant/status")
        assert response.json()["configured"] is True


# ── Ask endpoint — existing tests (preserved exactly) ────────────────────────

class TestAssistantAsk:
    """Original tests: no session_id supplied — generic path unchanged."""

    def _ask(self, question="What to do in heat?", language="en"):
        return TestClient(app).post("/api/assistant/ask", json={
            "question": question,
            "language": language,
        })

    def test_successful_english_response(self):
        with patch("routers.assistant.ask_gemini", return_value=_MOCK_ANSWER):
            response = self._ask("What to do in heat?", "en")
        assert response.status_code == 200
        data = response.json()
        assert data["answer"] == _MOCK_ANSWER
        assert data["language"] == "en"
        assert data["language_name"] == "English"

    def test_successful_hindi_response(self):
        with patch("routers.assistant.ask_gemini", return_value="हाइड्रेटेड रहें"):
            response = self._ask("गर्मी में क्या करें?", "hi")
        assert response.status_code == 200
        assert response.json()["language"] == "hi"

    def test_successful_telugu_response(self):
        with patch("routers.assistant.ask_gemini", return_value="నీరు తాగండి"):
            response = self._ask("వేడిలో ఏమి చేయాలి?", "te")
        assert response.status_code == 200
        assert response.json()["language"] == "te"

    def test_question_echoed_in_response(self):
        q = "How do I protect elderly people from heat?"
        with patch("routers.assistant.ask_gemini", return_value=_MOCK_ANSWER):
            response = self._ask(q)
        assert response.json()["question"] == q

    def test_missing_key_returns_503(self):
        with patch("routers.assistant.ask_gemini",
                   side_effect=GeminiServiceError("key missing", status_code=503)):
            response = self._ask()
        assert response.status_code == 503

    def test_rate_limit_returns_429(self):
        with patch("routers.assistant.ask_gemini",
                   side_effect=GeminiServiceError("rate limit", status_code=429)):
            response = self._ask()
        assert response.status_code == 429

    def test_network_error_returns_502(self):
        with patch("routers.assistant.ask_gemini",
                   side_effect=GeminiServiceError("network error", status_code=502)):
            response = self._ask()
        assert response.status_code == 502

    def test_question_too_short_returns_422(self):
        response = TestClient(app).post("/api/assistant/ask", json={"question": "Hi", "language": "en"})
        assert response.status_code == 422

    def test_invalid_language_returns_422(self):
        response = TestClient(app).post("/api/assistant/ask", json={
            "question": "What to do in heat?",
            "language": "fr",
        })
        assert response.status_code == 422

    def test_missing_question_returns_422(self):
        response = TestClient(app).post("/api/assistant/ask", json={"language": "en"})
        assert response.status_code == 422

    def test_no_session_id_gives_profile_active_false(self):
        """When no session_id is provided, profile_active must be False."""
        with patch("routers.assistant.ask_gemini", return_value=_MOCK_ANSWER):
            response = TestClient(app).post("/api/assistant/ask", json={
                "question": "What to do in heat?",
                "language": "en",
            })
        assert response.status_code == 200
        assert response.json()["profile_active"] is False


# ── Health profile integration tests ─────────────────────────────────────────

class TestAssistantHealthIntegration:
    """Tests that require a real DB session (in-memory SQLite)."""

    def test_valid_profile_gives_profile_active_true(self, api_client, db_session):
        _make_profile(db_session, session_id="sid-001")
        with patch("routers.assistant.ask_gemini", return_value=_MOCK_ANSWER) as mock_ask:
            resp = api_client.post("/api/assistant/ask", json={
                "question": "What should I do in extreme heat?",
                "language": "en",
                "session_id": "sid-001",
            })
        assert resp.status_code == 200
        assert resp.json()["profile_active"] is True

    def test_valid_profile_passes_context_to_gemini(self, api_client, db_session):
        """The health context string must be forwarded to ask_gemini."""
        _make_profile(
            db_session,
            session_id="sid-002",
            age_group="60+",
            conditions="cardiovascular,diabetes",
            outdoor_worker=True,
        )
        with patch("routers.assistant.ask_gemini", return_value=_MOCK_ANSWER) as mock_ask:
            api_client.post("/api/assistant/ask", json={
                "question": "How do I stay safe?",
                "language": "en",
                "session_id": "sid-002",
            })
        # Ensure ask_gemini was called with a non-None, non-empty health_context
        args, kwargs = mock_ask.call_args
        context = kwargs.get("health_context") or (args[2] if len(args) > 2 else None)
        assert context is not None
        assert len(context) > 0
        # The context should contain recognisable human-readable labels
        assert "60" in context           # age label
        assert "cardiovascular" in context
        assert "diabetes" in context
        assert "outdoor worker" in context

    def test_missing_profile_falls_back_gracefully(self, api_client, db_session):
        """Non-existent session_id must return 200 with profile_active=False."""
        with patch("routers.assistant.ask_gemini", return_value=_MOCK_ANSWER):
            resp = api_client.post("/api/assistant/ask", json={
                "question": "What to do in heat?",
                "language": "en",
                "session_id": "does-not-exist",
            })
        assert resp.status_code == 200
        assert resp.json()["profile_active"] is False
        assert resp.json()["answer"] == _MOCK_ANSWER

    def test_deleted_profile_falls_back_gracefully(self, api_client, db_session):
        """Deleting a profile and then asking must fall back to generic guidance."""
        _make_profile(db_session, session_id="sid-del")
        # Delete it
        profile = db_session.query(HealthProfile).filter_by(session_id="sid-del").first()
        db_session.delete(profile)
        db_session.commit()

        with patch("routers.assistant.ask_gemini", return_value=_MOCK_ANSWER):
            resp = api_client.post("/api/assistant/ask", json={
                "question": "What to do in heat?",
                "language": "en",
                "session_id": "sid-del",
            })
        assert resp.status_code == 200
        assert resp.json()["profile_active"] is False

    def test_blank_session_id_falls_back(self, api_client, db_session):
        """Whitespace-only session_id must be treated as no session."""
        with patch("routers.assistant.ask_gemini", return_value=_MOCK_ANSWER):
            resp = api_client.post("/api/assistant/ask", json={
                "question": "What to do in heat?",
                "language": "en",
                "session_id": "   ",
            })
        assert resp.status_code == 200
        assert resp.json()["profile_active"] is False

    def test_profile_with_none_condition_has_no_actionable_context(self, api_client, db_session):
        """Profile where conditions='none' and no age / not outdoor worker → generic."""
        _make_profile(
            db_session,
            session_id="sid-none",
            age_group=None,
            conditions="none",
            outdoor_worker=False,
        )
        with patch("routers.assistant.ask_gemini", return_value=_MOCK_ANSWER) as mock_ask:
            resp = api_client.post("/api/assistant/ask", json={
                "question": "What to do in heat?",
                "language": "en",
                "session_id": "sid-none",
            })
        assert resp.status_code == 200
        assert resp.json()["profile_active"] is False
        args, kwargs = mock_ask.call_args
        context = kwargs.get("health_context") or (args[2] if len(args) > 2 else None)
        assert context is None

    def test_gemini_error_still_propagates_correctly_with_profile(self, api_client, db_session):
        """A Gemini error with a valid profile must still return the correct HTTP status."""
        _make_profile(db_session, session_id="sid-err")
        with patch("routers.assistant.ask_gemini",
                   side_effect=GeminiServiceError("quota", status_code=429)):
            resp = api_client.post("/api/assistant/ask", json={
                "question": "What to do in heat?",
                "language": "en",
                "session_id": "sid-err",
            })
        assert resp.status_code == 429

    def test_context_not_passed_without_session_id(self, api_client, db_session):
        """Without session_id, ask_gemini must receive health_context=None."""
        with patch("routers.assistant.ask_gemini", return_value=_MOCK_ANSWER) as mock_ask:
            api_client.post("/api/assistant/ask", json={
                "question": "What to do in heat?",
                "language": "en",
            })
        args, kwargs = mock_ask.call_args
        context = kwargs.get("health_context") or (args[2] if len(args) > 2 else None)
        assert context is None


# ── Limitation-fix tests ──────────────────────────────────────────────────────

class TestAssistantLimitationFixes:
    """
    Tests that verify the three limitation fixes.

    Limitation 1: Profile status verified on each request (not only on first
                  question).  The backend DB lookup happens inside ask_assistant
                  on every call, so even a cold call immediately reflects the
                  current DB state.

    Limitation 2: Profile deleted or updated between consecutive questions is
                  reflected correctly on the very next ask — no stale data used.

    Limitation 3: Localisation is frontend-only; the backend returns
                  profile_active correctly for all three supported languages.
    """

    # ── Limitation 1: profile status always reflects current DB state ─────────

    def test_profile_active_true_on_first_ask_without_prior_interaction(self, api_client, db_session):
        """
        profile_active=True on the very first question (no prior 'warm-up'
        question required).  Simulates a page refresh followed immediately by
        asking a question.
        """
        _make_profile(db_session, session_id="lim1-sid")
        with patch("routers.assistant.ask_gemini", return_value=_MOCK_ANSWER):
            resp = api_client.post("/api/assistant/ask", json={
                "question": "What precautions for hot weather?",
                "language": "en",
                "session_id": "lim1-sid",
            })
        assert resp.status_code == 200
        assert resp.json()["profile_active"] is True

    def test_profile_active_false_immediately_after_deletion_no_prior_ask(self, api_client, db_session):
        """
        Even the very first question after a profile is deleted returns
        profile_active=False — no prior 'warm-up' call needed.
        """
        _make_profile(db_session, session_id="lim1-del")
        # Delete immediately
        p = db_session.query(HealthProfile).filter_by(session_id="lim1-del").first()
        db_session.delete(p)
        db_session.commit()

        with patch("routers.assistant.ask_gemini", return_value=_MOCK_ANSWER):
            resp = api_client.post("/api/assistant/ask", json={
                "question": "What precautions for hot weather?",
                "language": "en",
                "session_id": "lim1-del",
            })
        assert resp.status_code == 200
        assert resp.json()["profile_active"] is False

    # ── Limitation 2: profile deleted between questions ───────────────────────

    def test_profile_deleted_between_questions_uses_generic_on_next_ask(self, api_client, db_session):
        """
        Ask question 1 with a valid profile → profile_active=True.
        Delete the profile.
        Ask question 2 with the same session_id → profile_active=False (graceful
        fallback), question still answered normally.
        """
        _make_profile(db_session, session_id="lim2-del")

        # Question 1 — profile valid
        with patch("routers.assistant.ask_gemini", return_value=_MOCK_ANSWER):
            r1 = api_client.post("/api/assistant/ask", json={
                "question": "Stay safe in heat?",
                "language": "en",
                "session_id": "lim2-del",
            })
        assert r1.json()["profile_active"] is True

        # Delete the profile between questions
        p = db_session.query(HealthProfile).filter_by(session_id="lim2-del").first()
        db_session.delete(p)
        db_session.commit()

        # Question 2 — same session_id, but profile is gone
        with patch("routers.assistant.ask_gemini", return_value=_MOCK_ANSWER):
            r2 = api_client.post("/api/assistant/ask", json={
                "question": "Stay safe in heat?",
                "language": "en",
                "session_id": "lim2-del",
            })
        assert r2.status_code == 200
        assert r2.json()["profile_active"] is False
        assert r2.json()["answer"] == _MOCK_ANSWER

    # ── Limitation 2: profile updated between questions ───────────────────────

    def test_profile_updated_between_questions_uses_new_context(self, api_client, db_session):
        """
        Ask question 1 with outdoor_worker=False.
        Update the profile to outdoor_worker=True.
        Ask question 2 — the context forwarded to ask_gemini must reflect
        the update (outdoor worker present in context).
        """
        _make_profile(
            db_session,
            session_id="lim2-upd",
            age_group="41-60",
            conditions="respiratory",
            outdoor_worker=False,
        )

        # Question 1 — no outdoor_worker in context
        with patch("routers.assistant.ask_gemini", return_value=_MOCK_ANSWER) as mock1:
            api_client.post("/api/assistant/ask", json={
                "question": "Heat safety tips?",
                "language": "en",
                "session_id": "lim2-upd",
            })
        args1, kwargs1 = mock1.call_args
        ctx1 = kwargs1.get("health_context") or (args1[2] if len(args1) > 2 else None)
        assert ctx1 is not None
        assert "outdoor worker" not in ctx1

        # Update profile — set outdoor_worker=True.
        # expire_all() clears SQLAlchemy's identity-map cache so the next
        # query fetches fresh data from the DB.  We must not rollback() here
        # because that would destroy the in-memory SQLite schema.
        db_session.expire_all()
        p = db_session.query(HealthProfile).filter_by(session_id="lim2-upd").first()
        p.outdoor_worker = True
        db_session.commit()
        db_session.expire_all()

        # Question 2 — outdoor_worker must now appear in context
        with patch("routers.assistant.ask_gemini", return_value=_MOCK_ANSWER) as mock2:
            api_client.post("/api/assistant/ask", json={
                "question": "Heat safety tips?",
                "language": "en",
                "session_id": "lim2-upd",
            })
        args2, kwargs2 = mock2.call_args
        ctx2 = kwargs2.get("health_context") or (args2[2] if len(args2) > 2 else None)
        assert ctx2 is not None
        assert "outdoor worker" in ctx2

    # ── Limitation 3: localisation — profile_active correct for all languages ──

    def test_profile_active_flag_correct_for_hindi(self, api_client, db_session):
        """profile_active flag works correctly regardless of language selection."""
        _make_profile(db_session, session_id="lim3-hi")
        with patch("routers.assistant.ask_gemini", return_value="हाइड्रेटेड रहें"):
            resp = api_client.post("/api/assistant/ask", json={
                "question": "गर्मी में क्या करें?",
                "language": "hi",
                "session_id": "lim3-hi",
            })
        assert resp.status_code == 200
        assert resp.json()["profile_active"] is True
        assert resp.json()["language"] == "hi"

    def test_profile_active_flag_correct_for_telugu(self, api_client, db_session):
        """profile_active flag works correctly for Telugu."""
        _make_profile(db_session, session_id="lim3-te")
        with patch("routers.assistant.ask_gemini", return_value="నీరు తాగండి"):
            resp = api_client.post("/api/assistant/ask", json={
                "question": "వేడిలో ఏమి చేయాలి?",
                "language": "te",
                "session_id": "lim3-te",
            })
        assert resp.status_code == 200
        assert resp.json()["profile_active"] is True
        assert resp.json()["language"] == "te"

    def test_no_profile_generic_flag_correct_for_hindi(self, api_client, db_session):
        """No-profile path returns profile_active=False for Hindi."""
        with patch("routers.assistant.ask_gemini", return_value="हाइड्रेटेड रहें"):
            resp = api_client.post("/api/assistant/ask", json={
                "question": "गर्मी में क्या करें?",
                "language": "hi",
            })
        assert resp.status_code == 200
        assert resp.json()["profile_active"] is False


# ── _build_health_context unit-tests (no HTTP, no DB) ─────────────────────────

class TestBuildHealthContext:

    def _profile(self, age_group=None, conditions=None, outdoor_worker=False):
        # Use SimpleNamespace instead of HealthProfile.__new__ to avoid
        # triggering SQLAlchemy's ORM instrumentation on an unbound instance.
        from types import SimpleNamespace
        return SimpleNamespace(age_group=age_group, conditions=conditions,
                               outdoor_worker=outdoor_worker)

    def test_full_profile_includes_all_parts(self):
        p = self._profile("60+", "cardiovascular,diabetes", True)
        ctx = _build_health_context(p)
        assert "60 years old or older" in ctx
        assert "cardiovascular" in ctx
        assert "diabetes" in ctx
        assert "outdoor worker" in ctx

    def test_none_condition_is_silently_ignored(self):
        p = self._profile(conditions="none")
        ctx = _build_health_context(p)
        assert "none" not in ctx

    def test_profile_with_only_none_condition_returns_empty(self):
        p = self._profile(age_group=None, conditions="none", outdoor_worker=False)
        ctx = _build_health_context(p)
        assert ctx == ""

    def test_unknown_condition_code_is_ignored(self):
        """Unknown codes (not in the allowlist) must not appear in context."""
        p = self._profile(conditions="cardiovascular,unknown_code")
        ctx = _build_health_context(p)
        assert "unknown_code" not in ctx
        assert "cardiovascular" in ctx

    def test_outdoor_worker_only_profile(self):
        p = self._profile(outdoor_worker=True)
        ctx = _build_health_context(p)
        assert "outdoor worker" in ctx

    def test_age_only_profile(self):
        p = self._profile(age_group="18-40")
        ctx = _build_health_context(p)
        assert "18–40" in ctx

    def test_no_fields_returns_empty_string(self):
        p = self._profile()
        assert _build_health_context(p) == ""


# ── _get_health_context unit-tests ────────────────────────────────────────────

class TestGetHealthContext:

    def test_none_session_id_returns_none(self, db_session):
        assert _get_health_context(None, db_session) is None

    def test_empty_session_id_returns_none(self, db_session):
        assert _get_health_context("", db_session) is None

    def test_whitespace_session_id_returns_none(self, db_session):
        assert _get_health_context("   ", db_session) is None

    def test_missing_profile_returns_none(self, db_session):
        assert _get_health_context("nonexistent-uuid", db_session) is None

    def test_existing_profile_returns_context_string(self, db_session):
        _make_profile(db_session, session_id="ctx-test", age_group="41-60",
                      conditions="respiratory", outdoor_worker=False)
        ctx = _get_health_context("ctx-test", db_session)
        assert ctx is not None
        assert "respiratory" in ctx
        assert "41" in ctx

    def test_profile_with_no_actionable_data_returns_none(self, db_session):
        _make_profile(db_session, session_id="ctx-empty",
                      age_group=None, conditions="none", outdoor_worker=False)
        assert _get_health_context("ctx-empty", db_session) is None
