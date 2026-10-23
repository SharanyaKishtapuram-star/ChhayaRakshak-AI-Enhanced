"""
test_health_assistant.py — Tests for the Personal Health Assistant endpoint
and the new conversation-history feature on the general assistant.

POST /api/assistant/ask-health
  - Valid profile → 200, profile_active=True, answer returned
  - Missing profile (never existed) → 404
  - Deleted profile → 404
  - Missing session_id (empty string) → 422
  - No actionable context (only 'none' condition) → 200, answer with generic fallback
  - Gemini API errors propagate with correct HTTP status codes
  - No health data in error responses

POST /api/assistant/ask  (conversation history additions)
  - conversation_history is forwarded to ask_gemini
  - Empty conversation_history is handled gracefully
  - History with 20 turns accepted (server caps at 10)

ask_gemini_health() service-layer unit-tests
  - Raises ValueError when health_context is empty
  - Passes health_context and history to the Gemini API

All Gemini calls are mocked — no real API key required.
"""

import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from main import app
from services.gemini_service import GeminiServiceError, ask_gemini_health
from database.db import Base, get_db
from database.models import HealthProfile

# ── In-memory SQLite fixture ──────────────────────────────────────────────────

_TEST_DB_URL = "sqlite://"

@pytest.fixture()
def db_session():
    engine = create_engine(
        _TEST_DB_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    session = TestingSessionLocal()
    try:
        app.dependency_overrides[get_db] = lambda: session
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)
        app.dependency_overrides.pop(get_db, None)


@pytest.fixture()
def api_client(db_session):
    return TestClient(app)


def _make_profile(
    db,
    session_id: str = "hp-test-sid",
    age_group: str = "60+",
    conditions: str = "cardiovascular",
    outdoor_worker: bool = False,
) -> HealthProfile:
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


_MOCK_ANSWER = "Drink plenty of water and stay in the shade during peak hours."


# ── POST /api/assistant/ask-health ────────────────────────────────────────────

class TestAskHealthEndpoint:

    def _ask_health(self, client, session_id, question="What heat precautions should I take?"):
        return client.post("/api/assistant/ask-health", json={
            "question": question,
            "session_id": session_id,
        })

    def test_valid_profile_returns_200(self, api_client, db_session):
        _make_profile(db_session, session_id="hp-001")
        with patch("routers.assistant.ask_gemini_health", return_value=_MOCK_ANSWER):
            resp = self._ask_health(api_client, "hp-001")
        assert resp.status_code == 200

    def test_valid_profile_returns_answer(self, api_client, db_session):
        _make_profile(db_session, session_id="hp-002")
        with patch("routers.assistant.ask_gemini_health", return_value=_MOCK_ANSWER):
            resp = self._ask_health(api_client, "hp-002")
        assert resp.json()["answer"] == _MOCK_ANSWER

    def test_valid_profile_profile_active_true(self, api_client, db_session):
        _make_profile(db_session, session_id="hp-003")
        with patch("routers.assistant.ask_gemini_health", return_value=_MOCK_ANSWER):
            resp = self._ask_health(api_client, "hp-003")
        assert resp.json()["profile_active"] is True

    def test_valid_profile_passes_health_context_to_service(self, api_client, db_session):
        """The endpoint must forward a non-empty health_context to ask_gemini_health."""
        _make_profile(
            db_session,
            session_id="hp-004",
            age_group="60+",
            conditions="cardiovascular,kidney_disease",
            outdoor_worker=True,
        )
        with patch("routers.assistant.ask_gemini_health", return_value=_MOCK_ANSWER) as mock_fn:
            self._ask_health(api_client, "hp-004")

        args, kwargs = mock_fn.call_args
        ctx = kwargs.get("health_context") or (args[1] if len(args) > 1 else None)
        assert ctx is not None
        assert "cardiovascular" in ctx
        assert "kidney" in ctx
        assert "outdoor worker" in ctx
        assert "60" in ctx

    def test_missing_profile_returns_404(self, api_client, db_session):
        """Non-existent session_id must return 404 (not fall back silently)."""
        with patch("routers.assistant.ask_gemini_health", return_value=_MOCK_ANSWER):
            resp = self._ask_health(api_client, "does-not-exist")
        assert resp.status_code == 404

    def test_deleted_profile_returns_404(self, api_client, db_session):
        """Profile deleted before the request must return 404."""
        _make_profile(db_session, session_id="hp-del")
        p = db_session.query(HealthProfile).filter_by(session_id="hp-del").first()
        db_session.delete(p)
        db_session.commit()

        with patch("routers.assistant.ask_gemini_health", return_value=_MOCK_ANSWER):
            resp = self._ask_health(api_client, "hp-del")
        assert resp.status_code == 404

    def test_404_message_is_informative(self, api_client, db_session):
        """The 404 detail must guide the user to re-save their profile."""
        resp = self._ask_health(api_client, "nonexistent-sid")
        detail = resp.json().get("detail", "")
        assert "profile" in detail.lower()

    def test_empty_session_id_returns_422(self, api_client, db_session):
        """Empty / whitespace session_id must be rejected before touching the DB."""
        resp = api_client.post("/api/assistant/ask-health", json={
            "question": "What precautions should I take?",
            "session_id": "   ",
        })
        assert resp.status_code == 422

    def test_missing_session_id_field_returns_422(self, api_client, db_session):
        """session_id is required; omitting it must return 422."""
        resp = api_client.post("/api/assistant/ask-health", json={
            "question": "What precautions should I take?",
        })
        assert resp.status_code == 422

    def test_question_too_short_returns_422(self, api_client, db_session):
        resp = api_client.post("/api/assistant/ask-health", json={
            "question": "Hi",
            "session_id": "any-sid",
        })
        assert resp.status_code == 422

    def test_profile_with_no_actionable_context_still_returns_200(self, api_client, db_session):
        """
        A profile with only 'none' conditions and no age / outdoor_worker produces
        an empty _build_health_context, but the endpoint substitutes a generic
        fallback string and still answers.
        """
        _make_profile(
            db_session,
            session_id="hp-nocontext",
            age_group=None,
            conditions="none",
            outdoor_worker=False,
        )
        with patch("routers.assistant.ask_gemini_health", return_value=_MOCK_ANSWER) as mock_fn:
            resp = self._ask_health(api_client, "hp-nocontext")
        assert resp.status_code == 200
        # The endpoint must still call ask_gemini_health (with the fallback string)
        assert mock_fn.called
        args, kwargs = mock_fn.call_args
        ctx = kwargs.get("health_context") or (args[1] if len(args) > 1 else None)
        # Fallback string should be non-empty
        assert ctx and len(ctx) > 0

    def test_gemini_rate_limit_returns_429(self, api_client, db_session):
        _make_profile(db_session, session_id="hp-429")
        with patch("routers.assistant.ask_gemini_health",
                   side_effect=GeminiServiceError("quota", status_code=429)):
            resp = self._ask_health(api_client, "hp-429")
        assert resp.status_code == 429

    def test_gemini_key_missing_returns_503(self, api_client, db_session):
        _make_profile(db_session, session_id="hp-503")
        with patch("routers.assistant.ask_gemini_health",
                   side_effect=GeminiServiceError("key missing", status_code=503)):
            resp = self._ask_health(api_client, "hp-503")
        assert resp.status_code == 503

    def test_gemini_network_error_returns_502(self, api_client, db_session):
        _make_profile(db_session, session_id="hp-502")
        with patch("routers.assistant.ask_gemini_health",
                   side_effect=GeminiServiceError("network", status_code=502)):
            resp = self._ask_health(api_client, "hp-502")
        assert resp.status_code == 502

    def test_404_does_not_leak_health_data(self, api_client, db_session):
        """The 404 detail must not contain any health condition values."""
        resp = self._ask_health(api_client, "nonexistent-sid")
        detail = str(resp.json().get("detail", ""))
        for condition in ("cardiovascular", "respiratory", "diabetes", "kidney"):
            assert condition not in detail

    def test_response_language_is_english(self, api_client, db_session):
        """The health assistant always responds in English (for safety)."""
        _make_profile(db_session, session_id="hp-lang")
        with patch("routers.assistant.ask_gemini_health", return_value=_MOCK_ANSWER):
            resp = self._ask_health(api_client, "hp-lang")
        assert resp.json()["language"] == "en"
        assert resp.json()["language_name"] == "English"


# ── Conversation history — /ask-health ───────────────────────────────────────

class TestHealthAssistantConversationHistory:

    def test_conversation_history_is_forwarded(self, api_client, db_session):
        """conversation_history supplied by the client must reach ask_gemini_health."""
        _make_profile(db_session, session_id="hp-hist-01")
        history = [
            {"role": "user",      "text": "Is it safe to walk in 42 degree heat?"},
            {"role": "assistant", "text": "No, avoid outdoor activity above 40°C."},
        ]
        with patch("routers.assistant.ask_gemini_health", return_value=_MOCK_ANSWER) as mock_fn:
            api_client.post("/api/assistant/ask-health", json={
                "question": "What about cycling?",
                "session_id": "hp-hist-01",
                "conversation_history": history,
            })
        args, kwargs = mock_fn.call_args
        fwd_history = kwargs.get("conversation_history") or (args[3] if len(args) > 3 else None)
        assert fwd_history is not None
        assert len(fwd_history) == 2
        assert fwd_history[0]["role"] == "user"

    def test_no_conversation_history_works(self, api_client, db_session):
        """Omitting conversation_history must still return 200."""
        _make_profile(db_session, session_id="hp-hist-02")
        with patch("routers.assistant.ask_gemini_health", return_value=_MOCK_ANSWER):
            resp = api_client.post("/api/assistant/ask-health", json={
                "question": "What should I wear in extreme heat?",
                "session_id": "hp-hist-02",
            })
        assert resp.status_code == 200

    def test_empty_conversation_history_works(self, api_client, db_session):
        """Empty list for conversation_history must be handled gracefully."""
        _make_profile(db_session, session_id="hp-hist-03")
        with patch("routers.assistant.ask_gemini_health", return_value=_MOCK_ANSWER):
            resp = api_client.post("/api/assistant/ask-health", json={
                "question": "What should I eat during a heatwave?",
                "session_id": "hp-hist-03",
                "conversation_history": [],
            })
        assert resp.status_code == 200


# ── Conversation history — /ask ───────────────────────────────────────────────

class TestGeneralAssistantConversationHistory:

    def _ask_with_history(self, client, question, history=None):
        body = {"question": question, "language": "en"}
        if history is not None:
            body["conversation_history"] = history
        return client.post("/api/assistant/ask", json=body)

    def test_conversation_history_forwarded_to_ask_gemini(self, api_client, db_session):
        """Conversation history supplied by client must reach ask_gemini."""
        history = [
            {"role": "user",      "text": "What is a heat island?"},
            {"role": "assistant", "text": "Urban areas with higher temperatures than surroundings."},
        ]
        with patch("routers.assistant.ask_gemini", return_value=_MOCK_ANSWER) as mock_fn:
            resp = self._ask_with_history(api_client, "How can cities reduce this?", history)
        assert resp.status_code == 200
        args, kwargs = mock_fn.call_args
        fwd = kwargs.get("conversation_history") or (args[3] if len(args) > 3 else None)
        assert fwd is not None
        assert len(fwd) == 2

    def test_no_history_still_works(self, api_client, db_session):
        """Existing callers without history must continue to work."""
        with patch("routers.assistant.ask_gemini", return_value=_MOCK_ANSWER):
            resp = self._ask_with_history(api_client, "What to do in a heatwave?")
        assert resp.status_code == 200
        assert resp.json()["answer"] == _MOCK_ANSWER

    def test_empty_history_list_works(self, api_client, db_session):
        with patch("routers.assistant.ask_gemini", return_value=_MOCK_ANSWER):
            resp = self._ask_with_history(api_client, "What to do in a heatwave?", history=[])
        assert resp.status_code == 200

    def test_history_with_twenty_turns_accepted(self, api_client, db_session):
        """The schema allows up to 20 turns; server caps forwarding at 10."""
        history = [
            {"role": "user" if i % 2 == 0 else "assistant", "text": f"Turn {i}"}
            for i in range(20)
        ]
        with patch("routers.assistant.ask_gemini", return_value=_MOCK_ANSWER):
            resp = self._ask_with_history(api_client, "Follow-up question?", history)
        assert resp.status_code == 200

    def test_history_not_persisted_server_side(self, api_client, db_session):
        """
        Two requests with the same session_id but different histories must each
        use the history supplied in that specific request — no server-side accumulation.
        """
        _make_profile(db_session, session_id="hist-persist-test")
        history_a = [{"role": "user", "text": "First question"}, {"role": "assistant", "text": "First answer"}]
        history_b = [{"role": "user", "text": "Different question"}, {"role": "assistant", "text": "Different answer"}]

        captured = []
        def _capture(*args, **kwargs):
            h = kwargs.get("conversation_history") or (args[3] if len(args) > 3 else None)
            captured.append(h)
            return _MOCK_ANSWER

        with patch("routers.assistant.ask_gemini", side_effect=_capture):
            api_client.post("/api/assistant/ask", json={
                "question": "What to do in heat?", "language": "en",
                "session_id": "hist-persist-test",
                "conversation_history": history_a,
            })
            api_client.post("/api/assistant/ask", json={
                "question": "What to do in heat?", "language": "en",
                "session_id": "hist-persist-test",
                "conversation_history": history_b,
            })

        assert captured[0][0]["text"] == "First question"
        assert captured[1][0]["text"] == "Different question"


# ── ask_gemini_health() service unit-tests ────────────────────────────────────

class TestAskGeminiHealthService:

    def test_empty_health_context_raises_value_error(self):
        with pytest.raises(ValueError, match="non-empty health_context"):
            ask_gemini_health("A question", health_context="")

    def test_whitespace_health_context_raises_value_error(self):
        with pytest.raises(ValueError):
            ask_gemini_health("A question", health_context="   ")

    def test_missing_api_key_raises_gemini_service_error(self):
        """Without a configured API key, should raise GeminiServiceError 503."""
        import os
        with patch.dict("os.environ", {"GEMINI_API_KEY": ""}, clear=False):
            with pytest.raises(GeminiServiceError) as exc_info:
                ask_gemini_health(
                    "What precautions should I take?",
                    health_context="cardiovascular condition; outdoor worker",
                )
        assert exc_info.value.status_code == 503

    def test_passes_health_context_in_prompt(self):
        """The health_context string must appear in the prompt sent to Gemini."""
        with patch("services.gemini_service._get_client") as mock_client:
            mock_response = MagicMock()
            mock_response.text = _MOCK_ANSWER
            mock_client.return_value.models.generate_content.return_value = mock_response

            result = ask_gemini_health(
                "What should I do?",
                health_context="elderly; diabetes",
            )

        call_kwargs = mock_client.return_value.models.generate_content.call_args
        prompt_arg = call_kwargs[1].get("contents") or call_kwargs[0][1]
        assert "elderly" in prompt_arg
        assert "diabetes" in prompt_arg
        assert result == _MOCK_ANSWER

    def test_passes_conversation_history_in_prompt(self):
        """Prior turns must appear in the prompt when conversation_history is supplied."""
        history = [
            {"role": "user",      "text": "Is outdoor exercise safe?"},
            {"role": "assistant", "text": "Avoid exercise above 40°C."},
        ]
        with patch("services.gemini_service._get_client") as mock_client:
            mock_response = MagicMock()
            mock_response.text = _MOCK_ANSWER
            mock_client.return_value.models.generate_content.return_value = mock_response

            ask_gemini_health(
                "What about cycling?",
                health_context="cardiovascular condition",
                conversation_history=history,
            )

        call_kwargs = mock_client.return_value.models.generate_content.call_args
        prompt_arg = call_kwargs[1].get("contents") or call_kwargs[0][1]
        assert "outdoor exercise" in prompt_arg
        assert "cycling" in prompt_arg

    def test_history_capped_at_ten_turns(self):
        """Only the last 10 turns of a long history must be included in the prompt."""
        history = [
            {"role": "user" if i % 2 == 0 else "assistant", "text": f"Turn {i}"}
            for i in range(20)
        ]
        with patch("services.gemini_service._get_client") as mock_client:
            mock_response = MagicMock()
            mock_response.text = _MOCK_ANSWER
            mock_client.return_value.models.generate_content.return_value = mock_response

            ask_gemini_health(
                "Latest question",
                health_context="respiratory condition",
                conversation_history=history,
            )

        call_kwargs = mock_client.return_value.models.generate_content.call_args
        prompt_arg = call_kwargs[1].get("contents") or call_kwargs[0][1]
        # Turn 0 is the 1st item — must NOT appear (only last 10 kept: turns 10–19)
        assert "Turn 0" not in prompt_arg
        # Turn 19 (last) must appear
        assert "Turn 19" in prompt_arg


# ── Consent / profile-data privacy checks ────────────────────────────────────

class TestHealthAssistantPrivacy:

    def test_session_id_not_forwarded_to_gemini(self, api_client, db_session):
        """The session_id must never appear in the prompt sent to ask_gemini_health."""
        _make_profile(db_session, session_id="privacy-sid-xyz")
        captured_prompt = []

        def _capture(*args, **kwargs):
            prompt = args[0] if args else ""
            captured_prompt.append(prompt)
            return _MOCK_ANSWER

        with patch("services.gemini_service._get_client") as mock_client:
            mock_response = MagicMock()
            mock_response.text = _MOCK_ANSWER
            mock_client.return_value.models.generate_content.return_value = mock_response
            api_client.post("/api/assistant/ask-health", json={
                "question": "What precautions should I take?",
                "session_id": "privacy-sid-xyz",
            })

        call_kwargs = mock_client.return_value.models.generate_content.call_args
        prompt_arg = call_kwargs[1].get("contents") or call_kwargs[0][1]
        assert "privacy-sid-xyz" not in prompt_arg

    def test_profile_not_active_for_missing_profile(self, api_client, db_session):
        """When /ask is called with a non-existent session_id, profile_active=False."""
        with patch("routers.assistant.ask_gemini", return_value=_MOCK_ANSWER):
            resp = api_client.post("/api/assistant/ask", json={
                "question": "What to do in heat?",
                "language": "en",
                "session_id": "privacy-no-profile",
            })
        assert resp.status_code == 200
        assert resp.json()["profile_active"] is False
