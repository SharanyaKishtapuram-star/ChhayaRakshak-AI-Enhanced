/**
 * api.js — centralised API service layer.
 * All fetch calls to the FastAPI backend go through here.
 * The base URL is read from the Vite environment variable VITE_API_BASE_URL.
 * In development, leave VITE_API_BASE_URL empty — Vite's proxy forwards /api
 * and /health requests to http://localhost:8000 automatically.
 */

const BASE_URL = import.meta.env.VITE_API_BASE_URL || ''

// ── Phase 0 ───────────────────────────────────────────────────────────────────

/**
 * GET /health — confirms the backend is reachable.
 */
export async function checkHealth() {
  const res = await fetch(`${BASE_URL}/health`)
  if (!res.ok) throw new Error('Backend unreachable')
  return res.json()
}

// ── Phase 1: Heat Risk ────────────────────────────────────────────────────────

/**
 * GET /api/heat-risk?city=<name>
 *
 * Returns weather data, a 0–10 risk score, risk level, and safety
 * recommendations for the given Indian city.
 *
 * @param {string} city  - City name, e.g. "Hyderabad"
 * @returns {Promise<object>} - { city, weather, risk, recommendations, ... }
 * @throws {Error} with a human-readable message on failure
 */
export async function getHeatRisk(city) {
  const res = await fetch(`${BASE_URL}/api/heat-risk?city=${encodeURIComponent(city)}`)

  if (!res.ok) {
    // FastAPI returns { detail: "..." } for 4xx/5xx
    let detail = `Request failed (HTTP ${res.status})`
    try {
      const body = await res.json()
      if (body.detail) detail = body.detail
    } catch (_) { /* ignore JSON parse errors */ }
    throw new Error(detail)
  }

  return res.json()
}

// ── Phase 4: Shade Detection ──────────────────────────────────────────────────

/**
 * POST /api/shade/analyze
 *
 * Uploads an image file and returns OpenCV analysis results:
 * shade %, green cover %, sky %, infrastructure score, level,
 * interpretation, and recommendations.
 *
 * @param {File} file - A File object from an <input type="file"> element
 * @returns {Promise<object>} - Full analysis result
 * @throws {Error} with a human-readable message on failure
 */
export async function analyzeShadeImage(file) {
  const formData = new FormData()
  formData.append('file', file)

  const res = await fetch(`${BASE_URL}/api/shade/analyze`, {
    method: 'POST',
    body: formData,
    // Do NOT set Content-Type — the browser sets it automatically
    // with the correct multipart boundary.
  })

  if (!res.ok) {
    let detail = `Upload failed (HTTP ${res.status})`
    try {
      const body = await res.json()
      if (body.detail) detail = body.detail
    } catch (_) { /* ignore */ }
    throw new Error(detail)
  }

  return res.json()
}

// ── Phase 3: Vulnerability Map ────────────────────────────────────────────────

/**
 * GET /api/map/cities
 * Returns live heat-risk data for ~32 Indian cities (concurrent Open-Meteo fetch).
 * Used to populate Leaflet map markers.
 */
export async function getMapCities() {
  const res = await fetch(`${BASE_URL}/api/map/cities`)
  if (!res.ok) {
    let detail = `Map data failed (HTTP ${res.status})`
    try { const b = await res.json(); if (b.detail) detail = b.detail } catch (_) {}
    throw new Error(detail)
  }
  return res.json()
}

// ── Phase 5: Budget Optimizer ─────────────────────────────────────────────────

/**
 * POST /api/budget/optimize
 * @param {number} budgetLakhs   - Budget in Indian Rupee Lakhs
 * @param {string} areaType      - residential | commercial | mixed | park
 * @param {string} city          - Optional city name for context
 */
export async function optimizeBudget(budgetLakhs, areaType, city = '') {
  const res = await fetch(`${BASE_URL}/api/budget/optimize`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ budget_lakhs: budgetLakhs, area_type: areaType, city }),
  })
  if (!res.ok) {
    let detail = `Optimization failed (HTTP ${res.status})`
    try { const b = await res.json(); if (b.detail) detail = b.detail } catch (_) {}
    throw new Error(detail)
  }
  return res.json()
}

// ── Phase 2: AI Assistant ─────────────────────────────────────────────────────

/**
 * GET /api/assistant/status
 * Check if GEMINI_API_KEY is configured on the backend.
 */
export async function getAssistantStatus() {
  const res = await fetch(`${BASE_URL}/api/assistant/status`)
  if (!res.ok) throw new Error('Could not reach the assistant status endpoint.')
  return res.json()
}

/**
 * POST /api/assistant/ask
 * @param {string}        question             - The user's question
 * @param {string}        language             - 'en' | 'hi' | 'te'
 * @param {string|null}   sessionId            - Optional health-profile session ID.
 * @param {Array|null}    conversationHistory  - Optional prior turns for follow-up
 *                                               context. Each item: { role: 'user'|'assistant', text: string }.
 *                                               At most 20 entries; server caps at 10.
 */
export async function askAssistant(question, language = 'en', sessionId = null, conversationHistory = null) {
  const body = { question, language }
  if (sessionId) body.session_id = sessionId
  if (conversationHistory && conversationHistory.length > 0)
    body.conversation_history = conversationHistory

  const res = await fetch(`${BASE_URL}/api/assistant/ask`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!res.ok) {
    let detail = `Request failed (HTTP ${res.status})`
    try { const b = await res.json(); if (b.detail) detail = b.detail } catch (_) {}
    throw new Error(detail)
  }
  return res.json()
}

/**
 * POST /api/assistant/ask-health
 * Personal Heat-Safety Assistant — requires a saved health profile.
 * Returns 404 if the profile is missing or deleted.
 *
 * @param {string}        question             - The heat-safety question
 * @param {string}        sessionId            - Health-profile session ID (required)
 * @param {Array|null}    conversationHistory  - Optional prior turns (same format as askAssistant)
 */
export async function askHealthAssistant(question, sessionId, conversationHistory = null) {
  const body = { question, session_id: sessionId }
  if (conversationHistory && conversationHistory.length > 0)
    body.conversation_history = conversationHistory

  const res = await fetch(`${BASE_URL}/api/assistant/ask-health`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!res.ok) {
    let detail = `Request failed (HTTP ${res.status})`
    try { const b = await res.json(); if (b.detail) detail = b.detail } catch (_) {}
    throw new Error(detail)
  }
  return res.json()
}

// ── Personal Health Integration ───────────────────────────────────────────────

/**
 * POST /api/health/profile
 * Create an anonymous health profile. Returns { session_id, age_group, conditions,
 * outdoor_worker, message }.
 *
 * @param {{ consent_given: boolean, age_group: string|null, conditions: string[]|null, outdoor_worker: boolean }} profile
 */
export async function saveHealthProfile(profile) {
  const res = await fetch(`${BASE_URL}/api/health/profile`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(profile),
  })
  if (!res.ok) {
    let detail = `Could not save profile (HTTP ${res.status})`
    try { const b = await res.json(); if (b.detail) detail = b.detail } catch (_) {}
    throw new Error(detail)
  }
  return res.json()
}

/**
 * GET /api/health/profile/{sessionId}
 * Retrieve an existing profile by session ID.
 *
 * @param {string} sessionId
 */
export async function getHealthProfile(sessionId) {
  const res = await fetch(`${BASE_URL}/api/health/profile/${encodeURIComponent(sessionId)}`)
  if (!res.ok) {
    let detail = `Profile not found (HTTP ${res.status})`
    try { const b = await res.json(); if (b.detail) detail = b.detail } catch (_) {}
    throw new Error(detail)
  }
  return res.json()
}

/**
 * DELETE /api/health/profile/{sessionId}
 * Permanently delete the profile for the given session ID.
 *
 * @param {string} sessionId
 */
export async function deleteHealthProfile(sessionId) {
  const res = await fetch(`${BASE_URL}/api/health/profile/${encodeURIComponent(sessionId)}`, {
    method: 'DELETE',
  })
  if (!res.ok) {
    let detail = `Could not delete profile (HTTP ${res.status})`
    try { const b = await res.json(); if (b.detail) detail = b.detail } catch (_) {}
    throw new Error(detail)
  }
  return res.json()
}


