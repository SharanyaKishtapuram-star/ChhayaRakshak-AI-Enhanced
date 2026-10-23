import { useState, useEffect, useRef } from 'react'
import { saveHealthProfile, getHealthProfile, deleteHealthProfile, askHealthAssistant, getAssistantStatus } from '../services/api'
import MarkdownMessage from '../components/MarkdownMessage'

// ── Constants — must match backend Literal allowlists exactly ─────────────────
const AGE_GROUPS = [
  { value: 'under-18', label: 'Under 18',  desc: 'Child or teenager' },
  { value: '18-40',    label: '18 – 40',   desc: 'Young adult' },
  { value: '41-60',    label: '41 – 60',   desc: 'Middle-aged adult' },
  { value: '60+',      label: '60 +',      desc: 'Senior / elderly' },
]

const CONDITIONS = [
  { value: 'cardiovascular', label: 'Heart / Cardiovascular',  icon: '❤️',  desc: 'Heart disease, hypertension, or circulatory conditions' },
  { value: 'respiratory',    label: 'Respiratory',             icon: '🫁',  desc: 'Asthma, COPD, or other breathing difficulties' },
  { value: 'diabetes',       label: 'Diabetes',                icon: '🩸',  desc: 'Type 1 or Type 2 diabetes' },
  { value: 'kidney_disease', label: 'Kidney Disease',          icon: '🫘',  desc: 'Chronic kidney disease or renal conditions' },
  { value: 'pregnant',       label: 'Pregnant',                icon: '🤰',  desc: 'Currently pregnant' },
  { value: 'elderly',        label: 'Elderly / High Care',     icon: '👴',  desc: 'Age 60+ with additional care needs' },
  { value: 'young_child',    label: 'Caring for Young Child',  icon: '👶',  desc: 'Responsible for an infant or young child' },
  { value: 'none',           label: 'None of the above',       icon: '✅',  desc: 'No specific health conditions' },
]

const STORAGE_KEY = 'chhayarakshak_health_session_id'

// ── Small sub-components ──────────────────────────────────────────────────────

function ConsentNotice() {
  return (
    <div className="rounded-2xl border border-blue-200 bg-blue-50 p-5 text-sm text-blue-800 space-y-2">
      <p className="font-semibold text-blue-900">🔒 Privacy Notice — please read before continuing</p>
      <ul className="ml-4 list-disc space-y-1 text-xs text-blue-700 leading-relaxed">
        <li>Your health information is stored <strong>anonymously</strong> — no name, email, or device identifier is ever recorded.</li>
        <li>You are identified only by a random session ID stored in your browser's <strong>localStorage</strong>.</li>
        <li>Only broad category labels (e.g. "cardiovascular", "elderly") are stored — no clinical notes or free-text.</li>
        <li>Your health data is used <em>only</em> to personalise heat-safety advice in this app. It is never shared with third parties.</li>
        <li>You can <strong>permanently delete</strong> your profile at any time using the "Delete my profile" button.</li>
        <li>The Gemini AI receives only a short, curated natural-language summary (e.g. "elderly outdoor worker") — never raw field values.</li>
      </ul>
    </div>
  )
}

function SectionLabel({ children }) {
  return (
    <p className="text-[11px] font-semibold uppercase tracking-widest text-gray-400 mb-2">
      {children}
    </p>
  )
}

// ── Daily heat-safety checklist items (shown in the assistant panel) ──────────
const CHECKLIST_ITEMS = [
  { id: 'water',    icon: '💧', text: 'Drink at least 2–3 litres of water today, even if not thirsty.' },
  { id: 'clothes',  icon: '👕', text: 'Wear light, loose, light-coloured clothing.' },
  { id: 'sun',      icon: '☀️', text: 'Avoid going outdoors between 11 AM and 4 PM if possible.' },
  { id: 'fans',     icon: '🌬️', text: 'Use fans, damp cloths, or cool showers to lower body temperature.' },
  { id: 'food',     icon: '🥗', text: 'Eat lighter meals — heavy meals raise body temperature.' },
  { id: 'check',    icon: '👥', text: 'Check on elderly neighbours, young children, and outdoor workers.' },
]

// ── Suggested questions for the personal health assistant ─────────────────────
const HEALTH_SUGGESTED_QUESTIONS = [
  'What heat precautions are most important for my health conditions?',
  'What warning signs of heat illness should I watch for?',
  'How much water should I drink during a heatwave?',
  'Is it safe for me to exercise outdoors today?',
  'What should I keep in a personal heat emergency kit?',
]

// ── Personal Health Assistant sub-component ───────────────────────────────────
// Shown only when a saved profile is active (sessionId is non-null).
// Uses the /api/assistant/ask-health endpoint — profile-locked, stricter prompt.
function HealthAssistant({ sessionId }) {
  const [messages, setMessages]       = useState([])
  const [question, setQuestion]       = useState('')
  const [loading, setLoading]         = useState(false)
  const [apiReady, setApiReady]       = useState(null)  // null=checking, true, false
  const [history, setHistory]         = useState([])
  const [checklist, setChecklist]     = useState({})    // { id: boolean }
  const bottomRef = useRef(null)

  useEffect(() => {
    getAssistantStatus()
      .then(d => setApiReady(d.configured))
      .catch(() => setApiReady(false))
  }, [])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  async function handleSend(q) {
    const text = (q || question).trim()
    if (!text || loading || !apiReady) return
    setMessages(prev => [...prev, { role: 'user', text }])
    setQuestion('')
    setLoading(true)
    try {
      const data = await askHealthAssistant(text, sessionId, history)
      const answer = data.answer
      setMessages(prev => [...prev, { role: 'assistant', text: answer }])
      setHistory(prev => [...prev, { role: 'user', text }, { role: 'assistant', text: answer }])
    } catch (err) {
      // If profile was deleted server-side, show a clear message
      const msg = err.message?.includes('404') || err.message?.includes('not found')
        ? 'Your health profile was not found. Please re-save it above to continue.'
        : err.message || 'Something went wrong. Please try again.'
      setMessages(prev => [...prev, { role: 'error', text: msg }])
    } finally {
      setLoading(false)
    }
  }

  function handleKey(e) {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend() }
  }

  function toggleCheck(id) {
    setChecklist(prev => ({ ...prev, [id]: !prev[id] }))
  }

  return (
    <div className="mt-8 space-y-5 animate-fade-in">

      {/* Section header */}
      <div>
        <p className="section-label">Personal Heat-Safety Assistant</p>
        <h2 className="text-xl font-extrabold text-primary mb-1">🩺 Your Personal Heat-Safety Guide</h2>
        <p className="text-xs text-gray-500 leading-relaxed max-w-xl">
          Personalised heat-safety advice based on your saved profile.
          Responses use your consented health categories — never your name or raw data.
        </p>
      </div>

      {/* Daily checklist */}
      <div className="card p-5">
        <SectionLabel>Today's Heat-Safety Checklist</SectionLabel>
        <div className="space-y-2">
          {CHECKLIST_ITEMS.map(item => (
            <button
              key={item.id}
              type="button"
              onClick={() => toggleCheck(item.id)}
              className={`flex items-start gap-3 w-full text-left p-3 rounded-xl border text-sm transition-all duration-150 ${
                checklist[item.id]
                  ? 'border-emerald-200 bg-emerald-50 text-emerald-800'
                  : 'border-sage-light/40 hover:border-sage hover:bg-sage-soft bg-white text-gray-700'
              }`}
            >
              <span className="text-base flex-shrink-0 mt-0.5">{item.icon}</span>
              <span className="flex-1 leading-relaxed">{item.text}</span>
              <span className={`w-5 h-5 rounded-full border-2 flex-shrink-0 flex items-center justify-center mt-0.5 transition-all ${
                checklist[item.id] ? 'bg-emerald-500 border-emerald-500' : 'border-gray-300'
              }`}>
                {checklist[item.id] && <span className="text-white text-[10px] font-bold">✓</span>}
              </span>
            </button>
          ))}
        </div>
        {Object.values(checklist).filter(Boolean).length === CHECKLIST_ITEMS.length && (
          <p className="text-xs text-emerald-700 mt-3 flex items-center gap-1.5 font-semibold">
            <span>🎉</span> All done for today — stay safe and stay hydrated!
          </p>
        )}
      </div>

      {/* Chat panel */}
      <div className="card p-5">
        <SectionLabel>Ask Your Personal Health Assistant</SectionLabel>

        {/* API not configured */}
        {apiReady === false && (
          <div className="rounded-xl border border-amber-200 bg-amber-50 p-4 text-xs text-amber-800 mb-4">
            <strong>⚙️ Gemini API key not configured.</strong>{' '}
            Add <code className="bg-amber-100 px-1 rounded">GEMINI_API_KEY</code> to{' '}
            <code className="bg-amber-100 px-1 rounded">backend/.env</code> to enable the assistant.
          </div>
        )}

        {/* Suggested questions — shown only on empty state */}
        {messages.length === 0 && apiReady && (
          <div className="mb-4">
            <p className="text-[11px] font-semibold uppercase tracking-widest text-gray-400 mb-2">
              Suggested questions
            </p>
            <div className="flex flex-wrap gap-2">
              {HEALTH_SUGGESTED_QUESTIONS.map((q, i) => (
                <button
                  key={i}
                  type="button"
                  onClick={() => handleSend(q)}
                  disabled={loading}
                  className="text-xs px-3 py-2 rounded-xl border border-sage-light bg-white text-gray-600
                             hover:border-sage hover:text-primary hover:bg-sage-soft
                             disabled:opacity-40 disabled:cursor-not-allowed transition-colors duration-150"
                >
                  {q}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Message thread */}
        <div className="space-y-3 mb-4 min-h-[80px] max-h-[400px] overflow-y-auto">
          {messages.length === 0 && apiReady && (
            <div className="flex flex-col items-center justify-center py-8 text-gray-400">
              <div className="w-12 h-12 rounded-2xl bg-sage-soft border border-sage-light flex items-center justify-center text-2xl mb-2">
                🩺
              </div>
              <p className="text-xs text-gray-500 text-center">
                Ask me anything about heat safety for your specific health profile.
              </p>
            </div>
          )}

          {messages.map((msg, i) =>
            msg.role === 'error' ? (
              <div key={i} className="rounded-xl border border-red-200 bg-red-50 p-3 text-xs text-red-700 flex gap-2">
                <span className="flex-shrink-0">⚠️</span><span>{msg.text}</span>
              </div>
            ) : (
              <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                {msg.role === 'assistant' && (
                  <div className="w-7 h-7 rounded-xl bg-sage-soft border border-sage-light flex items-center justify-center text-sm flex-shrink-0 mr-2 mt-0.5">
                    🩺
                  </div>
                )}
                <div className={`max-w-[85%] rounded-2xl px-4 py-2.5 text-xs leading-relaxed ${
                  msg.role === 'user'
                    ? 'bg-gradient-to-br from-primary to-primary-light text-white rounded-br-md'
                    : 'bg-white border border-sage-light/50 text-gray-700 rounded-bl-md'
                }`}>
                  {msg.role === 'user'
                    ? msg.text
                    : <MarkdownMessage small>{msg.text}</MarkdownMessage>
                  }
                </div>
                {msg.role === 'user' && (
                  <div className="w-7 h-7 rounded-xl bg-accent/10 border border-accent/20 flex items-center justify-center text-sm flex-shrink-0 ml-2 mt-0.5">
                    👤
                  </div>
                )}
              </div>
            )
          )}

          {loading && (
            <div className="flex justify-start">
              <div className="w-7 h-7 rounded-xl bg-sage-soft border border-sage-light flex items-center justify-center text-sm flex-shrink-0 mr-2 mt-0.5">
                🩺
              </div>
              <div className="bg-white border border-sage-light/50 rounded-2xl rounded-bl-md px-4 py-2.5">
                <span className="flex gap-1 items-center">
                  <span className="w-1.5 h-1.5 bg-sage rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                  <span className="w-1.5 h-1.5 bg-sage rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                  <span className="w-1.5 h-1.5 bg-sage rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                </span>
              </div>
            </div>
          )}
          <div ref={bottomRef} />
        </div>

        {/* Input */}
        <div className="flex gap-2 items-end">
          <textarea
            value={question}
            onChange={e => setQuestion(e.target.value)}
            onKeyDown={handleKey}
            disabled={loading || !apiReady}
            placeholder={!apiReady ? 'Configure GEMINI_API_KEY to enable…' : 'Ask about heat safety for your profile…'}
            rows={2}
            className="flex-1 bg-white border border-sage-light/60 rounded-2xl px-4 py-2.5 text-xs resize-none
                       focus:outline-none focus:ring-2 focus:ring-sage focus:border-sage
                       disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-150"
          />
          <button
            type="button"
            onClick={() => handleSend()}
            disabled={loading || !question.trim() || !apiReady}
            className="btn-primary rounded-2xl h-[52px] w-11 flex-shrink-0 text-base"
          >
            {loading ? '…' : '➤'}
          </button>
        </div>

        {messages.length > 0 && (
          <button
            type="button"
            onClick={() => { setMessages([]); setHistory([]) }}
            className="text-xs text-gray-400 hover:text-gray-600 mt-3 mx-auto block transition-colors"
          >
            Clear conversation
          </button>
        )}

        <p className="text-[11px] text-gray-400 text-center mt-3">
          Powered by Google Gemini · Responses use your consented profile only ·
          Not a substitute for medical advice
        </p>
      </div>
    </div>
  )
}

// ── Page ──────────────────────────────────────────────────────────────────────
export default function HealthProfile() {
  // Form state
  const [ageGroup, setAgeGroup]           = useState(null)
  const [conditions, setConditions]       = useState([])
  const [outdoorWorker, setOutdoorWorker] = useState(false)
  const [consentGiven, setConsentGiven]   = useState(false)

  // App state
  const [sessionId, setSessionId]   = useState(null)   // loaded from localStorage
  const [saved, setSaved]           = useState(false)
  const [loading, setLoading]       = useState(false)
  const [deleting, setDeleting]     = useState(false)
  const [error, setError]           = useState(null)
  const [deleteConfirm, setDeleteConfirm] = useState(false)

  // On mount: check if a session_id already exists in localStorage,
  // then load the profile to pre-fill the form.
  useEffect(() => {
    const stored = localStorage.getItem(STORAGE_KEY)
    if (!stored) return

    getHealthProfile(stored)
      .then(data => {
        // Batch all state updates together after the async call resolves
        setSessionId(stored)
        setAgeGroup(data.age_group || null)
        setConditions(data.conditions || [])
        setOutdoorWorker(data.outdoor_worker || false)
        setConsentGiven(true)   // they already consented when creating
        setSaved(true)
      })
      .catch(() => {
        // Session ID in storage but profile not found (deleted server-side)
        localStorage.removeItem(STORAGE_KEY)
      })
  }, [])

  // ── Condition toggle logic ─────────────────────────────────────────────────
  function toggleCondition(value) {
    setConditions(prev => {
      if (value === 'none') {
        // Selecting "none" clears everything else
        return prev.includes('none') ? [] : ['none']
      }
      // Selecting any real condition clears "none"
      const withoutNone = prev.filter(c => c !== 'none')
      return withoutNone.includes(value)
        ? withoutNone.filter(c => c !== value)
        : [...withoutNone, value]
    })
  }

  // ── Save handler ───────────────────────────────────────────────────────────
  async function handleSave(e) {
    e.preventDefault()
    if (!consentGiven) {
      setError('You must check the consent box before saving.')
      return
    }
    setLoading(true)
    setError(null)
    try {
      const data = await saveHealthProfile({
        consent_given: true,
        age_group: ageGroup,
        conditions: conditions.length > 0 ? conditions : null,
        outdoor_worker: outdoorWorker,
      })
      localStorage.setItem(STORAGE_KEY, data.session_id)
      setSessionId(data.session_id)
      setSaved(true)
    } catch (err) {
      setError(err.message || 'Could not save profile. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  // ── Delete handler ─────────────────────────────────────────────────────────
  async function handleDelete() {
    if (!sessionId) return
    setDeleting(true)
    setError(null)
    try {
      await deleteHealthProfile(sessionId)
      localStorage.removeItem(STORAGE_KEY)
      // Reset all state
      setSessionId(null)
      setSaved(false)
      setAgeGroup(null)
      setConditions([])
      setOutdoorWorker(false)
      setConsentGiven(false)
      setDeleteConfirm(false)
    } catch (err) {
      setError(err.message || 'Could not delete profile. Please try again.')
    } finally {
      setDeleting(false)
    }
  }

  // ── Derived ────────────────────────────────────────────────────────────────
  const canSave = consentGiven && !loading

  return (
    <div className="page-wrapper animate-fade-in">

      {/* Header */}
      <div className="mb-8">
        <p className="section-label">Personal Health Integration</p>
        <h1 className="text-3xl font-extrabold text-primary mb-2">🏥 Personal Health Profile</h1>
        <p className="text-gray-500 text-sm leading-relaxed max-w-xl">
          Provide optional health information to receive personalised heat-safety guidance.
          All data is stored anonymously — no account required.
        </p>
      </div>

      {/* Active profile banner */}
      {saved && sessionId && (
        <div className="mb-6 rounded-2xl border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-800 flex items-start gap-3 animate-slide-up">
          <span className="text-xl flex-shrink-0">✅</span>
          <div>
            <p className="font-semibold">Health profile active</p>
            <p className="text-xs text-emerald-700 mt-0.5">
              Your profile is saved and will personalise heat-safety advice in the AI Assistant.
            </p>
            <p className="text-xs text-emerald-600 mt-1 font-mono break-all">
              Session ID: {sessionId}
            </p>
          </div>
        </div>
      )}

      <form onSubmit={handleSave} className="space-y-6">

        {/* Privacy notice */}
        <ConsentNotice />

        {/* Age group */}
        <div className="card p-5">
          <SectionLabel>Age Group <span className="normal-case text-gray-300 font-normal tracking-normal">(optional)</span></SectionLabel>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
            {AGE_GROUPS.map(({ value, label, desc }) => (
              <button
                key={value}
                type="button"
                onClick={() => setAgeGroup(prev => prev === value ? null : value)}
                title={desc}
                className={`p-3 text-xs rounded-xl border text-left transition-all duration-150 ${
                  ageGroup === value
                    ? 'bg-primary text-white border-primary shadow-card-md'
                    : 'border-sage-light/60 hover:border-sage hover:bg-sage-soft bg-white text-gray-700'
                }`}
              >
                <span className="font-semibold block">{label}</span>
                <span className={`block mt-0.5 ${ageGroup === value ? 'text-sage-light' : 'text-gray-400'}`}>{desc}</span>
              </button>
            ))}
          </div>
        </div>

        {/* Health conditions */}
        <div className="card p-5">
          <SectionLabel>Health Conditions <span className="normal-case text-gray-300 font-normal tracking-normal">(select all that apply — optional)</span></SectionLabel>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
            {CONDITIONS.map(({ value, label, icon, desc }) => {
              const isSelected = conditions.includes(value)
              const isDisabled = value !== 'none' && conditions.includes('none')
              return (
                <button
                  key={value}
                  type="button"
                  onClick={() => toggleCondition(value)}
                  disabled={isDisabled}
                  title={desc}
                  className={`flex items-center gap-3 p-3 rounded-xl border text-left text-sm transition-all duration-150 ${
                    isSelected
                      ? 'border-primary/40 bg-sage-soft shadow-card'
                      : isDisabled
                        ? 'border-gray-100 bg-gray-50 opacity-40 cursor-not-allowed'
                        : 'border-sage-light/40 hover:border-sage hover:bg-sage-soft bg-white'
                  }`}
                >
                  <span className="text-xl flex-shrink-0">{icon}</span>
                  <div className="min-w-0">
                    <span className={`font-medium block ${isSelected ? 'text-primary' : 'text-gray-700'}`}>{label}</span>
                    <span className="text-xs text-gray-400 block truncate">{desc}</span>
                  </div>
                  <div className={`ml-auto w-5 h-5 rounded-full border-2 flex-shrink-0 flex items-center justify-center transition-all ${
                    isSelected ? 'bg-primary border-primary' : 'border-gray-300'
                  }`}>
                    {isSelected && <span className="text-white text-[10px] font-bold">✓</span>}
                  </div>
                </button>
              )
            })}
          </div>
        </div>

        {/* Outdoor worker */}
        <div className="card p-5">
          <SectionLabel>Work Environment</SectionLabel>
          <button
            type="button"
            onClick={() => setOutdoorWorker(prev => !prev)}
            className={`flex items-center gap-4 w-full p-4 rounded-xl border text-left transition-all duration-150 ${
              outdoorWorker
                ? 'border-accent/40 bg-accent-soft shadow-card'
                : 'border-sage-light/40 hover:border-sage hover:bg-sage-soft bg-white'
            }`}
          >
            <span className="text-2xl flex-shrink-0">☀️</span>
            <div className="flex-1 min-w-0">
              <p className={`font-medium text-sm ${outdoorWorker ? 'text-accent' : 'text-gray-700'}`}>
                I work or spend significant time outdoors
              </p>
              <p className="text-xs text-gray-400 mt-0.5">
                Construction, agriculture, delivery, security, street vending, etc.
              </p>
            </div>
            <div className={`w-12 h-6 rounded-full flex items-center transition-all duration-200 flex-shrink-0 ${
              outdoorWorker ? 'bg-accent' : 'bg-gray-200'
            }`}>
              <div className={`w-5 h-5 rounded-full bg-white shadow mx-0.5 transition-all duration-200 ${
                outdoorWorker ? 'translate-x-6' : 'translate-x-0'
              }`} />
            </div>
          </button>
        </div>

        {/* Consent checkbox */}
        <div className="card p-5">
          <label className="flex items-start gap-3 cursor-pointer">
            <div className="relative flex-shrink-0 mt-0.5">
              <input
                type="checkbox"
                checked={consentGiven}
                onChange={e => setConsentGiven(e.target.checked)}
                className="sr-only"
              />
              <div
                className={`w-5 h-5 rounded border-2 flex items-center justify-center transition-all ${
                  consentGiven ? 'bg-primary border-primary' : 'border-gray-300 bg-white'
                }`}
              >
                {consentGiven && <span className="text-white text-[11px] font-bold leading-none">✓</span>}
              </div>
            </div>
            <span className="text-sm text-gray-700 leading-relaxed">
              <strong>I have read the privacy notice above</strong> and I consent to storing
              my anonymised health information to personalise heat-safety guidance.
              I understand I can delete my data at any time.
            </span>
          </label>
        </div>

        {/* Error */}
        {error && (
          <div className="rounded-2xl border border-red-200 bg-red-50 p-4 text-sm text-red-700 flex gap-2.5">
            <span className="flex-shrink-0">⚠️</span>
            <span>{error}</span>
          </div>
        )}

        {/* Save button */}
        <button
          type="submit"
          disabled={!canSave}
          className="btn-primary w-full text-base py-3"
        >
          {loading
            ? <><svg className="animate-spin w-4 h-4" viewBox="0 0 24 24" fill="none"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"/></svg> Saving…</>
            : saved ? '💾 Update Health Profile' : '💾 Save Health Profile'
          }
        </button>

      </form>

      {/* Personal Heat-Safety Assistant — only shown after profile is saved */}
      {saved && sessionId && (
        <HealthAssistant sessionId={sessionId} />
      )}

      {/* Delete section */}
      {sessionId && (
        <div className="mt-8 card p-5 border-red-100">
          <SectionLabel>Data Deletion</SectionLabel>
          <p className="text-sm text-gray-500 mb-4">
            Permanently delete all your stored health data. This cannot be undone.
          </p>
          {!deleteConfirm ? (
            <button
              type="button"
              onClick={() => setDeleteConfirm(true)}
              className="text-sm px-4 py-2 rounded-xl border border-red-200 text-red-600 bg-red-50 hover:bg-red-100 hover:border-red-300 transition-colors"
            >
              🗑️ Delete my health profile
            </button>
          ) : (
            <div className="rounded-xl border border-red-200 bg-red-50 p-4 space-y-3">
              <p className="text-sm font-semibold text-red-800">
                Are you sure? This will permanently erase your health profile.
              </p>
              <div className="flex gap-2">
                <button
                  type="button"
                  onClick={handleDelete}
                  disabled={deleting}
                  className="px-4 py-2 text-sm rounded-xl bg-red-600 text-white hover:bg-red-700 disabled:opacity-50 transition-colors"
                >
                  {deleting ? 'Deleting…' : 'Yes, delete permanently'}
                </button>
                <button
                  type="button"
                  onClick={() => setDeleteConfirm(false)}
                  className="px-4 py-2 text-sm rounded-xl border border-gray-200 text-gray-600 hover:bg-gray-50 transition-colors"
                >
                  Cancel
                </button>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Attribution */}
      <p className="text-[11px] text-gray-400 text-center mt-8">
        Anonymous storage only · No account required · ChhayaRakshak AI
      </p>
    </div>
  )
}
