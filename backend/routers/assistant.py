"""
assistant.py — Multilingual AI Heat Protection Assistant router (Phase 2)

Endpoints:
    POST /api/assistant/ask         — general heat-safety assistant (multilingual,
                                      optional health-profile context, conversation history)
    POST /api/assistant/ask-health  — Personal Heat-Safety Assistant (profile-locked,
                                      stricter prompt, requires a saved profile with consent)
    GET  /api/assistant/status      — check whether GEMINI_API_KEY is configured

Privacy / safety constraints enforced here:
  - Only allowlisted category labels are forwarded (e.g. "cardiovascular") —
    never raw DB rows, session IDs, or free-text notes.
  - Health data is never included in Python log output or error strings.
  - If the profile is not found (invalid/deleted session_id), /ask falls back
    silently to generic behaviour; /ask-health returns 404 so the UI can
    inform the user their profile is missing.
  - The model is instructed not to diagnose conditions or advise on medication.
  - Conversation history is accepted from the client but never persisted server-side.
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Literal
from sqlalchemy.orm import Session

from services.gemini_service import (
    ask_gemini,
    ask_gemini_health,
    GeminiServiceError,
    SUPPORTED_LANGUAGES,
)
from database.db import get_db
from database.models import HealthProfile

log = logging.getLogger(__name__)   # health data is never passed to this logger

router = APIRouter(prefix="/api/assistant", tags=["AI Assistant"])


# ── Shared models ─────────────────────────────────────────────────────────────

class ConversationTurn(BaseModel):
    """A single prior conversation turn for follow-up context."""
    role: Literal["user", "assistant"]
    text: str = Field(..., max_length=2000)


# ── Request / Response models — /ask ─────────────────────────────────────────

class AskRequest(BaseModel):
    question: str = Field(
        ...,
        min_length=3,
        max_length=1000,
        description="The heat-protection question to ask the AI",
        examples=["What should I do during a heatwave?"],
    )
    language: Literal["en", "hi", "te"] = Field(
        "en",
        description="Response language: en=English, hi=Hindi, te=Telugu",
    )
    session_id: Optional[str] = Field(
        None,
        description=(
            "Optional anonymous session ID from the user's saved health profile. "
            "When provided, the assistant retrieves the profile and tailors "
            "heat-safety advice accordingly. "
            "If the profile is not found the assistant falls back to generic guidance."
        ),
    )
    conversation_history: Optional[list[ConversationTurn]] = Field(
        None,
        max_length=20,
        description=(
            "Optional list of prior turns (newest last) for follow-up context. "
            "Each item has role ('user' or 'assistant') and text. "
            "At most 10 turns are forwarded to the model. "
            "Never stored server-side."
        ),
    )


# ── Request model — /ask-health ───────────────────────────────────────────────

class AskHealthRequest(BaseModel):
    question: str = Field(
        ...,
        min_length=3,
        max_length=1000,
        description="The heat-safety question for the Personal Health Assistant",
        examples=["What extra precautions should I take given my heart condition?"],
    )
    session_id: str = Field(
        ...,
        description=(
            "Anonymous session ID from the user's saved health profile. "
            "Required — the health assistant only works when a valid profile is found."
        ),
    )
    conversation_history: Optional[list[ConversationTurn]] = Field(
        None,
        max_length=20,
        description="Optional prior turns for follow-up context (same format as /ask).",
    )


# ── Health context builder ────────────────────────────────────────────────────

# Human-readable labels for each condition code.
# Kept minimal — only what is useful for heat-safety personalisation.
_CONDITION_LABELS: dict[str, str] = {
    "cardiovascular": "a cardiovascular condition",
    "respiratory":    "a respiratory condition",
    "diabetes":       "diabetes",
    "kidney_disease": "kidney disease",
    "pregnant":       "currently pregnant",
    "elderly":        "elderly with additional care needs",
    "young_child":    "caring for a young child",
}

_AGE_LABELS: dict[str, str] = {
    "under-18": "under 18 years old",
    "18-40":    "18–40 years old",
    "41-60":    "41–60 years old",
    "60+":      "60 years old or older",
}


def _build_health_context(profile: HealthProfile) -> str:
    """
    Translate stored category labels into a short, natural-language summary
    suitable for inclusion in a Gemini prompt.

    Example output:
        "60 years old or older; conditions: a cardiovascular condition, diabetes;
         outdoor worker"

    Only allowlisted labels are used — raw DB values are never forwarded.
    The 'none' condition is silently ignored (it means no conditions).
    """
    parts: list[str] = []

    if profile.age_group and profile.age_group in _AGE_LABELS:
        parts.append(_AGE_LABELS[profile.age_group])

    if profile.conditions:
        condition_codes = [c.strip() for c in profile.conditions.split(",") if c.strip()]
        readable = [
            _CONDITION_LABELS[code]
            for code in condition_codes
            if code in _CONDITION_LABELS   # 'none' is not in the dict → silently skipped
        ]
        if readable:
            parts.append(f"conditions: {', '.join(readable)}")

    if profile.outdoor_worker:
        parts.append("outdoor worker")

    if not parts:
        return ""   # profile exists but has no actionable context

    return "; ".join(parts)


def _get_health_context(session_id: Optional[str], db: Session) -> Optional[str]:
    """
    Look up a health profile and return a context string, or None on any miss.

    Returns None (never raises) when:
      - session_id is None / empty
      - profile not found (deleted or invalid ID)
      - profile produces no actionable context
    """
    if not session_id or not session_id.strip():
        return None

    try:
        profile = db.query(HealthProfile).filter(
            HealthProfile.session_id == session_id.strip()
        ).first()
    except Exception:
        # DB errors must not bubble up and fail the user's question.
        log.warning("DB error while fetching health profile (session_id redacted)")
        return None

    if profile is None:
        return None

    context = _build_health_context(profile)
    return context if context else None


def _serialise_history(
    turns: Optional[list[ConversationTurn]],
) -> Optional[list[dict]]:
    """Convert Pydantic ConversationTurn objects to plain dicts for the service layer."""
    if not turns:
        return None
    return [{"role": t.role, "text": t.text} for t in turns]


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get(
    "/status",
    summary="Check whether the AI Assistant is configured and ready",
)
def assistant_status():
    """
    Returns whether GEMINI_API_KEY is configured.
    The frontend uses this to show a setup banner when the key is missing.
    """
    import os
    from dotenv import load_dotenv
    load_dotenv()
    key = os.getenv("GEMINI_API_KEY", "").strip()
    configured = bool(key) and key != "your_gemini_api_key_here"
    return {
        "configured": configured,
        "supported_languages": SUPPORTED_LANGUAGES,
        "message": (
            "AI Assistant is ready."
            if configured
            else (
                "GEMINI_API_KEY is not set. "
                "Add it to backend/.env to enable the assistant. "
                "Get a free key at https://aistudio.google.com/app/apikey"
            )
        ),
    }


@router.post(
    "/ask",
    summary="Ask the multilingual AI heat-protection assistant",
    response_description="AI-generated answer in the requested language",
)
def ask_assistant(req: AskRequest, db: Session = Depends(get_db)):
    """
    Send a heat-protection question to Gemini and receive an answer in
    English, Hindi (हिन्दी), or Telugu (తెలుగు).

    Optionally supply a session_id to receive health-profile-personalised guidance,
    and conversation_history for follow-up context.  Both are optional and degrade
    gracefully when absent.

    Requires GEMINI_API_KEY to be set in backend/.env.
    Returns HTTP 503 with setup instructions if the key is missing.
    """
    # Resolve health context — silently falls back to None on any miss.
    health_context = _get_health_context(req.session_id, db)
    profile_active = health_context is not None

    history = _serialise_history(req.conversation_history)

    try:
        answer = ask_gemini(
            req.question,
            req.language,
            health_context=health_context,
            conversation_history=history,
        )
        return {
            "question":      req.question,
            "answer":        answer,
            "language":      req.language,
            "language_name": SUPPORTED_LANGUAGES.get(req.language, "English"),
            "profile_active": profile_active,
        }
    except GeminiServiceError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail=str(exc),
        )


@router.post(
    "/ask-health",
    summary="Personal Heat-Safety Assistant (profile-locked)",
    response_description="Personalised heat-safety guidance based on the saved health profile",
)
def ask_health_assistant(req: AskHealthRequest, db: Session = Depends(get_db)):
    """
    Dedicated Personal Health Assistant endpoint.

    Unlike /ask, this endpoint:
      - Requires a valid session_id with a saved profile.  Returns 404 if the
        profile is not found so the UI can prompt the user to (re-)save their profile.
      - Uses a stricter, health-focused system prompt.
      - Never falls back to generic guidance — if there's no profile there's no answer.
      - Does not accept profile context from the client; it always re-reads the DB.

    Conversation history is accepted for follow-up questions within a session.
    History is never persisted server-side.
    """
    # Require a valid, non-empty session ID.
    if not req.session_id or not req.session_id.strip():
        raise HTTPException(
            status_code=422,
            detail="session_id is required for the Personal Health Assistant.",
        )

    # Look up the profile — unlike /ask, we return 404 rather than fall back.
    try:
        profile = db.query(HealthProfile).filter(
            HealthProfile.session_id == req.session_id.strip()
        ).first()
    except Exception:
        log.warning("DB error in ask-health endpoint (session_id redacted)")
        raise HTTPException(status_code=503, detail="Database temporarily unavailable.")

    if profile is None:
        raise HTTPException(
            status_code=404,
            detail=(
                "Health profile not found. Please save or restore your profile "
                "on the Health Profile page before using the Personal Health Assistant."
            ),
        )

    health_context = _build_health_context(profile)

    # Profile exists but has no actionable context (e.g. only 'none' conditions,
    # no age, not an outdoor worker) — answer generically with the health prompt
    # so we still respect consent and provide a useful response.
    if not health_context:
        health_context = "No specific health conditions or risk factors noted."

    history = _serialise_history(req.conversation_history)

    try:
        answer = ask_gemini_health(
            req.question,
            health_context=health_context,
            language_code="en",   # health assistant is English-only for safety
            conversation_history=history,
        )
        return {
            "question": req.question,
            "answer":   answer,
            "language": "en",
            "language_name": "English",
            "profile_active": True,
        }
    except GeminiServiceError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail=str(exc),
        )
