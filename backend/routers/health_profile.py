"""
health_profile.py — Personal Health Profile router

Endpoints:
    POST   /api/health/profile          — create or update a profile (consent required)
    GET    /api/health/profile/{sid}    — retrieve a profile by session_id
    DELETE /api/health/profile/{sid}    — permanently delete a profile

Privacy / security design:
  - No PII is stored. Identification is by a randomly generated UUID session_id only.
  - The caller receives the session_id on first creation and is responsible for
    storing it (frontend keeps it in localStorage; it is never sent to Gemini directly).
  - consent_given=True is required in the request body. If False or absent, 422 is returned.
  - age_group and conditions are validated against fixed allowlists — no free-text clinical
    notes can be stored.
  - Health data is never included in Python log output or error detail strings.
  - The session_id UUID is not considered sensitive on its own (it has no link to identity);
    the profile fields are what must be protected.
"""

import uuid
from typing import Optional, Literal, List
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from database.db import get_db
from database.models import HealthProfile, Base
from database.db import engine

# Ensure the table exists (safe: create_all is idempotent)
Base.metadata.create_all(bind=engine)

router = APIRouter(prefix="/api/health", tags=["Health Profile"])

# ── Allowlists ────────────────────────────────────────────────────────────────
# Only these exact labels are accepted; this prevents storing arbitrary text.

VALID_AGE_GROUPS: set[str] = {"under-18", "18-40", "41-60", "60+"}

VALID_CONDITIONS: set[str] = {
    "cardiovascular",
    "respiratory",
    "diabetes",
    "kidney_disease",
    "pregnant",
    "elderly",        # 60+ who additionally flag themselves as needing extra care
    "young_child",    # caregiver selecting on behalf of a young child
    "none",
}


# ── Pydantic models ───────────────────────────────────────────────────────────

class ProfileCreateRequest(BaseModel):
    consent_given: bool = Field(
        ...,
        description="Must be True. Explicit consent required before any data is saved.",
    )
    age_group: Optional[Literal["under-18", "18-40", "41-60", "60+"]] = Field(
        None,
        description="Broad age band. Optional.",
    )
    conditions: Optional[List[Literal[
        "cardiovascular", "respiratory", "diabetes",
        "kidney_disease", "pregnant", "elderly", "young_child", "none"
    ]]] = Field(
        None,
        description=(
            "Pre-defined health condition categories relevant to heat risk. "
            "Select 'none' if no conditions apply."
        ),
    )
    outdoor_worker: bool = Field(
        False,
        description="Whether the user regularly works outdoors.",
    )

    @field_validator("consent_given")
    @classmethod
    def must_consent(cls, v: bool) -> bool:
        if not v:
            raise ValueError(
                "consent_given must be true. "
                "Please review the privacy notice and provide explicit consent."
            )
        return v

    @field_validator("conditions")
    @classmethod
    def no_mixed_none(cls, v):
        """If 'none' is selected alongside other conditions, reject the request."""
        if v and "none" in v and len(v) > 1:
            raise ValueError(
                "'none' cannot be combined with other conditions. "
                "Select 'none' only if no conditions apply."
            )
        return v


class ProfileResponse(BaseModel):
    session_id: str
    age_group: Optional[str]
    conditions: Optional[List[str]]
    outdoor_worker: bool
    message: str


class DeleteResponse(BaseModel):
    message: str


# ── Helpers ───────────────────────────────────────────────────────────────────

def _conditions_to_str(conditions: Optional[List[str]]) -> Optional[str]:
    """Convert list → comma-separated string for DB storage."""
    if not conditions:
        return None
    return ",".join(sorted(set(conditions)))  # sorted for deterministic storage


def _str_to_conditions(raw: Optional[str]) -> Optional[List[str]]:
    """Convert comma-separated DB string → list."""
    if not raw:
        return None
    return [c.strip() for c in raw.split(",") if c.strip()]


def _get_profile_or_404(session_id: str, db: Session) -> HealthProfile:
    """Fetch profile by session_id; raise 404 if absent."""
    profile = db.query(HealthProfile).filter(
        HealthProfile.session_id == session_id
    ).first()
    if profile is None:
        raise HTTPException(
            status_code=404,
            detail="Health profile not found. The session ID may be incorrect or the profile may have been deleted.",
        )
    return profile


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post(
    "/profile",
    response_model=ProfileResponse,
    status_code=201,
    summary="Create a personal health profile (requires explicit consent)",
    response_description="Session ID and stored profile summary",
)
def create_profile(
    req: ProfileCreateRequest,
    db: Session = Depends(get_db),
):
    """
    Create an anonymous health profile.

    A randomly generated UUID is returned as the session_id.
    **Store this session_id in your client** (the frontend keeps it in
    localStorage). It is the only way to retrieve or delete the profile later.

    consent_given must be True — the frontend must display a privacy notice
    before calling this endpoint.

    No name, email, or device identifier is stored.
    """
    session_id = str(uuid.uuid4())
    conditions_str = _conditions_to_str(req.conditions)

    profile = HealthProfile(
        session_id=session_id,
        consent_given=True,        # validated by the Pydantic model already
        age_group=req.age_group,
        conditions=conditions_str,
        outdoor_worker=req.outdoor_worker,
    )
    db.add(profile)
    db.commit()
    db.refresh(profile)

    return ProfileResponse(
        session_id=session_id,
        age_group=profile.age_group,
        conditions=_str_to_conditions(profile.conditions),
        outdoor_worker=profile.outdoor_worker,
        message="Health profile saved. Your session ID has been returned — store it to access or delete your profile later.",
    )


@router.get(
    "/profile/{session_id}",
    response_model=ProfileResponse,
    summary="Retrieve a health profile by session ID",
    response_description="Stored profile data",
)
def get_profile(
    session_id: str,
    db: Session = Depends(get_db),
):
    """
    Retrieve an existing health profile using the session_id returned at creation.

    Returns the stored age group, conditions, and outdoor-worker flag.
    Returns 404 if the session_id is not found.
    """
    profile = _get_profile_or_404(session_id, db)
    return ProfileResponse(
        session_id=profile.session_id,
        age_group=profile.age_group,
        conditions=_str_to_conditions(profile.conditions),
        outdoor_worker=profile.outdoor_worker,
        message="Profile retrieved successfully.",
    )


@router.delete(
    "/profile/{session_id}",
    response_model=DeleteResponse,
    summary="Permanently delete a health profile",
    response_description="Confirmation of deletion",
)
def delete_profile(
    session_id: str,
    db: Session = Depends(get_db),
):
    """
    Permanently delete all stored health data for a session ID.

    This action cannot be undone. After deletion the session_id is no longer
    valid and the frontend should clear its localStorage entry.
    """
    profile = _get_profile_or_404(session_id, db)
    db.delete(profile)
    db.commit()
    return DeleteResponse(message="Health profile permanently deleted.")
