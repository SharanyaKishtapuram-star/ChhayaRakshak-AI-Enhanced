import { useState, useRef } from 'react'
import { analyzeShadeImage } from '../services/api'

// ── Shade level config ─────────────────────────────────────────────────────────
const LEVEL_STYLES = {
  Poor:      { badge: 'bg-red-100 text-red-800 border-red-300',             bar: 'bg-red-500',      icon: '🔴', bg: 'from-red-50 to-rose-50',       border: 'border-red-200'     },
  Moderate:  { badge: 'bg-amber-100 text-amber-800 border-amber-300',       bar: 'bg-amber-400',    icon: '🟡', bg: 'from-amber-50 to-yellow-50',   border: 'border-amber-200'   },
  Good:      { badge: 'bg-sky-100 text-sky-800 border-sky-300',             bar: 'bg-sky-500',      icon: '🔵', bg: 'from-sky-50 to-blue-50',        border: 'border-sky-200'     },
  Excellent: { badge: 'bg-emerald-100 text-emerald-800 border-emerald-300', bar: 'bg-emerald-500',  icon: '🟢', bg: 'from-emerald-50 to-teal-50',   border: 'border-emerald-200' },
}

const MAX_FILE_MB = 10
const ACCEPTED = '.jpg,.jpeg,.png,.webp'

// ── Overlay legend items ───────────────────────────────────────────────────────
const OVERLAY_LEGEND = [
  { color: '#787878', label: 'Shade / Shadow',             note: 'dark pixels (HSV Value < 80)' },
  { color: '#28a028', label: 'Vegetation',                 note: 'green-hue pixels (HSV Hue 35–85°)' },
  { color: '#1450c8', label: 'Open Sky',                   note: 'blue-hue pixels (HSV Hue 90–130°)' },
  { color: '#dc6e14', label: 'Est. Sun-Exposed Surface',   note: 'residual — not shade, green, or sky' },
]

// ── Metric bar ─────────────────────────────────────────────────────────────────
function MetricBar({ label, value, colorClass, icon, method }) {
  const [showMethod, setShowMethod] = useState(false)
  return (
    <div className="space-y-1.5">
      <div className="flex items-center justify-between text-xs font-medium">
        <span className="flex items-center gap-1.5 text-gray-600">
          <span>{icon}</span> {label}
          <button
            onClick={() => setShowMethod(v => !v)}
            className="text-gray-400 hover:text-primary ml-0.5 text-[10px] leading-none border border-gray-300 rounded-full w-3.5 h-3.5 flex items-center justify-center flex-shrink-0"
            title="How is this calculated?"
            aria-label="How is this calculated?"
          >?</button>
        </span>
        <span className="font-bold text-primary">{value.toFixed(1)}%</span>
      </div>
      <div className="h-3 bg-gray-100 rounded-full overflow-hidden shadow-inner-sm">
        <div
          className={`h-full rounded-full transition-all duration-700 ${colorClass}`}
          style={{ width: `${Math.min(100, value)}%` }}
        />
      </div>
      {showMethod && (
        <p className="text-[11px] text-gray-500 bg-gray-50 rounded-lg px-2.5 py-1.5 border border-gray-200 leading-snug">
          {method}
        </p>
      )}
    </div>
  )
}

// ── Score arc ─────────────────────────────────────────────────────────────────
function ScoreArc({ score, level }) {
  const styles = LEVEL_STYLES[level] || LEVEL_STYLES.Poor
  const pct = Math.min(100, (score / 10) * 100)
  return (
    <div className="space-y-1.5">
      <div className="flex justify-between items-center text-[11px] font-medium text-gray-400">
        <span>0</span><span>Infrastructure Score</span><span>10</span>
      </div>
      <div className="h-4 bg-gray-100 rounded-full overflow-hidden shadow-inner-sm">
        <div className={`h-full rounded-full transition-all duration-700 ${styles.bar}`}
          style={{ width: `${pct}%` }} />
      </div>
      <div className="text-right text-[11px] text-gray-400">{score}/10</div>
    </div>
  )
}

// ── Image comparison (original vs overlay) ────────────────────────────────────
function ImageComparison({ preview, overlayB64, filename }) {
  const [activeTab, setActiveTab] = useState('overlay')

  return (
    <div className="space-y-2">
      {/* Tab switcher */}
      <div className="flex gap-2">
        {[
          { id: 'original', label: '📷 Original' },
          { id: 'overlay',  label: '🎨 Detection Overlay' },
        ].map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`flex-1 py-1.5 rounded-xl text-xs font-semibold border transition-colors ${
              activeTab === tab.id
                ? 'bg-primary text-white border-primary'
                : 'bg-white text-gray-600 border-sage-light hover:border-sage'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Image display */}
      <div className="relative rounded-2xl overflow-hidden border border-sage-light/60 bg-gray-50 shadow-card-sm">
        {activeTab === 'original' ? (
          <img
            src={preview}
            alt="Original uploaded image"
            className="w-full object-contain max-h-72"
          />
        ) : (
          overlayB64 ? (
            <img
              src={`data:image/png;base64,${overlayB64}`}
              alt="Detection overlay: shade, vegetation, sky, and sun-exposed areas colour-coded"
              className="w-full object-contain max-h-72"
            />
          ) : (
            <div className="flex items-center justify-center h-40 text-gray-400 text-sm">
              Overlay unavailable
            </div>
          )
        )}
      </div>

      {/* Overlay legend — only shown on overlay tab */}
      {activeTab === 'overlay' && (
        <div className="rounded-xl border border-sage-light/60 bg-white p-3">
          <p className="text-[11px] font-semibold text-gray-500 uppercase tracking-widest mb-2">Colour Legend</p>
          <div className="grid grid-cols-2 gap-x-4 gap-y-1.5">
            {OVERLAY_LEGEND.map(item => (
              <div key={item.label} className="flex items-start gap-2">
                <span
                  className="w-3 h-3 rounded-sm flex-shrink-0 mt-0.5 border border-black/10"
                  style={{ backgroundColor: item.color }}
                />
                <span className="text-[11px] text-gray-700 leading-snug">
                  <span className="font-medium">{item.label}</span>
                  <br />
                  <span className="text-gray-400">{item.note}</span>
                </span>
              </div>
            ))}
          </div>
          <p className="text-[10px] text-gray-400 mt-2 leading-snug">
            ⚠️ The overlay reflects pixel-level colour/brightness classification only — it cannot
            distinguish tree shade from building shadow, or dry grass from asphalt.
            See the Methodology & Limitations section below for full details.
          </p>
        </div>
      )}
    </div>
  )
}

// ── Recommendations list ──────────────────────────────────────────────────────
function RecommendationCard({ rec, index }) {
  const [expanded, setExpanded] = useState(false)
  const isUrgent = rec.urgent === true
  const hasWhy   = !!rec.why

  return (
    <li className={`flex gap-3 items-start card p-3.5 text-sm ${isUrgent ? 'border-amber-300 bg-amber-50' : ''}`}>
      <span className="flex-shrink-0 text-base mt-0.5">
        {isUrgent ? '⚠️' : '✅'}
      </span>
      <div className="flex-1 min-w-0">
        <p className="text-gray-700 leading-relaxed">{rec.text}</p>
        {hasWhy && (
          <>
            <button
              onClick={() => setExpanded(v => !v)}
              className="text-[11px] text-primary underline underline-offset-2 mt-1 hover:text-primary-light"
            >
              {expanded ? 'Hide rationale ↑' : 'Why this recommendation? ↓'}
            </button>
            {expanded && (
              <p className="text-[11px] text-gray-500 mt-1.5 leading-snug bg-gray-50 rounded-lg px-2.5 py-1.5 border border-gray-200">
                {rec.why}
              </p>
            )}
          </>
        )}
      </div>
    </li>
  )
}

// ── Methodology & Limitations disclosure ─────────────────────────────────────
function MethodologyDisclosure() {
  const [open, setOpen] = useState(false)
  return (
    <div className="rounded-2xl border border-sage-light/60 bg-sage-soft/20">
      <button
        onClick={() => setOpen(v => !v)}
        className="w-full flex items-center justify-between px-4 py-3 text-left"
      >
        <span className="text-xs font-semibold text-gray-600 uppercase tracking-widest">
          📋 Methodology &amp; Limitations
        </span>
        <span className="text-gray-400 text-sm">{open ? '▲' : '▼'}</span>
      </button>

      {open && (
        <div className="px-4 pb-4 space-y-3 text-xs text-gray-600 leading-relaxed border-t border-sage-light/40">
          <div className="pt-3 space-y-2.5">

            <div>
              <p className="font-semibold text-gray-700 mb-0.5">How shade is detected</p>
              <p>
                Pixels with HSV <em>Value</em> below 80 (out of 255) are classified as shaded.
                This captures shadows cast by buildings, tree canopies, and overhead structures.
                <span className="text-amber-700 font-medium"> Limitation:</span> dark-painted objects
                (black vehicles, dark walls) also trigger this mask. The algorithm cannot distinguish
                tree-canopy shade from structural shade.
              </p>
            </div>

            <div>
              <p className="font-semibold text-gray-700 mb-0.5">How vegetation is detected</p>
              <p>
                Pixels with HSV <em>Hue</em> 35–85° and <em>Saturation</em> &gt; 40 are classified
                as vegetation.
                <span className="text-amber-700 font-medium"> Limitation:</span> yellowed, dry, or
                brown vegetation may be missed. Blue-green painted surfaces near the hue boundary
                can be mis-classified as green cover.
              </p>
            </div>

            <div>
              <p className="font-semibold text-gray-700 mb-0.5">How sky is detected</p>
              <p>
                Pixels with HSV <em>Hue</em> 90–130°, <em>Saturation</em> &gt; 50, and
                <em> Value</em> &gt; 100 are classified as sky.
                <span className="text-amber-700 font-medium"> Limitation:</span> this detects
                saturated blue-hue pixels only. Pale, hazy, or overexposed sky has low
                saturation and reads near 0%. Sky glimpsed through dense foliage can appear
                teal (Hue &lt; 90°) and is also missed. This metric under-counts visible sky
                whenever sky is not deeply saturated blue.
              </p>
            </div>

            <div>
              <p className="font-semibold text-gray-700 mb-0.5">How sun-exposed surface is estimated</p>
              <p>
                This is a <strong>residual estimate</strong>: pixels not classified as shade,
                vegetation, or sky. It may represent paved surfaces, soil, mulch, stone,
                building walls, vehicles, or anything else outside the three colour/brightness
                categories — not necessarily hard or sun-exposed surface.
                <span className="text-amber-700 font-medium"> Limitation:</span> dark green
                foliage is counted in <em>both</em> the shade and vegetation masks
                simultaneously; the residual formula subtracts those pixels twice, making this
                number a slight underestimate of true residual pixels. The detection overlay
                paints vegetation colour on top of shade colour for these overlapping pixels,
                so the grey (shade) region in the overlay appears smaller than the shade
                percentage alone would suggest.
              </p>
            </div>

            <div>
              <p className="font-semibold text-gray-700 mb-0.5">What this tool does not measure</p>
              <ul className="list-disc list-inside space-y-0.5 text-gray-500">
                <li>Surface or air temperatures — pixel brightness is not temperature.</li>
                <li>Historical or seasonal patterns.</li>
                <li>Population exposure or vulnerability.</li>
                <li>The difference between canopy shade and structural shade.</li>
              </ul>
            </div>

            <div>
              <p className="font-semibold text-gray-700 mb-0.5">Infrastructure score formula</p>
              <p>
                Score = min(5, shade%/10) + min(3, green%/10) − min(1, sky%/40) + 1
                (baseline). Clamped to 0–10. Higher = more natural cooling infrastructure visible.
                This is a heuristic indicator, not a validated urban-heat index.
              </p>
            </div>

            <p className="text-gray-400 pt-1">
              Analysis engine: <a href="https://opencv.org" target="_blank" rel="noreferrer" className="underline hover:text-primary">OpenCV</a> — runs entirely offline. No image data is sent to any external service.
            </p>
          </div>
        </div>
      )}
    </div>
  )
}

// ── Page ──────────────────────────────────────────────────────────────────────
export default function ShadeDetection() {
  const [preview, setPreview]   = useState(null)
  const [file, setFile]         = useState(null)
  const [loading, setLoading]   = useState(false)
  const [error, setError]       = useState(null)
  const [result, setResult]     = useState(null)
  const [dragOver, setDragOver] = useState(false)
  const fileInputRef            = useRef(null)

  function handleFileChange(e) {
    const selected = e.target.files?.[0]
    if (!selected) return
    applyFile(selected)
  }

  function handleDrop(e) {
    e.preventDefault()
    setDragOver(false)
    const dropped = e.dataTransfer.files?.[0]
    if (!dropped) return
    applyFile(dropped)
  }

  function applyFile(selected) {
    if (selected.size > MAX_FILE_MB * 1024 * 1024) {
      setError(`File is too large (${(selected.size / 1024 / 1024).toFixed(1)} MB). Maximum is ${MAX_FILE_MB} MB.`)
      return
    }
    setFile(selected)
    setError(null)
    setResult(null)
    const reader = new FileReader()
    reader.onload = ev => setPreview(ev.target.result)
    reader.readAsDataURL(selected)
  }

  async function handleAnalyse() {
    if (!file) return
    setLoading(true)
    setError(null)
    setResult(null)
    try {
      const data = await analyzeShadeImage(file)
      setResult(data)
    } catch (err) {
      setError(err.message || 'Analysis failed. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  function handleReset() {
    setFile(null); setPreview(null); setResult(null); setError(null)
    if (fileInputRef.current) fileInputRef.current.value = ''
  }

  const level  = result?.shade_level
  const styles = level ? LEVEL_STYLES[level] : null

  return (
    <div className="page-wrapper animate-fade-in">

      {/* ── Header ── */}
      <div className="mb-8">
        <p className="section-label">Feature 2</p>
        <h1 className="text-3xl font-extrabold text-primary mb-2">🌿 Shade &amp; Infrastructure Detection</h1>
        <p className="text-gray-500 text-sm leading-relaxed max-w-xl">
          Upload a street, park, or neighbourhood photo. OpenCV analyses shade coverage,
          green vegetation, sky exposure, and estimated sun-exposed surface — then
          generates targeted urban cooling recommendations.
        </p>
        <p className="text-xs text-gray-400 mt-1.5">
          Accepts JPEG, PNG, WebP · Max {MAX_FILE_MB} MB · Analysed offline — no external API
        </p>
      </div>

      {/* ── Upload zone ── */}
      {!result && (
        <div
          onDrop={handleDrop}
          onDragOver={e => { e.preventDefault(); setDragOver(true) }}
          onDragLeave={() => setDragOver(false)}
          onClick={() => fileInputRef.current?.click()}
          className={`relative rounded-2xl border-2 border-dashed p-8 text-center cursor-pointer
                      transition-all duration-200 bg-white
                      ${dragOver
                        ? 'border-sage bg-sage-soft scale-[1.01]'
                        : preview
                        ? 'border-sage/50 bg-sage-soft/30'
                        : 'border-sage-light hover:border-sage hover:bg-sage-soft/20'
                      }`}
        >
          <input
            ref={fileInputRef}
            type="file"
            accept={ACCEPTED}
            onChange={handleFileChange}
            className="hidden"
          />

          {preview ? (
            <div className="space-y-3">
              <img
                src={preview}
                alt="Preview"
                className="max-h-60 mx-auto rounded-xl object-cover shadow-card-md"
              />
              <p className="text-sm font-medium text-gray-700 truncate">{file?.name}</p>
              <p className="text-xs text-gray-400">
                {(file?.size / 1024).toFixed(0)} KB · Click to change
              </p>
            </div>
          ) : (
            <div className="space-y-3 py-4">
              <div className={`w-16 h-16 rounded-2xl bg-sage-soft border border-sage-light mx-auto flex items-center justify-center text-3xl transition-transform duration-200 ${dragOver ? 'scale-110' : ''}`}>
                🖼️
              </div>
              <div>
                <p className="text-sm font-semibold text-gray-700">
                  Drag &amp; drop or <span className="text-primary underline">click to upload</span>
                </p>
                <p className="text-xs text-gray-400 mt-1">JPEG, PNG, WebP · up to {MAX_FILE_MB} MB</p>
              </div>
            </div>
          )}
        </div>
      )}

      {/* ── Action buttons ── */}
      {!result && (
        <div className="flex gap-3 mt-4">
          <button onClick={handleAnalyse} disabled={!file || loading} className="btn-primary flex-1">
            {loading
              ? <><svg className="animate-spin w-4 h-4" viewBox="0 0 24 24" fill="none"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"/></svg> Running OpenCV analysis…</>
              : '🔍 Analyse Image'
            }
          </button>
          {file && (
            <button onClick={handleReset} className="btn-secondary">Clear</button>
          )}
        </div>
      )}

      {/* ── Error ── */}
      {error && !loading && (
        <div className="mt-4 rounded-2xl border border-red-200 bg-red-50 p-4 text-sm text-red-700 flex gap-2.5">
          <span className="flex-shrink-0 text-base">⚠️</span>
          <div><strong>Error:</strong> {error}</div>
        </div>
      )}

      {/* ── Results ── */}
      {result && !loading && (
        <div className="space-y-5 animate-slide-up">

          {/* ── 1. Summary card ── */}
          <div className={`card bg-gradient-to-br ${styles.bg} ${styles.border} p-5`}>
            <div className="flex flex-wrap items-center justify-between gap-2 mb-3">
              <h2 className="text-lg font-bold text-primary truncate">{result.filename}</h2>
              <span className={`chip border text-xs font-semibold ${styles.badge}`}>
                {styles.icon} {level} Cooling Score
              </span>
            </div>
            <ScoreArc score={result.infrastructure_score} level={level} />
            <p className="text-[11px] text-gray-400 mt-2">
              {result.width} × {result.height} px · {result.total_pixels?.toLocaleString()} pixels analysed
            </p>
          </div>

          {/* ── 2. Image comparison: original vs overlay ── */}
          <div>
            <p className="section-label">Visual Detection Overlay</p>
            <ImageComparison
              preview={preview}
              overlayB64={result.overlay_image}
              filename={result.filename}
            />
          </div>

          {/* ── 3. Analysis metrics ── */}
          <div>
            <p className="section-label">Analysis Metrics</p>
            <div className="card p-5 space-y-5">
              <MetricBar
                label="Shade / Shadow Coverage"
                value={result.shade_percent}
                colorClass="bg-gray-500"
                icon="🌑"
                method="Pixels where HSV Value < 80 — captures dark shadow regions. Cannot distinguish tree shade from building shadow or dark surfaces."
              />
              <MetricBar
                label="Green Vegetation Cover"
                value={result.green_percent}
                colorClass="bg-emerald-500"
                icon="🌿"
                method="Pixels with HSV Hue 35–85° and Saturation > 40 — captures green foliage. Dry/yellowed vegetation may be under-counted."
              />
              <MetricBar
                label="Open Sky Exposure"
                value={result.sky_percent}
                colorClass="bg-sky-400"
                icon="☀️"
                method="Counts saturated blue-hue pixels only (HSV Hue 90–130°, Saturation > 50, Value > 100). Pale, overexposed, or hazy sky reads near 0% because those pixels fail the saturation threshold. Sky glimpsed through foliage may also be missed if its hue shifts toward cyan (H < 90°)."
              />
              <MetricBar
                label="Est. Sun-Exposed Surface"
                value={result.sun_exposed_percent}
                colorClass="bg-orange-400"
                icon="🏗️"
                method="Residual estimate: pixels not classified as shade, vegetation, or sky. May include concrete, soil, mulch, stone paths, building walls, vehicles, or any other surface that does not match the three colour/brightness categories."
              />

              {/* Totals note */}
              <p className="text-[11px] text-gray-400 border-t border-gray-100 pt-3">
                Percentages are independent per-mask counts and will not sum to 100%.
                Shade and green can overlap (shaded foliage), and unclassified pixels are not shown as a separate category.
              </p>
            </div>
          </div>

          {/* ── 4. Interpretation ── */}
          <div>
            <p className="section-label">Interpretation</p>
            <div className="card p-5">
              <p className="text-sm text-gray-700 leading-relaxed">{result.interpretation}</p>
            </div>
          </div>

          {/* ── 5. Smart recommendations ── */}
          <div>
            <p className="section-label">Urban Cooling Recommendations</p>
            <p className="text-xs text-gray-400 mb-2">
              Recommendations are generated from the actual analysis results above.
              Click "Why this recommendation?" on any item to see the detected condition that triggered it.
            </p>
            <ul className="space-y-2">
              {result.recommendations.map((rec, i) => (
                <RecommendationCard key={i} rec={rec} index={i} />
              ))}
            </ul>
          </div>

          {/* ── 6. Methodology & Limitations ── */}
          <MethodologyDisclosure />

          {/* ── Analyse another ── */}
          <div className="text-center pt-2">
            <button onClick={handleReset} className="btn-secondary">
              🖼️ Analyse Another Image
            </button>
          </div>

          {/* Attribution */}
          <p className="text-[11px] text-gray-400 text-center">
            Analysis by{' '}
            <a href="https://opencv.org" target="_blank" rel="noreferrer" className="underline hover:text-primary">OpenCV</a>
            {' · '}ChhayaRakshak AI
          </p>
        </div>
      )}
    </div>
  )
}
