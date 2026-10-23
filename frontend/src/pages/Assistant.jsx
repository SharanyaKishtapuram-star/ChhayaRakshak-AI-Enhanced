import { useState, useEffect, useRef } from 'react'
import { askAssistant, getAssistantStatus, getHealthProfile } from '../services/api'
import MarkdownMessage from '../components/MarkdownMessage'

const HEALTH_SESSION_KEY = 'chhayarakshak_health_session_id'

// ── Language config (codes match backend Literal["en","hi","te"]) ─────────────
// indicator_* keys carry the profile-status indicator strings for each language.
const LANGUAGES = [
  {
    code: 'en', label: 'English', flag: '🇬🇧',
    placeholder: 'Ask a heat-protection question… (Enter to send)',
    indicator_active:   'Personalised heat-safety guidance enabled.',
    indicator_active_sub: 'Responses are tailored to your saved health profile.',
    indicator_found:    'Health profile found. Send a question to activate personalised guidance.',
    indicator_none:     'General heat-safety guidance.',
    indicator_none_link: 'Save a health profile',
    indicator_none_suffix: ' to receive personalised advice.',
  },
  {
    code: 'hi', label: 'हिन्दी', flag: '🇮🇳',
    placeholder: 'अपना प्रश्न यहाँ लिखें…',
    indicator_active:   'व्यक्तिगत ताप-सुरक्षा मार्गदर्शन सक्रिय है।',
    indicator_active_sub: 'उत्तर आपकी सहेजी गई स्वास्थ्य प्रोफ़ाइल के अनुसार अनुकूलित हैं।',
    indicator_found:    'स्वास्थ्य प्रोफ़ाइल मिली। व्यक्तिगत मार्गदर्शन के लिए प्रश्न भेजें।',
    indicator_none:     'सामान्य ताप-सुरक्षा मार्गदर्शन।',
    indicator_none_link: 'स्वास्थ्य प्रोफ़ाइल सहेजें',
    indicator_none_suffix: ' व्यक्तिगत सलाह के लिए।',
  },
  {
    code: 'te', label: 'తెలుగు', flag: '🌟',
    placeholder: 'మీ ప్రశ్న ఇక్కడ టైప్ చేయండి…',
    indicator_active:   'వ్యక్తిగత వేడి-భద్రత మార్గదర్శకత్వం సక్రియంగా ఉంది.',
    indicator_active_sub: 'సమాధానాలు మీ ఆరోగ్య ప్రొఫైల్‌కు అనుగుణంగా అందించబడతాయి.',
    indicator_found:    'ఆరోగ్య ప్రొఫైల్ కనుగొనబడింది. వ్యక్తిగత మార్గదర్శకత్వానికి ప్రశ్న పంపండి.',
    indicator_none:     'సాధారణ వేడి-భద్రత మార్గదర్శకత్వం.',
    indicator_none_link: 'ఆరోగ్య ప్రొఫైల్ సేవ్ చేయండి',
    indicator_none_suffix: ' వ్యక్తిగత సలహా కోసం.',
  },
]

// ── Sample questions ──────────────────────────────────────────────────────────
// Includes data-aware questions about app features (heat risk, shade, budget, map).
// These are shown on the empty state — the user can tap to send instantly.
const SAMPLE_QUESTIONS = {
  en: [
    'What should I do if someone has heatstroke?',
    'How can I keep my house cool without AC?',
    'Explain what a heat-risk score means.',
    'How can my area become cooler?',
    'Explain budget recommendations for cooling interventions.',
    'Who is most vulnerable to heat illness?',
  ],
  hi: [
    'लू लगने पर क्या करें?',
    'बिना AC के घर को ठंडा कैसे रखें?',
    'हीट वेव में पानी कितना पीना चाहिए?',
    'हीट रिस्क स्कोर का क्या मतलब है?',
  ],
  te: [
    'వేసవి వేడిలో ఎలా సురక్షితంగా ఉండాలి?',
    'హీట్‌స్ట్రోక్ లక్షణాలు ఏమిటి?',
    'నా ప్రాంతాన్ని చల్లగా చేయడానికి ఏమి చేయాలి?',
    'హీట్ రిస్క్ స్కోర్ అంటే ఏమిటి?',
  ],
}

// ── Chat bubble ───────────────────────────────────────────────────────────────
function ChatBubble({ role, text, lang }) {
  const isUser = role === 'user'
  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'} animate-slide-up`}>
      {!isUser && (
        <div className="w-8 h-8 rounded-xl bg-sage-soft border border-sage-light flex items-center justify-center text-base flex-shrink-0 mr-2 mt-0.5">
          🤖
        </div>
      )}
      <div
        className={`max-w-[82%] rounded-2xl px-4 py-3 text-sm leading-relaxed
          ${isUser
            ? 'bg-gradient-to-br from-primary to-primary-light text-white rounded-br-md shadow-card-md'
            : 'bg-white border border-sage-light/50 text-gray-700 rounded-bl-md shadow-card'
          }`}
        lang={lang}
      >
        {isUser ? text : <MarkdownMessage>{text}</MarkdownMessage>}
      </div>
      {isUser && (
        <div className="w-8 h-8 rounded-xl bg-accent/10 border border-accent/20 flex items-center justify-center text-base flex-shrink-0 ml-2 mt-0.5">
          👤
        </div>
      )}
    </div>
  )
}

// ── Page ──────────────────────────────────────────────────────────────────────
export default function Assistant() {
  const [language, setLanguage]   = useState('en')
  const [question, setQuestion]   = useState('')
  const [messages, setMessages]   = useState([])
  const [loading, setLoading]     = useState(false)
  const [apiStatus, setApiStatus] = useState(null)
  // Verified health session ID: set only after a successful GET /api/health/profile.
  // null means "no profile" or "profile deleted/invalid".
  const [healthSessionId, setHealthSessionId] = useState(null)
  // True once the backend confirms a real profile was used for the last reply.
  const [profileActive, setProfileActive] = useState(false)
  // Conversation history: array of { role, text } sent with each request for follow-ups.
  // Cleared when the user clicks "Clear conversation".
  const [conversationHistory, setConversationHistory] = useState([])
  const bottomRef = useRef(null)

  // ── Validate a session ID against the backend and update state ──────────────
  // Returns the validated session ID string if valid, or null if not.
  // Side-effects: updates healthSessionId & clears stale localStorage.
  // Never throws — all errors are swallowed into a graceful fallback.
  async function resolveSessionId(sid) {
    if (!sid) return null
    try {
      await getHealthProfile(sid)   // throws on 404 / network error
      setHealthSessionId(sid)
      return sid
    } catch (_) {
      // Profile deleted, invalid, or unreachable — clear stale localStorage.
      localStorage.removeItem(HEALTH_SESSION_KEY)
      setHealthSessionId(null)
      setProfileActive(false)
      return null
    }
  }

  // ── On mount: check API key and verify the stored session ID ─────────────────
  useEffect(() => {
    getAssistantStatus()
      .then(data => setApiStatus(data))
      .catch(() => setApiStatus({ configured: false, message: 'Could not reach the backend.' }))

    // Validate the stored session ID immediately on page load / refresh.
    // This fixes Limitation 1: the indicator is shown as soon as the profile
    // is confirmed valid, not only after the first question.
    const stored = localStorage.getItem(HEALTH_SESSION_KEY)
    if (stored) resolveSessionId(stored)
  }, [])   // eslint-disable-line react-hooks/exhaustive-deps

  // ── Cross-tab sync: listen for storage events from other tabs ────────────────
  // Fixes Limitation 2: if the user saves or deletes their profile in another
  // tab, the storage event fires here and we re-validate immediately.
  useEffect(() => {
    function handleStorageChange(e) {
      if (e.key !== HEALTH_SESSION_KEY) return
      if (e.newValue) {
        // Profile saved or updated in another tab — validate the new ID.
        resolveSessionId(e.newValue)
      } else {
        // Profile deleted in another tab.
        setHealthSessionId(null)
        setProfileActive(false)
      }
    }
    window.addEventListener('storage', handleStorageChange)
    return () => window.removeEventListener('storage', handleStorageChange)
  }, [])   // eslint-disable-line react-hooks/exhaustive-deps

  // Scroll to bottom on new messages
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  async function handleSend(q) {
    const text = (q || question).trim()
    if (!text || loading) return

    // Add the user message to displayed messages immediately.
    setMessages(prev => [...prev, { role: 'user', text, lang: language }])
    setQuestion('')
    setLoading(true)

    try {
      // Re-read localStorage on every send to pick up in-tab updates.
      // Then validate against the backend so we never use a stale session ID.
      const latestStored = localStorage.getItem(HEALTH_SESSION_KEY)
      const validSid = await resolveSessionId(latestStored)

      const data = await askAssistant(text, language, validSid, conversationHistory)

      // Update the profile-active indicator based on what the backend confirms.
      setProfileActive(!!data.profile_active)

      const assistantText = data.answer
      setMessages(prev => [...prev, { role: 'assistant', text: assistantText, lang: language }])

      // Append both turns to conversation history for follow-up context.
      setConversationHistory(prev => [
        ...prev,
        { role: 'user', text },
        { role: 'assistant', text: assistantText },
      ])
    } catch (err) {
      setMessages(prev => [...prev, {
        role: 'error',
        text: err.message || 'Something went wrong. Please try again.',
        lang: 'en',
      }])
    } finally {
      setLoading(false)
    }
  }

  function handleKeyDown(e) {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend() }
  }

  const configured = apiStatus?.configured
  const activeLang = LANGUAGES.find(l => l.code === language) || LANGUAGES[0]

  return (
    <div className="max-w-2xl mx-auto px-4 sm:px-6 py-10 flex flex-col animate-fade-in"
      style={{ minHeight: 'calc(100vh - 64px)' }}>

      {/* Header */}
      <div className="mb-6">
        <p className="section-label">Feature 5</p>
        <h1 className="text-3xl font-extrabold text-primary mb-2">🤖 Multilingual AI Heat Assistant</h1>
        <p className="text-gray-500 text-sm">
          Ask heat-protection questions in English, Hindi, or Telugu.
          Powered by Google Gemini — responds in your chosen language.
        </p>
      </div>

      {/* Health profile status indicator — text uses the active language (Limitation 3) */}
      {healthSessionId ? (
        <div className={`mb-4 rounded-xl border px-4 py-2.5 text-xs flex items-center gap-2 animate-fade-in ${
          profileActive
            ? 'border-emerald-200 bg-emerald-50 text-emerald-800'
            : 'border-sage-light/40 bg-sage-soft/50 text-gray-500'
        }`}>
          <span className="flex-shrink-0">{profileActive ? '✅' : '👤'}</span>
          <span>
            {profileActive
              ? <><strong>{activeLang.indicator_active}</strong> {activeLang.indicator_active_sub}</>
              : activeLang.indicator_found
            }
          </span>
        </div>
      ) : (
        <div className="mb-4 rounded-xl border border-sage-light/30 bg-sage-soft/30 px-4 py-2.5 text-xs flex items-center gap-2 text-gray-400">
          <span className="flex-shrink-0">ℹ️</span>
          <span>
            {activeLang.indicator_none}{' '}
            <a href="/health-profile" className="underline text-primary hover:text-primary-light">
              {activeLang.indicator_none_link}
            </a>
            {activeLang.indicator_none_suffix}
          </span>
        </div>
      )}

      {/* Setup banner when key is missing */}
      {apiStatus && !configured && (
        <div className="mb-5 rounded-2xl border border-amber-200 bg-amber-50 p-5 text-sm text-amber-800 animate-slide-up">
          <p className="font-semibold mb-2">⚙️ Setup required</p>
          <p className="text-xs mb-3 text-amber-700">{apiStatus.message}</p>
          <ol className="ml-4 list-decimal space-y-1.5 text-xs text-amber-700">
            <li>Get a <strong>free</strong> Gemini API key at{' '}
              <a href="https://aistudio.google.com/app/apikey" target="_blank" rel="noreferrer" className="underline font-medium">
                aistudio.google.com
              </a>
            </li>
            <li>Create <code className="bg-amber-100 px-1.5 py-0.5 rounded font-mono text-[11px]">backend/.env</code> with:{' '}
              <code className="bg-amber-100 px-1.5 py-0.5 rounded font-mono text-[11px]">GEMINI_API_KEY=your_key</code>
            </li>
            <li>Restart the backend server</li>
          </ol>
        </div>
      )}

      {/* Language switcher */}
      <div className="flex gap-2 mb-5">
        {LANGUAGES.map(({ code, label, flag }) => (
          <button
            key={code}
            onClick={() => setLanguage(code)}
            className={`flex items-center gap-1.5 px-4 py-2 rounded-xl text-sm font-medium border transition-all duration-150 ${
              language === code
                ? 'bg-primary text-white border-primary shadow-card'
                : 'border-sage-light text-gray-600 hover:border-sage hover:bg-sage-soft bg-white'
            }`}
          >
            <span>{flag}</span>
            <span>{label}</span>
          </button>
        ))}
      </div>

      {/* Sample question chips */}
      {messages.length === 0 && (
        <div className="mb-5 animate-fade-in">
          <p className="text-[11px] font-semibold uppercase tracking-widest text-gray-400 mb-2">Suggested questions</p>
          <div className="flex flex-wrap gap-2">
            {(SAMPLE_QUESTIONS[language] || SAMPLE_QUESTIONS.en).map((q, i) => (
              <button
                key={i}
                onClick={() => handleSend(q)}
                disabled={loading || !configured}
                className="text-xs px-3 py-2 rounded-xl border border-sage-light bg-white text-gray-600
                           hover:border-sage hover:text-primary hover:bg-sage-soft
                           disabled:opacity-40 disabled:cursor-not-allowed
                           transition-colors duration-150"
              >
                {q}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Message thread */}
      <div className="flex-1 space-y-3 mb-4 min-h-[200px]">
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center py-12 text-gray-400">
            <div className="w-14 h-14 rounded-2xl bg-sage-soft border border-sage-light flex items-center justify-center text-3xl mb-3">
              {activeLang.flag}
            </div>
            <p className="text-sm font-medium text-gray-500">
              {configured
                ? `Ask me anything about heat protection in ${activeLang.label}.`
                : 'Configure your Gemini API key above to start chatting.'
              }
            </p>
          </div>
        )}

        {messages.map((msg, i) => (
          msg.role === 'error'
            ? (
              <div key={i} className="rounded-2xl border border-red-200 bg-red-50 p-3.5 text-sm text-red-700 flex gap-2.5">
                <span className="flex-shrink-0">⚠️</span><span>{msg.text}</span>
              </div>
            )
            : <ChatBubble key={i} role={msg.role} text={msg.text} lang={msg.lang} />
        ))}

        {/* Typing indicator */}
        {loading && (
          <div className="flex justify-start">
            <div className="w-8 h-8 rounded-xl bg-sage-soft border border-sage-light flex items-center justify-center text-base flex-shrink-0 mr-2 mt-0.5">
              🤖
            </div>
            <div className="bg-white border border-sage-light/50 rounded-2xl rounded-bl-md px-4 py-3 shadow-card">
              <span className="flex gap-1 items-center">
                <span className="w-2 h-2 bg-sage rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                <span className="w-2 h-2 bg-sage rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                <span className="w-2 h-2 bg-sage rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
              </span>
            </div>
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      {/* Input area */}
      <div className="flex gap-2 items-end">
        <textarea
          value={question}
          onChange={e => setQuestion(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={loading || !configured}
          placeholder={!configured ? 'Configure GEMINI_API_KEY to enable…' : activeLang.placeholder}
          rows={2}
          className="flex-1 bg-white border border-sage-light/60 rounded-2xl px-4 py-3 text-sm resize-none
                     focus:outline-none focus:ring-2 focus:ring-sage focus:border-sage
                     disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-150"
        />
        <button
          onClick={() => handleSend()}
          disabled={loading || !question.trim() || !configured}
          className="btn-primary rounded-2xl h-[60px] w-12 flex-shrink-0 text-lg"
        >
          {loading ? '…' : '➤'}
        </button>
      </div>

      {messages.length > 0 && (
        <button
          onClick={() => { setMessages([]); setConversationHistory([]) }}
          className="text-xs text-gray-400 hover:text-gray-600 mt-3 mx-auto transition-colors"
        >
          Clear conversation
        </button>
      )}

      {/* Attribution */}
      <p className="text-[11px] text-gray-400 text-center mt-4">
        Powered by Google Gemini 3.5 Flash Lite · ChhayaRakshak AI
      </p>
    </div>
  )
}
