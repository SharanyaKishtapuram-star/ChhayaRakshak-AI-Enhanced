import { useState, useMemo } from 'react'
import { getHeatRisk } from '../services/api'

// ── Risk level config (colours match the original scoring thresholds) ─────────
const LEVEL_STYLES = {
  Low:      {
    badge: 'bg-emerald-100 text-emerald-800 border-emerald-300',
    bar: 'bg-risk-low', glow: 'shadow-[0_0_16px_rgba(22,163,74,0.3)]',
    bg: 'from-emerald-50 to-teal-50', border: 'border-emerald-200',
    icon: '🟢', ring: 'ring-emerald-200',
  },
  Moderate: {
    badge: 'bg-amber-100 text-amber-800 border-amber-300',
    bar: 'bg-risk-moderate', glow: 'shadow-[0_0_16px_rgba(202,138,4,0.3)]',
    bg: 'from-amber-50 to-yellow-50', border: 'border-amber-200',
    icon: '🟡', ring: 'ring-amber-200',
  },
  High:     {
    badge: 'bg-orange-100 text-orange-800 border-orange-300',
    bar: 'bg-risk-high', glow: 'shadow-[0_0_16px_rgba(234,88,12,0.3)]',
    bg: 'from-orange-50 to-red-50', border: 'border-orange-200',
    icon: '🟠', ring: 'ring-orange-200',
  },
  Extreme:  {
    badge: 'bg-red-100 text-red-800 border-red-300',
    bar: 'bg-risk-extreme', glow: 'shadow-[0_0_16px_rgba(220,38,38,0.35)]',
    bg: 'from-red-50 to-rose-50', border: 'border-red-300',
    icon: '🔴', ring: 'ring-red-200',
  },
}

const QUICK_CITIES = [
  'Hyderabad', 'Delhi', 'Mumbai', 'Chennai', 'Kolkata',
  'Bengaluru', 'Ahmedabad', 'Jaipur', 'Lucknow', 'Nagpur',
  'Warangal', 'Coimbatore', 'Patna', 'Bhopal', 'Guwahati',
  'Gangtok', 'Shillong', 'Srinagar', 'Bhubaneswar', 'Ranchi',
]

// ── Weather card ──────────────────────────────────────────────────────────────
function WeatherCard({ label, value, unit, icon, highlight }) {
  return (
    <div className={`stat-card gap-1 ${highlight ? 'ring-2 ring-accent/20 bg-accent-soft' : ''}`}>
      <span className="text-2xl mb-1">{icon}</span>
      <span className="text-2xl font-extrabold text-primary leading-none">
        {value !== undefined && value !== null ? value : '—'}
        <span className="text-sm font-medium text-gray-400 ml-0.5">{unit}</span>
      </span>
      <span className="text-[11px] text-gray-400 mt-0.5 font-medium">{label}</span>
    </div>
  )
}

// ── Gradient risk meter ────────────────────────────────────────────────────────
function RiskMeter({ score, level }) {
  const styles = LEVEL_STYLES[level] || LEVEL_STYLES.Low
  const pct = Math.min(100, (score / 10) * 100)
  return (
    <div className="w-full space-y-2">
      <div className="flex justify-between items-center text-[11px] font-medium">
        <span className="text-gray-400">Safe (0)</span>
        <span className={`font-bold text-sm ${
          level === 'Extreme' ? 'text-red-600' :
          level === 'High' ? 'text-orange-600' :
          level === 'Moderate' ? 'text-amber-600' : 'text-emerald-600'
        }`}>Score: {score}/10</span>
        <span className="text-gray-400">Extreme (10)</span>
      </div>
      {/* Gradient track */}
      <div className="relative h-5 rounded-full bg-risk-gradient overflow-hidden shadow-inner-sm">
        {/* Dark overlay from right to mask unscored region */}
        <div
          className="absolute right-0 top-0 h-full bg-white/80 rounded-r-full transition-all duration-700"
          style={{ width: `${100 - pct}%` }}
        />
        {/* Needle */}
        <div
          className="absolute top-0 h-full w-0.5 bg-primary/80 transition-all duration-700"
          style={{ left: `calc(${pct}% - 1px)` }}
        />
      </div>
      {/* Level label */}
      <div className="flex justify-start">
        <span className={`chip border text-xs font-semibold ${styles.badge} ${styles.glow}`}>
          {styles.icon} {level} Risk
        </span>
      </div>
    </div>
  )
}

// ── Score explanation ─────────────────────────────────────────────────────────
// Collapsible breakdown of the four formula components.
// Only renders when result.score_explanation is present.
function ScoreExplanation({ se }) {
  const [open, setOpen] = useState(false)
  if (!se) return null

  const rows = [
    {
      label: 'Temperature',
      detail: se.temperature_band,
      pts: se.temperature_points,
      sign: '+',
    },
    {
      label: 'Humidity modifier',
      detail: se.humidity_points === 0
        ? '< 40 % — no addition'
        : se.humidity_points === 0.5
        ? '40–60 % (+0.5)'
        : se.humidity_points === 1.5
        ? '60–75 % (+1.5)'
        : '> 75 % (+2.5)',
      pts: se.humidity_points,
      sign: '+',
    },
    {
      label: 'Wind speed',
      detail: se.wind_reduction < 0 ? '> 20 km/h (light cooling)' : '≤ 20 km/h — no reduction',
      pts: se.wind_reduction,
      sign: se.wind_reduction < 0 ? '' : '+',
    },
    {
      label: 'Heat-index bonus',
      detail: se.heat_index_bonus > 0
        ? 'Feels-like > actual + 4 °C'
        : 'Feels-like within 4 °C of actual',
      pts: se.heat_index_bonus,
      sign: '+',
    },
  ]

  return (
    <div className="rounded-2xl border border-sage-light/60 bg-white">
      <button
        onClick={() => setOpen(v => !v)}
        className="w-full flex items-center justify-between px-4 py-3 text-left"
        aria-expanded={open}
      >
        <span className="text-xs font-semibold text-gray-600 uppercase tracking-widest">
          📐 How is the risk score calculated?
        </span>
        <span className="text-gray-400 text-sm ml-3 flex-shrink-0">{open ? '▲' : '▼'}</span>
      </button>

      {open && (
        <div className="px-4 pb-4 border-t border-sage-light/40">
          <table className="w-full text-xs mt-3">
            <thead>
              <tr className="text-gray-400 text-left">
                <th className="pb-1.5 font-medium">Component</th>
                <th className="pb-1.5 font-medium">Condition</th>
                <th className="pb-1.5 font-medium text-right">Points</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {rows.map(r => (
                <tr key={r.label}>
                  <td className="py-1.5 text-gray-700 font-medium pr-3">{r.label}</td>
                  <td className="py-1.5 text-gray-500 pr-3">{r.detail}</td>
                  <td className={`py-1.5 text-right font-bold tabular-nums ${
                    r.pts < 0 ? 'text-emerald-600' :
                    r.pts > 0 ? 'text-red-600' : 'text-gray-400'
                  }`}>
                    {r.pts < 0 ? '' : r.sign}{r.pts.toFixed(1)}
                  </td>
                </tr>
              ))}
              <tr className="border-t-2 border-gray-200">
                <td className="pt-2 text-gray-700 font-bold" colSpan={2}>Total (clamped 0–10)</td>
                <td className="pt-2 text-right font-extrabold text-primary tabular-nums">
                  {se.total}/10
                </td>
              </tr>
            </tbody>
          </table>
          <p className="text-[11px] text-gray-400 mt-3 leading-snug">
            ⚠️ {se.note}
          </p>
        </div>
      )}
    </div>
  )
}

// ── Hourly heat forecast ──────────────────────────────────────────────────────
// Shows temperature and feels-like for up to 12 upcoming hours.
// Only renders when forecast is a non-empty array.

// Quick temperature-band colour dot (client-side, indicative only).
function _tempDot(temp) {
  if (temp < 27) return 'bg-emerald-400'
  if (temp < 32) return 'bg-yellow-400'
  if (temp < 37) return 'bg-orange-400'
  if (temp < 42) return 'bg-red-500'
  return 'bg-red-700'
}

// Format an ISO datetime string ("2024-05-01T14:00") to "2:00 PM".
function _fmtTime(iso) {
  try {
    const d = new Date(iso)
    return d.toLocaleTimeString('en-IN', { hour: 'numeric', minute: '2-digit', hour12: true })
  } catch {
    return iso
  }
}

function HourlyForecast({ forecast }) {
  if (!forecast || forecast.length === 0) return null

  // Filter to upcoming hours only (ISO strings compare lexicographically within the same day).
  const nowISO = new Date().toISOString().slice(0, 16)  // "2024-05-01T14:30" format
  const upcoming = forecast
    .filter(h => h.time >= nowISO)
    .slice(0, 12)  // show at most 12 hours ahead

  // If everything is in the past (edge case: late-night fetch), show the last 12 entries.
  const rows = upcoming.length > 0 ? upcoming : forecast.slice(-12)

  return (
    <div>
      <p className="section-label">Hourly Heat Forecast</p>
      <div className="card p-0 overflow-hidden">
        {/* Disclaimer */}
        <div className="px-4 py-2.5 bg-gray-50 border-b border-gray-100 text-[11px] text-gray-400">
          ℹ️ Forecast values are model estimates from Open-Meteo, not live observations.
          The colour dot reflects temperature band only — it does not account for humidity or wind.
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-xs min-w-[340px]">
            <thead>
              <tr className="text-gray-400 text-left border-b border-gray-100">
                <th className="px-4 py-2.5 font-medium">Time (IST)</th>
                <th className="px-4 py-2.5 font-medium">Temperature</th>
                <th className="px-4 py-2.5 font-medium">Feels Like</th>
                <th className="px-4 py-2.5 font-medium sr-only">Level</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {rows.map((h, i) => (
                <tr key={h.time} className={i % 2 === 0 ? 'bg-white' : 'bg-gray-50/50'}>
                  <td className="px-4 py-2 font-medium text-gray-700 whitespace-nowrap">
                    {_fmtTime(h.time)}
                  </td>
                  <td className="px-4 py-2 font-bold text-primary tabular-nums">
                    {h.temperature?.toFixed(1)} °C
                  </td>
                  <td className="px-4 py-2 text-gray-600 tabular-nums">
                    {h.apparent_temperature?.toFixed(1)} °C
                  </td>
                  <td className="px-4 py-2">
                    <span
                      className={`inline-block w-2.5 h-2.5 rounded-full ${_tempDot(h.temperature)}`}
                      title={`Temperature band indicator`}
                    />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}

// ── Safer-time guidance ───────────────────────────────────────────────────────
// Identifies the relatively coolest forecast hours using a transparent comparison.
// Explicitly avoids calling any period "safe."
// Only renders alongside a non-empty forecast.

function SaferTimeGuidance({ forecast }) {
  if (!forecast || forecast.length === 0) return null

  // Use the same upcoming-hours logic as HourlyForecast.
  const nowISO = new Date().toISOString().slice(0, 16)
  const upcoming = forecast
    .filter(h => h.time >= nowISO)
    .slice(0, 12)
  const rows = upcoming.length > 0 ? upcoming : forecast.slice(-12)

  if (rows.length === 0) return null

  // Find the minimum temperature in the window.
  const minTemp = Math.min(...rows.map(h => h.temperature))
  // Coolest hours: within 1 °C of the minimum (may be several).
  const coolest = rows.filter(h => h.temperature <= minTemp + 1.0)

  // Current-hour temperature for comparison context.
  const currentTemp = rows[0]?.temperature

  return (
    <div>
      <p className="section-label">Safer-Time Guidance</p>
      <div className="card p-4 space-y-3">
        <p className="text-sm text-gray-700 leading-relaxed">
          Based on the next {rows.length} forecast hours, the{' '}
          <strong>relatively coolest period{coolest.length > 1 ? 's' : ''}</strong>
          {' '}in this window {coolest.length > 1 ? 'are' : 'is'}{' '}
          <span className="font-semibold text-primary">
            {coolest.map(h => _fmtTime(h.time)).join(', ')}
          </span>
          {' '}(forecast temperature: <span className="font-semibold">{minTemp.toFixed(1)} °C</span>
          {currentTemp !== undefined && currentTemp > minTemp
            ? `, compared to ${currentTemp.toFixed(1)} °C now`
            : ''}
          ).
        </p>

        <div className="rounded-xl bg-amber-50 border border-amber-200 px-3 py-2.5 text-xs text-amber-800 leading-snug">
          <span className="font-semibold">Important: </span>
          No outdoor period should be considered completely safe during High or Extreme
          heat conditions. These are relatively cooler times within today's forecast window,
          not safe windows. Continue to follow all safety recommendations regardless of
          the time of day.
        </div>
      </div>
    </div>
  )
}

// ── Page ──────────────────────────────────────────────────────────────────────
export default function HeatRisk() {
  const [city, setCity]       = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError]     = useState(null)
  const [result, setResult]   = useState(null)

  async function handleAnalyse(cityName) {
    const target = (cityName || city).trim()
    if (!target) return
    setCity(target)
    setLoading(true)
    setError(null)
    setResult(null)
    try {
      const data = await getHeatRisk(target)
      setResult(data)
    } catch (err) {
      setError(err.message || 'Something went wrong. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  function handleSubmit(e) { e.preventDefault(); handleAnalyse() }

  const level  = result?.risk?.level
  const styles = level ? LEVEL_STYLES[level] : null

  return (
    <div className="page-wrapper animate-fade-in">

      {/* Page header */}
      <div className="mb-8">
        <p className="section-label">Feature 1</p>
        <h1 className="text-3xl font-extrabold text-primary mb-2">🌡️ Heat Exposure Risk Analysis</h1>
        <p className="text-gray-500 text-sm leading-relaxed max-w-xl">
          Enter any Indian city to get live temperature, humidity, wind speed, a risk score (0–10),
          and personalised heat-safety recommendations from Open-Meteo.
        </p>
      </div>

      {/* Search form */}
      <form onSubmit={handleSubmit} className="flex gap-2 mb-4">
        <input
          type="text"
          value={city}
          onChange={e => setCity(e.target.value)}
          placeholder="e.g. Hyderabad, Delhi, Chennai…"
          className="input-field flex-1"
        />
        <button
          type="submit"
          disabled={loading || !city.trim()}
          className="btn-primary flex-shrink-0"
        >
          {loading
            ? <><svg className="animate-spin w-4 h-4" viewBox="0 0 24 24" fill="none"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"/></svg> Analysing…</>
            : 'Analyse'
          }
        </button>
      </form>

      {/* Quick-select city chips */}
      <div className="flex flex-wrap gap-1.5 mb-8">
        {QUICK_CITIES.map(c => (
          <button
            key={c}
            onClick={() => handleAnalyse(c)}
            disabled={loading}
            className="chip border-sage-light/60 bg-white text-gray-600 hover:border-sage hover:text-primary hover:bg-sage-soft disabled:opacity-40 disabled:cursor-not-allowed"
          >
            {c}
          </button>
        ))}
      </div>

      {/* Error */}
      {error && !loading && (() => {
        const isStateGuidance = error.includes('is a state') || error.includes('specific city')
        return (
          <div className={`rounded-2xl border p-4 text-sm mb-6 animate-slide-up ${
            isStateGuidance
              ? 'border-amber-200 bg-amber-50 text-amber-800'
              : 'border-red-200 bg-red-50 text-red-700'
          }`}>
            <div className="flex gap-2.5 items-start">
              <span className="text-lg mt-0.5 flex-shrink-0">{isStateGuidance ? '🗺️' : '⚠️'}</span>
              <div>
                {isStateGuidance
                  ? <><strong>That's a state, not a city.</strong> {error.replace(/^[^.]+\.\s*/, '')}</>
                  : <><strong>Could not find location:</strong> {error}</>
                }
              </div>
            </div>
          </div>
        )
      })()}

      {/* Results */}
      {result && !loading && (
        <div className="space-y-5 animate-slide-up">

          {/* Alias banner */}
          {result.alias_note && (
            <div className="flex items-center gap-2.5 rounded-2xl border border-sky-200 bg-sky-50 px-4 py-3 text-sm text-sky-700">
              <span className="text-base">ℹ️</span>
              <span>
                Showing results for <strong>{result.city}</strong>
                {' '}— you searched for <em>{result.alias_note.split(' → ')[0]}</em>.
              </span>
            </div>
          )}

          {/* Location + Risk summary card */}
          <div className={`card bg-gradient-to-br ${styles.bg} ${styles.border} p-5`}>
            <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-4 mb-5">
              <div>
                <h2 className="text-2xl font-extrabold text-primary">{result.city}</h2>
                <p className="text-sm text-gray-400 mt-0.5">
                  {[result.state, result.country].filter(Boolean).join(', ')}
                  <span className="mx-1.5 opacity-40">·</span>
                  {result.latitude?.toFixed(2)}°N, {result.longitude?.toFixed(2)}°E
                </p>
              </div>
            </div>
            <RiskMeter score={result.risk.score} level={level} />
          </div>

          {/* Weather grid */}
          <div>
            <p className="section-label">Current Weather</p>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              <WeatherCard icon="🌡️" label="Temperature"   value={result.weather.temperature?.toFixed(1)}          unit="°C" />
              <WeatherCard icon="🥵" label="Feels Like"    value={result.weather.apparent_temperature?.toFixed(1)} unit="°C" highlight />
              <WeatherCard icon="💧" label="Humidity"      value={result.weather.humidity?.toFixed(0)}              unit="%" />
              <WeatherCard icon="💨" label="Wind Speed"    value={result.weather.wind_speed?.toFixed(1)}            unit="km/h" />
            </div>
          </div>

          {/* Recommendations */}
          <div>
            <p className="section-label">Safety Recommendations</p>
            <ul className="space-y-2">
              {result.recommendations.map((rec, i) => (
                <li key={i} className="flex gap-3 items-start card p-3.5 text-sm">
                  <span className="flex-shrink-0 text-base mt-0.5">
                    {i === 0 && level === 'Extreme' ? '🚨' : '✅'}
                  </span>
                  <span className="text-gray-700 leading-relaxed">{rec}</span>
                </li>
              ))}
            </ul>
          </div>

          {/* ── Section A: Risk Score Explanation ── */}
          <ScoreExplanation se={result.score_explanation} />

          {/* ── Section B: Hourly Heat Forecast ── */}
          <HourlyForecast forecast={result.forecast} />

          {/* ── Section C: Safer-Time Guidance ── */}
          <SaferTimeGuidance forecast={result.forecast} />

          {/* Attribution */}
          <p className="text-[11px] text-gray-400 text-center pt-2">
            Weather from{' '}
            <a href="https://open-meteo.com" target="_blank" rel="noreferrer" className="underline hover:text-primary">
              Open-Meteo
            </a>
            {' · '}Risk scoring by ChhayaRakshak AI
          </p>
        </div>
      )}
    </div>
  )
}
