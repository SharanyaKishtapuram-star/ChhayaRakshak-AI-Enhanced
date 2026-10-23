"""
gemini_service.py — Google Gemini AI service (Phase 2 / AI Assistant)

Uses the new google-genai SDK (replaces deprecated google-generativeai).

Key design decisions:
  • API key is read from the GEMINI_API_KEY environment variable.
    If absent, a ServiceUnavailableError is raised immediately so the
    endpoint can return a clear 503 rather than a cryptic auth failure.
  • The system prompt constrains the model to heat-protection topics only,
    so it stays on-topic even if the user asks off-topic questions.
  • Language is passed in the prompt, not as a separate API parameter,
    because Gemini responds reliably when asked to reply in a specific language.
  • Quota / rate-limit errors from the Gemini API are caught and returned
    as 429 responses with a clear message.
  • Network errors are caught and returned as 502 responses.
  • ask_gemini()        — general heat-safety assistant, optional health context,
                          optional conversation history for follow-up questions.
  • ask_gemini_health() — profile-locked personal health assistant; requires a
                          valid health_context; uses a stricter system prompt.
"""

import os
from dotenv import load_dotenv
from typing import Optional

load_dotenv()

_SYSTEM_PROMPT = """You are ChhayaRakshak (meaning "Shade Protector" in Hindi), an AI assistant
specialising in urban heat protection, heat safety, and climate adaptation for Indian cities.

Your role:
- Answer questions about heat safety, heatstroke prevention, and staying cool.
- Explain urban heat island effects and cooling strategies.
- Provide practical advice for residents, outdoor workers, and vulnerable groups.
- Discuss government heat action plans, early warning systems, and community resources.
- Respond in the language requested by the user (English, Hindi, or Telugu).

Guidelines:
- Keep answers concise, practical, and actionable.
- If asked about something outside heat protection and climate adaptation, politely
  redirect to your area of expertise.
- Never fabricate statistics or health advice — note uncertainty where it exists.
- For medical emergencies, always direct to emergency services (108 in India).
"""

# Stricter system prompt used exclusively by the Personal Health Assistant.
# Must not be used for the general assistant — it assumes profile context is
# always present and gives more targeted, cautious guidance.
_HEALTH_SYSTEM_PROMPT = """You are the Personal Heat-Safety Assistant within ChhayaRakshak
("Shade Protector"), an AI tool for urban heat protection in Indian cities.

You have been given a brief, anonymised summary of the user's health profile.
Use this context to personalise your heat-safety guidance.

Your role:
- Give practical, personalised heat-safety advice relevant to the user's health profile.
- Highlight precautions that are especially important for their specific conditions or
  age group (e.g. extra hydration for kidney disease, avoiding direct sun for the elderly).
- Respond in the language requested by the user (English, Hindi, or Telugu).

Strict guidelines:
- Do NOT diagnose medical conditions or recommend changes to any medication or treatment.
- Do NOT speculate about conditions beyond what is stated in the user's profile summary.
- If unsure whether advice is safe for the user's specific condition, recommend consulting
  a healthcare provider.
- For medical emergencies, always direct to emergency services (108 in India).
- Keep answers concise, practical, and actionable.
- If asked about something unrelated to heat safety or climate adaptation, politely redirect.
"""

# Supported languages: ISO code → display name for prompting
SUPPORTED_LANGUAGES = {
    "en": "English",
    "hi": "Hindi (हिन्दी)",
    "te": "Telugu (తెలుగు)",
}


class GeminiServiceError(Exception):
    """Base error from the Gemini service layer."""
    def __init__(self, message: str, status_code: int = 500):
        super().__init__(message)
        self.status_code = status_code


def _get_client():
    """Build and return a Gemini client. Raises GeminiServiceError if key is missing."""
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key or api_key == "your_gemini_api_key_here":
        raise GeminiServiceError(
            "GEMINI_API_KEY is not configured. "
            "Please add your Gemini API key to backend/.env. "
            "Get a free key at https://aistudio.google.com/app/apikey",
            status_code=503,
        )
    from google import genai
    return genai.Client(api_key=api_key)


def _handle_gemini_exception(exc: Exception) -> None:
    """Convert a raw Gemini SDK exception into a typed GeminiServiceError and re-raise."""
    err_str = str(exc).lower()
    if "quota" in err_str or "rate" in err_str or "429" in err_str:
        raise GeminiServiceError(
            "Gemini API rate limit reached. Please wait a moment and try again.",
            status_code=429,
        )
    if "api_key" in err_str or "401" in err_str or "403" in err_str:
        raise GeminiServiceError(
            "Invalid Gemini API key. Please check your GEMINI_API_KEY in backend/.env.",
            status_code=401,
        )
    if any(w in err_str for w in ("connect", "timeout", "network", "unreachable")):
        raise GeminiServiceError(
            "Could not reach the Gemini API. Please check your internet connection.",
            status_code=502,
        )
    raise GeminiServiceError(f"Gemini API error: {exc}", status_code=500)


def ask_gemini(
    question: str,
    language_code: str = "en",
    health_context: Optional[str] = None,
    conversation_history: Optional[list[dict]] = None,
) -> str:
    """
    Send a question to the general heat-safety assistant and return the text response.

    Args:
        question:               The user's latest question text.
        language_code:          One of "en", "hi", "te".
        health_context:         Optional short, curated summary of the user's health
                                profile derived server-side from allowlisted category
                                labels — never raw DB records or free-text.
                                When None, the assistant responds generically.
        conversation_history:   Optional list of prior turns for follow-up context.
                                Each item is {"role": "user"|"assistant", "text": str}.
                                At most the last 10 turns are used to keep prompts short.

    Returns:
        The model's response text.

    Raises:
        GeminiServiceError with an appropriate status_code on any failure.
    """
    lang_name = SUPPORTED_LANGUAGES.get(language_code, "English")
    client = _get_client()  # raises 503 if key missing

    # Build prior-turn context block (capped at 10 turns to control token use).
    history_block = ""
    if conversation_history:
        recent = conversation_history[-10:]
        lines = []
        for turn in recent:
            role = "User" if turn.get("role") == "user" else "Assistant"
            lines.append(f"{role}: {turn.get('text', '').strip()}")
        if lines:
            history_block = "Previous conversation:\n" + "\n".join(lines) + "\n\n"

    # Build the current-turn prompt.
    if health_context:
        prompt = (
            f"Please respond in {lang_name}.\n\n"
            f"User health context: {health_context}\n\n"
            f"{history_block}"
            f"User question: {question}\n\n"
            f"Please tailor your heat-safety advice to this user's specific "
            f"health profile where relevant. Do not diagnose medical conditions "
            f"or recommend changing any medication or treatment."
        )
    else:
        prompt = (
            f"Please respond in {lang_name}.\n\n"
            f"{history_block}"
            f"User question: {question}"
        )

    try:
        from google.genai import types
        response = client.models.generate_content(
            model="gemini-3.5-flash-lite",
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=_SYSTEM_PROMPT,
                max_output_tokens=1024,
            ),
        )
        return response.text

    except GeminiServiceError:
        raise
    except Exception as exc:
        _handle_gemini_exception(exc)


def ask_gemini_health(
    question: str,
    health_context: str,
    language_code: str = "en",
    conversation_history: Optional[list[dict]] = None,
) -> str:
    """
    Personal Health Assistant variant of ask_gemini.

    Unlike ask_gemini(), this function:
      - Requires a non-empty health_context (callers must verify consent first).
      - Uses _HEALTH_SYSTEM_PROMPT — more cautious, more personalised.
      - Does NOT fall back to generic guidance if health_context is empty;
        callers are responsible for gating this behind a valid profile.

    Args:
        question:               The user's latest question text.
        health_context:         Curated health-profile summary (must be non-empty).
        language_code:          One of "en", "hi", "te".
        conversation_history:   Optional prior turns (same format as ask_gemini).

    Returns:
        The model's response text.

    Raises:
        GeminiServiceError with an appropriate status_code on any failure.
        ValueError if health_context is empty (caller error, not a Gemini error).
    """
    if not health_context or not health_context.strip():
        raise ValueError("ask_gemini_health requires a non-empty health_context")

    lang_name = SUPPORTED_LANGUAGES.get(language_code, "English")
    client = _get_client()

    # Build prior-turn context block (capped at 10 turns).
    history_block = ""
    if conversation_history:
        recent = conversation_history[-10:]
        lines = []
        for turn in recent:
            role = "User" if turn.get("role") == "user" else "Assistant"
            lines.append(f"{role}: {turn.get('text', '').strip()}")
        if lines:
            history_block = "Previous conversation:\n" + "\n".join(lines) + "\n\n"

    prompt = (
        f"Please respond in {lang_name}.\n\n"
        f"User health profile summary: {health_context}\n\n"
        f"{history_block}"
        f"User question: {question}\n\n"
        f"Provide heat-safety guidance personalised to this profile. "
        f"Do not diagnose conditions or recommend medication changes."
    )

    try:
        from google.genai import types
        response = client.models.generate_content(
            model="gemini-3.5-flash-lite",
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=_HEALTH_SYSTEM_PROMPT,
                max_output_tokens=1024,
            ),
        )
        return response.text

    except GeminiServiceError:
        raise
    except Exception as exc:
        _handle_gemini_exception(exc)
