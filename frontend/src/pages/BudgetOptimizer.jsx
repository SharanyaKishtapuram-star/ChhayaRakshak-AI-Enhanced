import { useState } from 'react'
import { optimizeBudget, getHeatRisk } from '../services/api'
import ILLUSTRATIONS from '../assets/interventionIllustrations'

// ── Area type options (unchanged values — used in API request) ────────────────
const AREA_TYPES = [
  { value: 'residential', label: 'Residential',  icon: '🏘️', desc: 'Housing colonies and neighbourhood streets' },
  { value: 'commercial',  label: 'Commercial',   icon: '🏢', desc: 'Markets, offices, and business districts'   },
  { value: 'mixed',       label: 'Mixed Use',    icon: '🏙️', desc: 'Areas combining housing and commerce'       },
  { value: 'park',        label: 'Park / Green', icon: '🌳', desc: 'Parks, open spaces, and recreation areas'   },
]

const BUDGET_PRESETS = [1, 5, 10, 25, 50, 100]

// ── Intervention illustration ─────────────────────────────────────────────────
// Renders the inline SVG for an intervention, or nothing if not found.
// dangerouslySetInnerHTML is safe here: the SVG strings are authored locally,
// contain no user input, and no script tags.
function InterventionIllustration({ imageTag, name, selected }) {
  const svg = ILLUSTRATIONS[imageTag]
  if (!svg) return null
  return (
    <div
      className={`w-full rounded-xl overflow-hidden mb-3 transition-all duration-200 ${
        selected ? '' : 'opacity-40 grayscale'
      }`}
      style={{ height: '90px' }}
      role="img"
      aria-label={name}
      dangerouslySetInnerHTML={{ __html: svg }}
    />
  )
}

// ── Intervention card ─────────────────────────────────────────────────────────
function InterventionCard({ item }) {
  const impactDots = Math.round(item.cooling_score / 2) // 1–5 dots
  return (
    <div className={`rounded-2xl border p-4 text-sm transition-all duration-200 ${
      item.selected
        ? 'border-primary/30 bg-gradient-to-br from-sage-soft to-white shadow-card-md'
        : 'border-sage-light/30 bg-gray-50/50 opacity-55'
    }`}>
      {/* Illustration — gracefully absent if image_tag missing or unknown */}
      <InterventionIllustration
        imageTag={item.image_tag}
        name={item.name}
        selected={item.selected}
      />
      <div className="flex justify-between items-start gap-2 mb-2">
        <div className="flex items-center gap-2 min-w-0">
          <span className={`text-base flex-shrink-0 ${item.selected ? '' : 'grayscale opacity-60'}`}>
            {item.selected ? '✅' : '○'}
          </span>
          <span className={`font-semibold truncate ${item.selected ? 'text-primary' : 'text-gray-400'}`}>
            {item.name}
          </span>
        </div>
        <span className={`chip flex-shrink-0 text-[11px] font-bold ${item.selected ? 'border-primary/30 bg-primary/5 text-primary' : 'border-gray-200 bg-gray-100 text-gray-400'}`}>
          ₹{item.cost_lakhs}L
        </span>
      </div>
      <p className="text-gray-500 text-xs leading-relaxed mb-2.5">{item.description}</p>
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3 text-xs text-gray-500">
          <span className="flex items-center gap-1">
            🌡️
            <span className="flex gap-0.5">
              {Array.from({ length: 5 }).map((_, i) => (
                <span key={i} className={`w-2 h-2 rounded-sm ${i < impactDots ? (item.selected ? 'bg-accent' : 'bg-gray-300') : 'bg-gray-100'}`} />
              ))}
            </span>
            <span className="font-medium">{item.cooling_score}/10</span>
          </span>
        </div>
        <span className="text-[11px] text-gray-400">{item.units}</span>
      </div>
      {item.co_benefits && item.selected && (
        <p className="text-xs text-emerald-700 mt-2 flex items-center gap-1">
          <span>🌱</span> {item.co_benefits}
        </p>
      )}
    </div>
  )
}

// ── Heat-risk insight card ────────────────────────────────────────────────────
// Shown above optimization results whenever a city is provided.
// Uses only data returned from the API — never hardcoded scores.

const _RISK_STYLES = {
  Low:      { bar: 'bg-green-500',  badge: 'bg-green-100 text-green-800 border-green-300',  icon: '🟢', tip: 'Current conditions are comfortable. Any intervention will maintain this advantage.' },
  Moderate: { bar: 'bg-yellow-400', badge: 'bg-yellow-100 text-yellow-800 border-yellow-300', icon: '🟡', tip: 'Moderate heat stress present. Shade and reflective interventions will have meaningful impact.' },
  High:     { bar: 'bg-orange-500', badge: 'bg-orange-100 text-orange-800 border-orange-300', icon: '🟠', tip: 'High heat risk. Prioritise shade trees, cool roofs, and misting stations for fastest relief.' },
  Extreme:  { bar: 'bg-red-500',    badge: 'bg-red-100 text-red-800 border-red-300',          icon: '🔴', tip: 'Extreme heat risk. Every selected intervention directly counters dangerous urban heat.' },
}

function HeatRiskInsightCard({ loading, error, data }) {
  // Don't render at all if no fetch was attempted (no city given)
  if (!loading && !error && !data) return null

  return (
    <div className="rounded-2xl border border-sage-light/40 bg-forest-gradient text-white p-5 mb-5 animate-slide-up">
      <div className="flex items-center gap-2 mb-3">
        <span className="text-base">🌡️</span>
        <p className="text-xs font-semibold uppercase tracking-widest text-sage-light/70">Live Heat-Risk Insights</p>
      </div>

      {/* Loading */}
      {loading && (
        <div className="flex items-center gap-2 text-sm text-sage-light/80">
          <svg className="animate-spin w-4 h-4 flex-shrink-0" viewBox="0 0 24 24" fill="none">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"/>
          </svg>
          Fetching live heat-risk data…
        </div>
      )}

      {/* Error — city not found or API unavailable */}
      {!loading && error && (
        <p className="text-sm text-sage-light/70 italic">
          Heat-risk data unavailable for this city: <span className="not-italic text-white/80">{error}</span>
        </p>
      )}

      {/* Live data */}
      {!loading && data && (() => {
        const level = data.risk.level
        const styles = _RISK_STYLES[level] || _RISK_STYLES['Moderate']
        const score  = data.risk.score
        return (
          <div className="space-y-3">
            {/* City + badge row */}
            <div className="flex items-center justify-between gap-3 flex-wrap">
              <div>
                <span className="text-lg font-extrabold leading-none">{data.city}</span>
                {data.state && <span className="text-xs text-sage-light/60 ml-2">{data.state}</span>}
              </div>
              <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full border text-xs font-bold ${styles.badge}`}>
                {styles.icon} {level} Risk
              </span>
            </div>

            {/* Score bar */}
            <div>
              <div className="flex justify-between text-xs text-sage-light/60 mb-1">
                <span>Risk score</span>
                <span className="font-bold text-white">{score} / 10</span>
              </div>
              <div className="h-2 bg-white/10 rounded-full overflow-hidden">
                <div
                  className={`h-full rounded-full transition-all duration-700 ${styles.bar}`}
                  style={{ width: `${score * 10}%` }}
                />
              </div>
            </div>

            {/* Weather snapshot */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-center text-xs">
              {[
                { label: 'Temp',      value: `${data.weather.temperature} °C`   },
                { label: 'Feels like', value: `${data.weather.apparent_temperature} °C` },
                { label: 'Humidity',  value: `${data.weather.humidity} %`       },
                { label: 'Wind',      value: `${data.weather.wind_speed} km/h`  },
              ].map(({ label, value }) => (
                <div key={label} className="bg-white/10 rounded-xl py-2 px-1">
                  <div className="font-bold text-sm leading-none">{value}</div>
                  <div className="text-sage-light/60 mt-0.5">{label}</div>
                </div>
              ))}
            </div>

            {/* Contextual tip */}
            <p className="text-xs text-sage-light/80 leading-relaxed border-t border-white/10 pt-3">
              💡 {styles.tip}
            </p>
          </div>
        )
      })()}
    </div>
  )
}



// ── Page ──────────────────────────────────────────────────────────────────────
export default function BudgetOptimizer() {
  const [budget, setBudget]     = useState(10)
  const [areaType, setAreaType] = useState('mixed')
  const [city, setCity]         = useState('')
  const [loading, setLoading]   = useState(false)
  const [error, setError]       = useState(null)
  const [result, setResult]     = useState(null)

  // Heat-risk insight state (only populated when a city is provided)
  const [heatLoading, setHeatLoading] = useState(false)
  const [heatError,   setHeatError]   = useState(null)
  const [heatData,    setHeatData]    = useState(null)

  async function handleOptimize() {
    setLoading(true)
    setError(null)
    setResult(null)
    // Reset dependent sections when inputs change
    setHeatData(null)
    setHeatError(null)

    // Fire heat-risk fetch in parallel — only if a city was entered.
    // We never await it here; it resolves independently into its own state.
    const cityTrimmed = city.trim()
    if (cityTrimmed.length >= 2) {
      setHeatLoading(true)
      getHeatRisk(cityTrimmed)
        .then(d  => setHeatData(d))
        .catch(e => setHeatError(e.message || 'Heat-risk data unavailable'))
        .finally(() => setHeatLoading(false))
    }

    try {
      const data = await optimizeBudget(budget, areaType, city)
      setResult(data)
    } catch (err) {
      setError(err.message || 'Optimization failed. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="page-wrapper animate-fade-in">

      {/* Header */}
      <div className="mb-8">
        <p className="section-label">Feature 4</p>
        <h1 className="text-3xl font-extrabold text-primary mb-2">💰 Budget Optimizer for Cooling Interventions</h1>
        <p className="text-gray-500 text-sm leading-relaxed max-w-xl">
          Enter your available budget and area type. The optimizer selects the highest-impact
          urban cooling interventions using a greedy value-density algorithm — all local, no external API.
        </p>
      </div>

      {/* Input form */}
      <div className="card p-6 space-y-6 mb-6">

        {/* Budget input */}
        <div>
          <label className="section-label block">
            Budget (₹ Lakhs) &nbsp;<span className="normal-case text-xs text-gray-400 font-normal tracking-normal">1 Lakh = ₹1,00,000</span>
          </label>
          <div className="flex items-center gap-3 flex-wrap">
            <input
              type="number"
              min="0.5"
              max="500"
              step="0.5"
              value={budget}
              onChange={e => setBudget(parseFloat(e.target.value) || 0)}
              className="w-28 input-field"
            />
            <div className="flex flex-wrap gap-1.5">
              {BUDGET_PRESETS.map(p => (
                <button
                  key={p}
                  onClick={() => setBudget(p)}
                  className={`chip transition-all duration-150 ${
                    budget === p
                      ? 'bg-primary text-white border-primary font-bold'
                      : 'border-sage-light text-gray-600 hover:border-sage hover:text-primary bg-white'
                  }`}
                >
                  ₹{p}L
                </button>
              ))}
            </div>
          </div>

          {/* Budget progress bar */}
          <div className="mt-3 h-1.5 bg-gray-100 rounded-full overflow-hidden">
            <div
              className="h-full bg-gradient-to-r from-primary to-sage rounded-full transition-all duration-500"
              style={{ width: `${Math.min(100, (budget / 100) * 100)}%` }}
            />
          </div>
        </div>

        {/* Area type */}
        <div>
          <label className="section-label block">Area Type</label>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
            {AREA_TYPES.map(({ value, label, icon, desc }) => (
              <button
                key={value}
                onClick={() => setAreaType(value)}
                title={desc}
                className={`p-3 text-xs rounded-xl border text-left transition-all duration-150 ${
                  areaType === value
                    ? 'bg-primary text-white border-primary shadow-card-md'
                    : 'border-sage-light/60 hover:border-sage hover:bg-sage-soft bg-white text-gray-700'
                }`}
              >
                <span className="text-lg block mb-1">{icon}</span>
                <span className="font-semibold">{label}</span>
              </button>
            ))}
          </div>
        </div>

        {/* Optional city */}
        <div>
          <label className="section-label block">
            City <span className="normal-case text-xs text-gray-400 font-normal tracking-normal">(optional — for summary context)</span>
          </label>
          <input
            type="text"
            value={city}
            onChange={e => setCity(e.target.value)}
            placeholder="e.g. Hyderabad"
            className="input-field"
          />
        </div>

        <button
          onClick={handleOptimize}
          disabled={loading || budget <= 0}
          className="btn-primary w-full text-base py-3"
        >
          {loading
            ? <><svg className="animate-spin w-4 h-4" viewBox="0 0 24 24" fill="none"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"/></svg> Calculating…</>
            : '🔍 Find Best Interventions'
          }
        </button>
      </div>

      {/* Error */}
      {error && !loading && (
        <div className="rounded-2xl border border-red-200 bg-red-50 p-4 text-sm text-red-700 flex gap-2.5 mb-6">
          <span className="flex-shrink-0 text-base">⚠️</span>
          <div><strong>Error:</strong> {error}</div>
        </div>
      )}

      {/* Live heat-risk insights — shown when city fetch resolves */}
      {(heatLoading || heatError || heatData) && result && !loading && (
        <HeatRiskInsightCard
          loading={heatLoading}
          error={heatError}
          data={heatData}
        />
      )}

      {/* Results */}
      {result && !loading && (
        <div className="space-y-5 animate-slide-up">

          {/* Summary banner */}
          <div className="bg-forest-gradient rounded-2xl p-6 text-white">
            <p className="text-sm text-sage-light/80 leading-relaxed mb-5">{result.roi_summary}</p>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              {[
                { label: 'Budget',         value: `₹${result.budget_lakhs}L`,            accent: false },
                { label: 'Spent',          value: `₹${result.total_cost_lakhs}L`,         accent: true  },
                { label: 'Remaining',      value: `₹${result.remaining_lakhs}L`,          accent: false },
                { label: 'Temp Reduction', value: `↓${result.expected_temp_reduction_c} °C`, accent: true },
              ].map(({ label, value, accent }) => (
                <div key={label} className={`rounded-xl p-3 text-center ${accent ? 'bg-accent/20 border border-accent/30' : 'bg-white/10'}`}>
                  <div className="text-xl font-extrabold leading-none">{value}</div>
                  <div className="text-xs text-sage-light/70 mt-1">{label}</div>
                </div>
              ))}
            </div>
          </div>

          {/* Budget progress */}
          <div className="card p-4">
            <div className="flex justify-between text-xs font-medium text-gray-500 mb-2">
              <span>Budget utilisation</span>
              <span className="text-primary font-bold">
                {Math.round((result.total_cost_lakhs / result.budget_lakhs) * 100)}%
              </span>
            </div>
            <div className="h-3 bg-gray-100 rounded-full overflow-hidden">
              <div
                className="h-full bg-gradient-to-r from-primary to-sage rounded-full transition-all duration-700"
                style={{ width: `${Math.min(100, (result.total_cost_lakhs / result.budget_lakhs) * 100)}%` }}
              />
            </div>
          </div>

          {/* Interventions */}
          <div>
            <p className="section-label">
              Interventions ({result.selected_interventions.length} selected of {result.all_interventions.length})
            </p>
            <div className="space-y-3">
              {result.all_interventions.map(item => (
                <InterventionCard key={item.id} item={item} />
              ))}
            </div>
          </div>

          {/* Attribution */}
          <p className="text-[11px] text-gray-400 text-center">
            Optimized locally · ChhayaRakshak AI · Costs are indicative estimates for Indian urban context
          </p>
        </div>
      )}

    </div>
  )
}
