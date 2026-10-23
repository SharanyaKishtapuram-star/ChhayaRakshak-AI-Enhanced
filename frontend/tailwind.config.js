/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // ChhayaRakshak premium eco-tech palette
        primary:   "#1a3a2a",   // deep forest green
        "primary-light": "#2d5a40",  // mid forest green
        "primary-dark":  "#0f2018",  // darkest green
        accent:    "#e8621a",   // heat/fire orange
        "accent-light":  "#f97316",  // warm orange
        "accent-soft":   "#fff4ed",  // very light orange tint
        sage:      "#7fb685",   // sage green
        "sage-light":    "#b8d9bd",  // light sage
        "sage-soft":     "#f0f7f1",  // sage background tint
        cream:     "#faf7f2",   // warm cream
        "cream-dark":    "#f5efe6",  // deeper cream
        forest:    "#2d5a40",   // forest green alias
        // Risk level semantic colours (unchanged — used in multiple places)
        risk: {
          low:      "#16a34a",
          moderate: "#ca8a04",
          high:     "#ea580c",
          extreme:  "#dc2626",
        },
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "-apple-system", "sans-serif"],
      },
      borderRadius: {
        "2xl": "1rem",
        "3xl": "1.5rem",
      },
      boxShadow: {
        "card":    "0 1px 3px 0 rgba(26,58,42,0.08), 0 1px 2px -1px rgba(26,58,42,0.05)",
        "card-md": "0 4px 12px -1px rgba(26,58,42,0.10), 0 2px 6px -2px rgba(26,58,42,0.06)",
        "card-lg": "0 10px 30px -3px rgba(26,58,42,0.12), 0 4px 12px -4px rgba(26,58,42,0.08)",
        "glow":    "0 0 20px rgba(127,182,133,0.25)",
        "inner-sm":"inset 0 1px 2px rgba(26,58,42,0.06)",
      },
      backgroundImage: {
        "hero-gradient":   "linear-gradient(135deg, #1a3a2a 0%, #2d5a40 40%, #1a4a2e 70%, #0f2018 100%)",
        "card-gradient":   "linear-gradient(135deg, #ffffff 0%, #f0f7f1 100%)",
        "sage-gradient":   "linear-gradient(135deg, #f0f7f1 0%, #e8f3ea 100%)",
        "cream-gradient":  "linear-gradient(135deg, #faf7f2 0%, #f5efe6 100%)",
        "risk-gradient":   "linear-gradient(90deg, #16a34a 0%, #ca8a04 40%, #ea580c 70%, #dc2626 100%)",
        "accent-gradient": "linear-gradient(135deg, #e8621a 0%, #f97316 100%)",
        "forest-gradient": "linear-gradient(135deg, #1a3a2a 0%, #2d5a40 100%)",
      },
      animation: {
        "fade-in":    "fadeIn 0.4s ease-out",
        "slide-up":   "slideUp 0.4s ease-out",
        "slide-in":   "slideIn 0.3s ease-out",
        "pulse-slow": "pulse 3s cubic-bezier(0.4,0,0.6,1) infinite",
        "float":      "float 3s ease-in-out infinite",
        "bar-grow":   "barGrow 0.8s ease-out forwards",
      },
      keyframes: {
        fadeIn:  { "0%": { opacity: "0" },                      "100%": { opacity: "1" } },
        slideUp: { "0%": { opacity: "0", transform: "translateY(12px)" }, "100%": { opacity: "1", transform: "translateY(0)" } },
        slideIn: { "0%": { opacity: "0", transform: "translateX(-8px)" }, "100%": { opacity: "1", transform: "translateX(0)" } },
        float:   { "0%,100%": { transform: "translateY(0px)" }, "50%": { transform: "translateY(-6px)" } },
        barGrow: { "0%": { width: "0%" }, "100%": { width: "var(--bar-width)" } },
      },
      transitionTimingFunction: {
        "spring": "cubic-bezier(0.34, 1.56, 0.64, 1)",
      },
    },
  },
  plugins: [],
}
