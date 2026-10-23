/**
 * interventionIllustrations.js
 *
 * Self-contained SVG illustrations for each Budget Optimizer catalogue item.
 * All SVGs are inline strings — no external files, no CDN, no API keys.
 * Each illustration uses the project's colour palette (forest greens, warm accents).
 *
 * Keyed by the `image_tag` field returned by the backend catalogue.
 * The InterventionCard component uses ILLUSTRATIONS[item.image_tag] to look up
 * the correct SVG, falling back gracefully if the key is missing.
 */

const ILLUSTRATIONS = {

  // ── Tree Planting ──────────────────────────────────────────────────────────
  tree_planting: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 120 80" aria-hidden="true">
    <rect width="120" height="80" rx="8" fill="#f0f7f1"/>
    <!-- ground -->
    <ellipse cx="60" cy="72" rx="42" ry="6" fill="#b8d9bd" opacity="0.5"/>
    <!-- left tree -->
    <rect x="22" y="52" width="5" height="18" rx="2" fill="#5d4037"/>
    <ellipse cx="24.5" cy="46" rx="12" ry="15" fill="#2d5a40"/>
    <ellipse cx="24.5" cy="42" rx="9" ry="12" fill="#3d7a55"/>
    <!-- centre tree (tallest) -->
    <rect x="57" y="45" width="6" height="25" rx="2" fill="#5d4037"/>
    <ellipse cx="60" cy="38" rx="15" ry="18" fill="#1a3a2a"/>
    <ellipse cx="60" cy="33" rx="11" ry="13" fill="#2d5a40"/>
    <ellipse cx="60" cy="28" rx="7" ry="9" fill="#3d7a55"/>
    <!-- right tree -->
    <rect x="91" y="50" width="5" height="20" rx="2" fill="#5d4037"/>
    <ellipse cx="93.5" cy="44" rx="12" ry="14" fill="#2d5a40"/>
    <ellipse cx="93.5" cy="40" rx="9" ry="10" fill="#3d7a55"/>
    <!-- sun glint -->
    <circle cx="102" cy="12" r="8" fill="#f97316" opacity="0.25"/>
    <circle cx="102" cy="12" r="5" fill="#f97316" opacity="0.35"/>
  </svg>`,

  // ── Cool Roof ──────────────────────────────────────────────────────────────
  cool_roof: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 120 80" aria-hidden="true">
    <rect width="120" height="80" rx="8" fill="#eff6ff"/>
    <!-- building body -->
    <rect x="20" y="38" width="80" height="34" rx="4" fill="#cbd5e1"/>
    <!-- roof base -->
    <rect x="16" y="30" width="88" height="14" rx="3" fill="#94a3b8"/>
    <!-- cool coating highlight (white reflective layer) -->
    <rect x="16" y="30" width="88" height="7" rx="3" fill="#f8fafc"/>
    <rect x="20" y="31" width="80" height="3" rx="2" fill="white" opacity="0.8"/>
    <!-- reflection rays -->
    <line x1="30" y1="26" x2="26" y2="18" stroke="#e0f2fe" stroke-width="2" stroke-linecap="round"/>
    <line x1="50" y1="26" x2="48" y2="17" stroke="#e0f2fe" stroke-width="2" stroke-linecap="round"/>
    <line x1="70" y1="26" x2="72" y2="17" stroke="#e0f2fe" stroke-width="2" stroke-linecap="round"/>
    <line x1="90" y1="26" x2="94" y2="18" stroke="#e0f2fe" stroke-width="2" stroke-linecap="round"/>
    <!-- sun -->
    <circle cx="60" cy="10" r="6" fill="#fbbf24" opacity="0.7"/>
    <!-- windows -->
    <rect x="30" y="44" width="14" height="12" rx="2" fill="#93c5fd" opacity="0.7"/>
    <rect x="53" y="44" width="14" height="12" rx="2" fill="#93c5fd" opacity="0.7"/>
    <rect x="76" y="44" width="14" height="12" rx="2" fill="#93c5fd" opacity="0.7"/>
    <!-- door -->
    <rect x="51" y="58" width="18" height="14" rx="2" fill="#64748b"/>
  </svg>`,

  // ── Shade Sails ────────────────────────────────────────────────────────────
  shade_sails: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 120 80" aria-hidden="true">
    <rect width="120" height="80" rx="8" fill="#fff8f0"/>
    <!-- ground / path -->
    <rect x="0" y="62" width="120" height="18" rx="0" fill="#e8d5b7" opacity="0.6"/>
    <!-- sail 1 (left, teal) -->
    <polygon points="10,14 72,8 55,52" fill="#0d9488" opacity="0.80"/>
    <polygon points="10,14 72,8 55,52" fill="none" stroke="#0f766e" stroke-width="1"/>
    <!-- sail 2 (right, orange) -->
    <polygon points="48,10 110,18 90,54" fill="#ea580c" opacity="0.75"/>
    <polygon points="48,10 110,18 90,54" fill="none" stroke="#c2410c" stroke-width="1"/>
    <!-- support posts -->
    <line x1="10" y1="14" x2="10" y2="64" stroke="#78716c" stroke-width="3" stroke-linecap="round"/>
    <line x1="110" y1="18" x2="110" y2="64" stroke="#78716c" stroke-width="3" stroke-linecap="round"/>
    <!-- people silhouettes below shade -->
    <circle cx="45" cy="60" r="4" fill="#57534e" opacity="0.5"/>
    <rect x="43" y="64" width="4" height="8" rx="2" fill="#57534e" opacity="0.5"/>
    <circle cx="68" cy="60" r="4" fill="#57534e" opacity="0.5"/>
    <rect x="66" y="64" width="4" height="8" rx="2" fill="#57534e" opacity="0.5"/>
  </svg>`,

  // ── Green Wall ─────────────────────────────────────────────────────────────
  green_wall: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 120 80" aria-hidden="true">
    <rect width="120" height="80" rx="8" fill="#f0f7f1"/>
    <!-- building wall -->
    <rect x="28" y="8" width="64" height="66" rx="4" fill="#d1d5db"/>
    <!-- green wall panels (grid of leaf clusters) -->
    <rect x="28" y="8" width="28" height="66" rx="4" fill="#2d5a40"/>
    <!-- leaf texture rows -->
    <ellipse cx="42" cy="20" rx="10" ry="7" fill="#3d7a55"/>
    <ellipse cx="42" cy="34" rx="10" ry="7" fill="#3d7a55"/>
    <ellipse cx="42" cy="48" rx="10" ry="7" fill="#3d7a55"/>
    <ellipse cx="42" cy="62" rx="10" ry="7" fill="#3d7a55"/>
    <ellipse cx="38" cy="27" rx="7" ry="5" fill="#4ade80" opacity="0.35"/>
    <ellipse cx="46" cy="41" rx="7" ry="5" fill="#4ade80" opacity="0.35"/>
    <ellipse cx="38" cy="55" rx="7" ry="5" fill="#4ade80" opacity="0.35"/>
    <!-- windows on plain wall -->
    <rect x="66" y="20" width="16" height="12" rx="2" fill="#93c5fd" opacity="0.7"/>
    <rect x="66" y="40" width="16" height="12" rx="2" fill="#93c5fd" opacity="0.7"/>
    <rect x="66" y="60" width="16" height="12" rx="2" fill="#93c5fd" opacity="0.7"/>
    <!-- sun -->
    <circle cx="106" cy="14" r="7" fill="#fbbf24" opacity="0.55"/>
  </svg>`,

  // ── Misting Station ────────────────────────────────────────────────────────
  misting_station: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 120 80" aria-hidden="true">
    <rect width="120" height="80" rx="8" fill="#f0f9ff"/>
    <!-- ground -->
    <rect x="0" y="65" width="120" height="15" rx="0" fill="#e2e8f0" opacity="0.5"/>
    <!-- post -->
    <rect x="56" y="28" width="8" height="38" rx="3" fill="#64748b"/>
    <!-- mist head / nozzle ring -->
    <ellipse cx="60" cy="28" rx="18" ry="5" fill="#94a3b8"/>
    <ellipse cx="60" cy="26" rx="14" ry="4" fill="#cbd5e1"/>
    <!-- mist droplets spray -->
    <circle cx="38" cy="20" r="2.5" fill="#bae6fd" opacity="0.85"/>
    <circle cx="44" cy="15" r="2"   fill="#7dd3fc" opacity="0.75"/>
    <circle cx="50" cy="12" r="1.5" fill="#38bdf8" opacity="0.7"/>
    <circle cx="58" cy="11" r="2"   fill="#bae6fd" opacity="0.8"/>
    <circle cx="66" cy="13" r="1.5" fill="#7dd3fc" opacity="0.7"/>
    <circle cx="72" cy="17" r="2"   fill="#38bdf8" opacity="0.75"/>
    <circle cx="79" cy="21" r="2.5" fill="#bae6fd" opacity="0.8"/>
    <!-- second mist row -->
    <circle cx="42" cy="30" r="1.5" fill="#e0f2fe" opacity="0.6"/>
    <circle cx="54" cy="22" r="1.5" fill="#e0f2fe" opacity="0.6"/>
    <circle cx="70" cy="24" r="1.5" fill="#e0f2fe" opacity="0.6"/>
    <circle cx="80" cy="30" r="1.5" fill="#e0f2fe" opacity="0.6"/>
    <!-- person -->
    <circle cx="60" cy="52" r="5" fill="#78716c" opacity="0.55"/>
    <rect x="57" y="57" width="6" height="10" rx="2" fill="#78716c" opacity="0.55"/>
  </svg>`,

  // ── Permeable Paving ───────────────────────────────────────────────────────
  permeable_paving: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 120 80" aria-hidden="true">
    <rect width="120" height="80" rx="8" fill="#fafaf9"/>
    <!-- paving surface (top view) -->
    <rect x="10" y="30" width="100" height="40" rx="4" fill="#d6d3d1"/>
    <!-- paving grid pattern -->
    <rect x="10" y="30" width="24" height="18" rx="1" fill="#e7e5e4" stroke="#a8a29e" stroke-width="0.5"/>
    <rect x="36" y="30" width="24" height="18" rx="1" fill="#d6d3d1" stroke="#a8a29e" stroke-width="0.5"/>
    <rect x="62" y="30" width="24" height="18" rx="1" fill="#e7e5e4" stroke="#a8a29e" stroke-width="0.5"/>
    <rect x="88" y="30" width="22" height="18" rx="1" fill="#d6d3d1" stroke="#a8a29e" stroke-width="0.5"/>
    <rect x="10" y="50" width="24" height="20" rx="1" fill="#d6d3d1" stroke="#a8a29e" stroke-width="0.5"/>
    <rect x="36" y="50" width="24" height="20" rx="1" fill="#e7e5e4" stroke="#a8a29e" stroke-width="0.5"/>
    <rect x="62" y="50" width="24" height="20" rx="1" fill="#d6d3d1" stroke="#a8a29e" stroke-width="0.5"/>
    <rect x="88" y="50" width="22" height="20" rx="1" fill="#e7e5e4" stroke="#a8a29e" stroke-width="0.5"/>
    <!-- water percolating down arrows -->
    <path d="M22 54 L22 66 M19 63 L22 66 L25 63" stroke="#38bdf8" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" fill="none"/>
    <path d="M48 52 L48 64 M45 61 L48 64 L51 61" stroke="#38bdf8" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" fill="none"/>
    <path d="M74 54 L74 66 M71 63 L74 66 L77 63" stroke="#38bdf8" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" fill="none"/>
    <!-- rain drops above -->
    <circle cx="30" cy="16" r="2" fill="#7dd3fc" opacity="0.8"/>
    <circle cx="50" cy="12" r="2" fill="#7dd3fc" opacity="0.8"/>
    <circle cx="70" cy="16" r="2" fill="#7dd3fc" opacity="0.8"/>
    <circle cx="90" cy="12" r="2" fill="#7dd3fc" opacity="0.8"/>
    <line x1="30" y1="18" x2="30" y2="25" stroke="#7dd3fc" stroke-width="1.5" stroke-linecap="round"/>
    <line x1="50" y1="14" x2="50" y2="25" stroke="#7dd3fc" stroke-width="1.5" stroke-linecap="round"/>
    <line x1="70" y1="18" x2="70" y2="25" stroke="#7dd3fc" stroke-width="1.5" stroke-linecap="round"/>
    <line x1="90" y1="14" x2="90" y2="25" stroke="#7dd3fc" stroke-width="1.5" stroke-linecap="round"/>
  </svg>`,

  // ── Rooftop Garden ─────────────────────────────────────────────────────────
  rooftop_garden: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 120 80" aria-hidden="true">
    <rect width="120" height="80" rx="8" fill="#f0f7f1"/>
    <!-- building body -->
    <rect x="15" y="44" width="90" height="30" rx="4" fill="#cbd5e1"/>
    <!-- rooftop surface -->
    <rect x="15" y="36" width="90" height="12" rx="3" fill="#a16207"/>
    <!-- soil layer -->
    <rect x="20" y="34" width="80" height="8" rx="2" fill="#92400e"/>
    <!-- grass layer -->
    <rect x="20" y="30" width="80" height="6" rx="2" fill="#4ade80" opacity="0.7"/>
    <!-- plants / bushes -->
    <ellipse cx="32" cy="26" rx="10" ry="9" fill="#2d5a40"/>
    <ellipse cx="32" cy="23" rx="7" ry="7" fill="#3d7a55"/>
    <ellipse cx="60" cy="22" rx="12" ry="10" fill="#1a3a2a"/>
    <ellipse cx="60" cy="19" rx="9" ry="8" fill="#2d5a40"/>
    <ellipse cx="60" cy="16" rx="6" ry="6" fill="#3d7a55"/>
    <ellipse cx="88" cy="26" rx="10" ry="9" fill="#2d5a40"/>
    <ellipse cx="88" cy="23" rx="7" ry="7" fill="#3d7a55"/>
    <!-- small flowers -->
    <circle cx="45" cy="28" r="2" fill="#fbbf24"/>
    <circle cx="75" cy="28" r="2" fill="#f97316"/>
    <!-- windows -->
    <rect x="30" y="50" width="14" height="10" rx="2" fill="#93c5fd" opacity="0.7"/>
    <rect x="76" y="50" width="14" height="10" rx="2" fill="#93c5fd" opacity="0.7"/>
    <!-- door -->
    <rect x="51" y="56" width="18" height="18" rx="2" fill="#64748b"/>
  </svg>`,

  // ── Urban Park ─────────────────────────────────────────────────────────────
  urban_park: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 120 80" aria-hidden="true">
    <rect width="120" height="80" rx="8" fill="#f0fdf4"/>
    <!-- grass base -->
    <ellipse cx="60" cy="68" rx="55" ry="14" fill="#bbf7d0" opacity="0.7"/>
    <!-- path -->
    <path d="M20 72 Q60 58 100 72" stroke="#d6d3d1" stroke-width="6" fill="none" stroke-linecap="round"/>
    <!-- big tree left -->
    <rect x="20" y="44" width="6" height="26" rx="2" fill="#78350f"/>
    <ellipse cx="23" cy="36" rx="16" ry="18" fill="#15803d"/>
    <ellipse cx="23" cy="30" rx="11" ry="13" fill="#16a34a"/>
    <!-- big tree right -->
    <rect x="94" y="44" width="6" height="26" rx="2" fill="#78350f"/>
    <ellipse cx="97" cy="36" rx="16" ry="18" fill="#15803d"/>
    <ellipse cx="97" cy="30" rx="11" ry="13" fill="#16a34a"/>
    <!-- centre feature tree -->
    <rect x="57" y="38" width="6" height="32" rx="2" fill="#78350f"/>
    <ellipse cx="60" cy="28" rx="18" ry="20" fill="#14532d"/>
    <ellipse cx="60" cy="22" rx="13" ry="14" fill="#15803d"/>
    <ellipse cx="60" cy="16" rx="8" ry="9" fill="#16a34a"/>
    <!-- bench -->
    <rect x="44" y="62" width="16" height="3" rx="1" fill="#92400e"/>
    <rect x="46" y="65" width="2" height="5" rx="1" fill="#78350f"/>
    <rect x="56" y="65" width="2" height="5" rx="1" fill="#78350f"/>
    <!-- flowers -->
    <circle cx="36" cy="66" r="2.5" fill="#fde68a"/>
    <circle cx="82" cy="66" r="2.5" fill="#fca5a5"/>
    <!-- sun -->
    <circle cx="106" cy="10" r="7" fill="#fbbf24" opacity="0.65"/>
  </svg>`,

  // ── Cool Pavement ──────────────────────────────────────────────────────────
  cool_pavement: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 120 80" aria-hidden="true">
    <rect width="120" height="80" rx="8" fill="#f8fafc"/>
    <!-- road surface -->
    <rect x="10" y="28" width="100" height="44" rx="6" fill="#94a3b8"/>
    <!-- reflective coating highlight -->
    <rect x="10" y="28" width="100" height="10" rx="6" fill="#f1f5f9" opacity="0.85"/>
    <!-- road markings -->
    <rect x="54" y="36" width="12" height="6" rx="1" fill="white" opacity="0.7"/>
    <rect x="54" y="48" width="12" height="6" rx="1" fill="white" opacity="0.7"/>
    <rect x="54" y="60" width="12" height="6" rx="1" fill="white" opacity="0.7"/>
    <!-- sun high above -->
    <circle cx="60" cy="10" r="8" fill="#fbbf24" opacity="0.7"/>
    <!-- reflection glare off road -->
    <ellipse cx="40" cy="31" rx="8" ry="3" fill="white" opacity="0.5" transform="rotate(-10,40,31)"/>
    <ellipse cx="80" cy="31" rx="8" ry="3" fill="white" opacity="0.5" transform="rotate(10,80,31)"/>
    <!-- temperature arrows showing drop -->
    <path d="M100 18 L108 10 M105 10 L108 10 L108 13" stroke="#16a34a" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" fill="none"/>
    <text x="86" y="22" font-size="8" fill="#16a34a" font-family="sans-serif" font-weight="bold">-8°C</text>
  </svg>`,

  // ── Water Body ─────────────────────────────────────────────────────────────
  water_body: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 120 80" aria-hidden="true">
    <rect width="120" height="80" rx="8" fill="#f0f9ff"/>
    <!-- grass surround -->
    <ellipse cx="60" cy="58" rx="52" ry="20" fill="#bbf7d0" opacity="0.6"/>
    <!-- pond base -->
    <ellipse cx="60" cy="54" rx="40" ry="16" fill="#0ea5e9"/>
    <!-- water shimmer -->
    <ellipse cx="60" cy="52" rx="36" ry="13" fill="#38bdf8"/>
    <ellipse cx="52" cy="50" rx="10" ry="4"  fill="#7dd3fc" opacity="0.5"/>
    <ellipse cx="70" cy="52" rx="8"  ry="3"  fill="#7dd3fc" opacity="0.4"/>
    <!-- water ripples -->
    <ellipse cx="60" cy="54" rx="18" ry="6" fill="none" stroke="#bae6fd" stroke-width="1" opacity="0.7"/>
    <ellipse cx="60" cy="54" rx="28" ry="10" fill="none" stroke="#bae6fd" stroke-width="0.8" opacity="0.5"/>
    <!-- fountain jet -->
    <line x1="60" y1="54" x2="60" y2="30" stroke="#7dd3fc" stroke-width="2.5" stroke-linecap="round"/>
    <!-- fountain spray droplets -->
    <circle cx="60" cy="28" r="3"  fill="#bae6fd"/>
    <circle cx="52" cy="34" r="2"  fill="#7dd3fc" opacity="0.8"/>
    <circle cx="68" cy="34" r="2"  fill="#7dd3fc" opacity="0.8"/>
    <circle cx="56" cy="31" r="1.5" fill="#e0f2fe" opacity="0.9"/>
    <circle cx="64" cy="31" r="1.5" fill="#e0f2fe" opacity="0.9"/>
    <!-- reeds / plants at edge -->
    <line x1="24" y1="60" x2="22" y2="40" stroke="#4ade80" stroke-width="2" stroke-linecap="round"/>
    <ellipse cx="22" cy="38" rx="4" ry="6" fill="#166534" opacity="0.7"/>
    <line x1="96" y1="60" x2="98" y2="40" stroke="#4ade80" stroke-width="2" stroke-linecap="round"/>
    <ellipse cx="98" cy="38" rx="4" ry="6" fill="#166534" opacity="0.7"/>
    <!-- bird -->
    <path d="M85 18 Q88 15 91 18" stroke="#64748b" stroke-width="1.5" fill="none" stroke-linecap="round"/>
    <path d="M95 16 Q98 13 101 16" stroke="#64748b" stroke-width="1.5" fill="none" stroke-linecap="round"/>
  </svg>`,
}

export default ILLUSTRATIONS
