import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { checkHealth } from '../services/api'

// ── Feature card data (routes + API calls are unchanged) ─────────────────────
const features = [
  {
    to: '/heat-risk',
    icon: '🌡️',
    title: 'Heat Exposure Risk',
    desc: 'Real-time risk scoring (0–10) for any Indian city using live Open-Meteo weather data.',
    tag: 'Live Data',
    color: 'from-orange-50 to-red-50',
    border: 'border-orange-200',
    tagColor: 'bg-orange-100 text-orange-700 border-orange-200',
  },
  {
    to: '/shade',
    icon: '🌿',
    title: 'Shade Detection',
    desc: 'Upload a street photo — OpenCV analyses shade, green cover, and sky exposure instantly.',
    tag: 'Computer Vision',
    color: 'from-emerald-50 to-teal-50',
    border: 'border-emerald-200',
    tagColor: 'bg-emerald-100 text-emerald-700 border-emerald-200',
  },
  {
    to: '/map',
    icon: '🗺️',
    title: 'Vulnerability Map',
    desc: 'Interactive Leaflet map with live heat-risk colour markers for 32 Indian cities.',
    tag: 'Interactive Map',
    color: 'from-sky-50 to-indigo-50',
    border: 'border-sky-200',
    tagColor: 'bg-sky-100 text-sky-700 border-sky-200',
  },
  {
    to: '/budget',
    icon: '💰',
    title: 'Budget Optimizer',
    desc: 'Greedy algorithm selects the highest-impact cooling interventions within your budget.',
    tag: 'Local Algorithm',
    color: 'from-violet-50 to-purple-50',
    border: 'border-violet-200',
    tagColor: 'bg-violet-100 text-violet-700 border-violet-200',
  },
  {
    to: '/assistant',
    icon: '🤖',
    title: 'AI Heat Assistant',
    desc: 'Ask heat-safety questions in English, Hindi, or Telugu — powered by Google Gemini.',
    tag: 'Multilingual AI',
    color: 'from-amber-50 to-yellow-50',
    border: 'border-amber-200',
    tagColor: 'bg-amber-100 text-amber-700 border-amber-200',
  },
]

// ── Stats strip ───────────────────────────────────────────────────────────────
const stats = [
  { value: '32+',  label: 'Indian cities monitored' },
  { value: '0–10', label: 'Precise risk scoring' },
  { value: '3',    label: 'Languages supported' },
  { value: '100%', label: 'Free to use' },
]

// ── Tech badges ───────────────────────────────────────────────────────────────
const techStack = [
  'React + Vite', 'FastAPI', 'OpenCV', 'Google Gemini', 'Open-Meteo', 'Leaflet OSM',
]

export default function Home() {
  const [apiStatus, setApiStatus] = useState('checking')

  useEffect(() => {
    checkHealth()
      .then(() => setApiStatus('online'))
      .catch(() => setApiStatus('offline'))
  }, [])

  return (
    <div>

      {/* ── Hero ─────────────────────────────────────────────────────────── */}
      <section className="bg-hero-gradient relative overflow-hidden">
        {/* Decorative circles */}
        <div className="absolute inset-0 overflow-hidden pointer-events-none">
          <div className="absolute -top-24 -right-24 w-96 h-96 rounded-full bg-sage/10 blur-3xl" />
          <div className="absolute -bottom-16 -left-16 w-72 h-72 rounded-full bg-accent/10 blur-3xl" />
          <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] rounded-full bg-primary-light/20 blur-3xl" />
        </div>

        <div className="relative max-w-5xl mx-auto px-4 sm:px-6 py-20 text-center">
          {/* API status badge */}
          <div className="flex justify-center mb-8">
            <div className={`inline-flex items-center gap-2 px-4 py-1.5 rounded-full text-xs font-semibold border backdrop-blur-sm transition-colors
              ${apiStatus === 'online'
                ? 'bg-sage/20 border-sage/40 text-sage-light'
                : apiStatus === 'offline'
                ? 'bg-red-500/20 border-red-400/40 text-red-300'
                : 'bg-white/10 border-white/20 text-white/60'
              }`}
            >
              <span className={`w-2 h-2 rounded-full flex-shrink-0 ${
                apiStatus === 'online'   ? 'bg-sage animate-pulse-slow' :
                apiStatus === 'offline'  ? 'bg-red-400 animate-pulse' : 'bg-white/40 animate-pulse'
              }`} />
              {apiStatus === 'checking' && 'Connecting to backend…'}
              {apiStatus === 'online'   && 'Backend API · Online'}
              {apiStatus === 'offline'  && 'Backend Offline — start FastAPI on port 8001'}
            </div>
          </div>

          {/* Headline */}
          <h1 className="text-5xl sm:text-6xl font-extrabold text-white leading-tight mb-5 tracking-tight">
            Beat the Heat.<br />
            <span className="text-accent-light">Protect Every Life.</span>
          </h1>
          <p className="text-sage-light text-lg sm:text-xl max-w-2xl mx-auto mb-10 leading-relaxed">
            ChhayaRakshak AI is an open-source urban heat protection system using real-time weather data,
            computer vision, and multilingual AI to keep Indian communities safe from extreme heat.
          </p>

          {/* CTA buttons */}
          <div className="flex flex-col sm:flex-row gap-3 justify-center mb-12">
            <Link to="/heat-risk"
              className="btn-accent text-base px-8 py-3 rounded-2xl shadow-lg hover:shadow-xl"
            >
              🌡️ Check Your City's Risk
            </Link>
            <Link to="/map"
              className="inline-flex items-center justify-center gap-2 bg-white/10 border border-white/20 text-white text-base font-semibold px-8 py-3 rounded-2xl hover:bg-white/20 transition-all duration-200"
            >
              🗺️ View Risk Map
            </Link>
          </div>

          {/* Tech badges */}
          <div className="flex flex-wrap justify-center gap-2">
            {techStack.map(t => (
              <span key={t} className="px-3 py-1 text-xs font-medium rounded-full bg-white/10 border border-white/15 text-white/70">
                {t}
              </span>
            ))}
          </div>
        </div>
      </section>

      {/* ── Stats strip ──────────────────────────────────────────────────── */}
      <section className="bg-cream-dark border-b border-sage-light/30">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 py-8 grid grid-cols-2 sm:grid-cols-4 gap-6">
          {stats.map(({ value, label }) => (
            <div key={label} className="text-center">
              <div className="text-3xl font-extrabold text-primary mb-1">{value}</div>
              <div className="text-xs text-gray-500 font-medium">{label}</div>
            </div>
          ))}
        </div>
      </section>

      {/* ── Feature cards ─────────────────────────────────────────────────── */}
      <section className="max-w-5xl mx-auto px-4 sm:px-6 py-14">
        <div className="text-center mb-10">
          <p className="section-label">What ChhayaRakshak can do</p>
          <h2 className="text-3xl font-bold text-primary">Six Powerful Features</h2>
          <p className="text-gray-500 mt-2 max-w-xl mx-auto text-sm">
            Every feature is live, tested, and fully functional. No sample data — all results are calculated in real time.
          </p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
          {features.map(({ to, icon, title, desc, tag, color, border, tagColor }) => (
            <Link
              key={to}
              to={to}
              className={`group relative block bg-gradient-to-br ${color} rounded-2xl border ${border} p-6
                         shadow-card hover:shadow-card-md hover:-translate-y-0.5
                         transition-all duration-200 overflow-hidden`}
            >
              {/* Decorative corner circle */}
              <div className="absolute -top-4 -right-4 w-20 h-20 rounded-full bg-white/40 group-hover:bg-white/60 transition-colors" />

              <div className="relative">
                <div className="text-4xl mb-3 animate-float" style={{ animationDelay: `${Math.random() * 0.5}s` }}>
                  {icon}
                </div>
                <div className="flex items-center justify-between gap-2 mb-2">
                  <h3 className="text-base font-bold text-primary">{title}</h3>
                  <span className={`chip ${tagColor} flex-shrink-0 text-[10px]`}>{tag}</span>
                </div>
                <p className="text-sm text-gray-600 leading-relaxed">{desc}</p>
                <div className="mt-4 flex items-center gap-1 text-xs font-semibold text-primary-light group-hover:gap-2 transition-all">
                  Open feature
                  <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
                  </svg>
                </div>
              </div>
            </Link>
          ))}
        </div>
      </section>

      {/* ── How it works ─────────────────────────────────────────────────── */}
      <section className="bg-sage-soft border-y border-sage-light/40 py-14">
        <div className="max-w-5xl mx-auto px-4 sm:px-6">
          <div className="text-center mb-10">
            <p className="section-label">Architecture</p>
            <h2 className="text-3xl font-bold text-primary">How It Works</h2>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-6 text-center">
            {[
              { step: '01', icon: '📡', title: 'Live Data Fetching', desc: 'Real-time weather from Open-Meteo API. No API key required. Geocodes 32+ Indian cities automatically.' },
              { step: '02', icon: '⚙️', title: 'Local Processing',  desc: 'OpenCV analyses images offline. Budget optimizer runs a greedy algorithm — no cloud, no latency.' },
              { step: '03', icon: '🤖', title: 'AI Insights',        desc: 'Google Gemini 3.5 provides multilingual heat-safety guidance in English, Hindi, and Telugu.' },
            ].map(({ step, icon, title, desc }) => (
              <div key={step} className="card p-6 text-center">
                <div className="w-10 h-10 rounded-xl bg-primary text-white text-xs font-bold flex items-center justify-center mx-auto mb-4">
                  {step}
                </div>
                <div className="text-3xl mb-3">{icon}</div>
                <h3 className="font-bold text-primary mb-2">{title}</h3>
                <p className="text-sm text-gray-500 leading-relaxed">{desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Footer ───────────────────────────────────────────────────────── */}
      <footer className="bg-primary-dark text-sage-light/60 text-center py-6 text-xs">
        <p className="font-medium text-sage-light/80 mb-1">ChhayaRakshak AI · Urban Heat Protection System</p>
        <p>Open-source · Free to use · Built for Indian communities</p>
      </footer>
    </div>
  )
}
