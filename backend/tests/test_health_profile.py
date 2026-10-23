"""
test_health_profile.py — Personal Health Profile endpoint tests

All tests use an in-memory SQLite database (overrides the app dependency)
so no file is created or modified during testing.

SQLite in-memory requires StaticPool to share the same connection across
multiple sessions — without it each new connection would get a blank DB.

Test coverage:
  - POST /api/health/profile   — create (happy path, consent rejection, validation)
  - GET  /api/health/profile/{session_id} — retrieve (happy path, 404)
  - DELETE /api/health/profile/{session_id} — delete (happy path, 404, idempotency)
  - Privacy checks: health data not leaked in error messages
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from main import app
from database.db import get_db
from database.models import Base

# ── In-memory SQLite override ─────────────────────────────────────────────────
# StaticPool forces SQLAlchemy to reuse ONE connection for the entire test run,
# so all sessions see the same in-memory database.

TEST_DB_URL = "sqlite://"

_engine = create_engine(
    TEST_DB_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_engine)

# Create tables once when the module loads
Base.metadata.create_all(bind=_engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _create_profile(**kwargs):
    """Helper: POST a valid profile and return the response."""
    payload = {
        "consent_given": True,
        "age_group": "41-60",
        "conditions": ["cardiovascular"],
        "outdoor_worker": False,
    }
    payload.update(kwargs)
    return client.post("/api/health/profile", json=payload)


# ── POST /api/health/profile ──────────────────────────────────────────────────

class TestCreateProfile:

    def test_create_returns_201(self):
        res = _create_profile()
        assert res.status_code == 201

    def test_create_returns_session_id(self):
        res = _create_profile()
        data = res.json()
        assert "session_id" in data
        assert len(data["session_id"]) == 36   # UUID4 string length

    def test_session_ids_are_unique(self):
        id1 = _create_profile().json()["session_id"]
        id2 = _create_profile().json()["session_id"]
        assert id1 != id2

    def test_create_echoes_age_group(self):
        res = _create_profile(age_group="18-40")
        assert res.json()["age_group"] == "18-40"

    def test_create_echoes_conditions(self):
        res = _create_profile(conditions=["respiratory", "diabetes"])
        conds = res.json()["conditions"]
        assert set(conds) == {"respiratory", "diabetes"}

    def test_create_echoes_outdoor_worker(self):
        res = _create_profile(outdoor_worker=True)
        assert res.json()["outdoor_worker"] is True

    def test_create_with_none_condition(self):
        res = _create_profile(conditions=["none"])
        assert res.status_code == 201
        assert res.json()["conditions"] == ["none"]

    def test_create_without_age_group(self):
        res = _create_profile(age_group=None)
        assert res.status_code == 201
        assert res.json()["age_group"] is None

    def test_create_without_conditions(self):
        res = _create_profile(conditions=None)
        assert res.status_code == 201
        # conditions may be None or absent
        conds = res.json().get("conditions")
        assert conds is None or conds == []

    def test_no_consent_returns_422(self):
        res = client.post("/api/health/profile", json={
            "consent_given": False,
            "age_group": "18-40",
        })
        assert res.status_code == 422

    def test_missing_consent_field_returns_422(self):
        res = client.post("/api/health/profile", json={
            "age_group": "18-40",
            "outdoor_worker": False,
        })
        assert res.status_code == 422

    def test_invalid_age_group_returns_422(self):
        res = _create_profile(age_group="25")   # not in the Literal enum
        assert res.status_code == 422

    def test_invalid_condition_returns_422(self):
        res = _create_profile(conditions=["fever"])   # free-text not allowed
        assert res.status_code == 422

    def test_none_with_other_conditions_returns_422(self):
        res = _create_profile(conditions=["none", "cardiovascular"])
        assert res.status_code == 422

    def test_no_consent_error_does_not_leak_health_data(self):
        """Error detail must not contain any health condition values."""
        res = client.post("/api/health/profile", json={
            "consent_given": False,
            "age_group": "60+",
            "conditions": ["cardiovascular"],
        })
        detail = str(res.json().get("detail", ""))
        # None of the condition labels should appear in the error response
        for condition in ("cardiovascular", "respiratory", "diabetes"):
            assert condition not in detail

    def test_response_has_message_field(self):
        res = _create_profile()
        assert "message" in res.json()


# ── GET /api/health/profile/{session_id} ─────────────────────────────────────

class TestGetProfile:

    def test_get_existing_profile_returns_200(self):
        sid = _create_profile().json()["session_id"]
        res = client.get(f"/api/health/profile/{sid}")
        assert res.status_code == 200

    def test_get_returns_correct_session_id(self):
        sid = _create_profile(age_group="60+").json()["session_id"]
        data = client.get(f"/api/health/profile/{sid}").json()
        assert data["session_id"] == sid

    def test_get_returns_correct_age_group(self):
        sid = _create_profile(age_group="under-18").json()["session_id"]
        assert client.get(f"/api/health/profile/{sid}").json()["age_group"] == "under-18"

    def test_get_returns_correct_conditions(self):
        sid = _create_profile(conditions=["diabetes", "elderly"]).json()["session_id"]
        conds = set(client.get(f"/api/health/profile/{sid}").json()["conditions"])
        assert conds == {"diabetes", "elderly"}

    def test_get_returns_correct_outdoor_worker(self):
        sid = _create_profile(outdoor_worker=True).json()["session_id"]
        assert client.get(f"/api/health/profile/{sid}").json()["outdoor_worker"] is True

    def test_get_nonexistent_returns_404(self):
        res = client.get("/api/health/profile/00000000-0000-0000-0000-000000000000")
        assert res.status_code == 404

    def test_404_message_does_not_reveal_internals(self):
        """404 detail should be generic — no stack traces or DB info."""
        res = client.get("/api/health/profile/does-not-exist")
        detail = res.json()["detail"]
        assert "sql" not in detail.lower()
        assert "database" not in detail.lower()
        assert "column" not in detail.lower()


# ── DELETE /api/health/profile/{session_id} ───────────────────────────────────

class TestDeleteProfile:

    def test_delete_returns_200(self):
        sid = _create_profile().json()["session_id"]
        res = client.delete(f"/api/health/profile/{sid}")
        assert res.status_code == 200

    def test_delete_removes_profile(self):
        sid = _create_profile().json()["session_id"]
        client.delete(f"/api/health/profile/{sid}")
        # Profile should now be gone
        res = client.get(f"/api/health/profile/{sid}")
        assert res.status_code == 404

    def test_delete_has_confirmation_message(self):
        sid = _create_profile().json()["session_id"]
        data = client.delete(f"/api/health/profile/{sid}").json()
        assert "message" in data
        assert len(data["message"]) > 0

    def test_delete_nonexistent_returns_404(self):
        res = client.delete("/api/health/profile/00000000-0000-0000-0000-000000000001")
        assert res.status_code == 404

    def test_delete_then_recreate_works(self):
        """Deleting a profile and creating a fresh one must succeed."""
        sid = _create_profile().json()["session_id"]
        client.delete(f"/api/health/profile/{sid}")
        new_res = _create_profile()
        assert new_res.status_code == 201
        assert new_res.json()["session_id"] != sid


# ── Privacy regression checks ─────────────────────────────────────────────────

class TestPrivacyConstraints:

    def test_session_id_is_uuid4_format(self):
        """Session IDs must look like UUID4 strings."""
        import re
        UUID4_RE = re.compile(
            r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
        )
        sid = _create_profile().json()["session_id"]
        assert UUID4_RE.match(sid), f"session_id does not look like UUID4: {sid}"

    def test_response_does_not_include_db_primary_key(self):
        """The internal integer PK must not be exposed in the API response."""
        res = _create_profile()
        data = res.json()
        assert "id" not in data

    def test_response_does_not_include_consent_field(self):
        """consent_given is write-only input — not echoed in the response."""
        res = _create_profile()
        data = res.json()
        assert "consent_given" not in data

    def test_multiple_conditions_stored_and_retrieved_correctly(self):
        conditions = ["respiratory", "kidney_disease", "outdoor_worker"]
        # outdoor_worker is a separate boolean, so it shouldn't be in conditions list
        conditions = ["respiratory", "kidney_disease"]
        sid = _create_profile(conditions=conditions).json()["session_id"]
        retrieved = set(client.get(f"/api/health/profile/{sid}").json()["conditions"])
        assert retrieved == set(conditions)
