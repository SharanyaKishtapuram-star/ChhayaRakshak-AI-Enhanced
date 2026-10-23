import { useState } from 'react'
import { Link, useLocation } from 'react-router-dom'

const navLinks = [
  { to: '/heat-risk',      label: 'Heat Risk',        icon: '🌡️' },
  { to: '/shade',          label: 'Shade Detection',  icon: '🌿' },
  { to: '/map',            label: 'Vulnerability Map',icon: '🗺️' },
  { to: '/budget',         label: 'Budget Optimizer', icon: '💰' },
  { to: '/assistant',      label: 'AI Assistant',     icon: '🤖' },
  { to: '/health-profile', label: 'Health Profile',   icon: '🏥' },
]

export default function Navbar() {
  const { pathname } = useLocation()
  const [menuOpen, setMenuOpen] = useState(false)

  return (
    <nav className="bg-gradient-to-r from-primary-dark via-primary to-primary-light shadow-lg sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6">
        <div className="flex items-center justify-between h-16">

          {/* Brand */}
          <Link
            to="/"
            className="flex items-center gap-2.5 group flex-shrink-0"
            onClick={() => setMenuOpen(false)}
          >
            <div className="w-8 h-8 rounded-lg bg-sage/20 border border-sage/30 flex items-center justify-center text-lg group-hover:bg-sage/30 transition-colors">
              🌿
            </div>
            <div>
              <span className="text-white font-bold text-base tracking-tight">ChhayaRakshak</span>
              <span className="text-sage-light font-medium text-base ml-1">AI</span>
            </div>
          </Link>

          {/* Desktop links */}
          <div className="hidden md:flex items-center gap-1">
            {navLinks.map(({ to, label, icon }) => {
              const active = pathname === to
              return (
                <Link
                  key={to}
                  to={to}
                  className={`flex items-center gap-1.5 px-3 py-2 rounded-lg text-sm font-medium transition-all duration-150
                    ${active
                      ? 'bg-white/15 text-white border border-white/20'
                      : 'text-sage-light hover:text-white hover:bg-white/10'
                    }`}
                >
                  <span className="text-base leading-none">{icon}</span>
                  <span>{label}</span>
                </Link>
              )
            })}
          </div>

          {/* Mobile hamburger */}
          <button
            className="md:hidden p-2 rounded-lg text-sage-light hover:text-white hover:bg-white/10 transition-colors"
            onClick={() => setMenuOpen(o => !o)}
            aria-label="Toggle menu"
          >
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              {menuOpen
                ? <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                : <path strokeLinecap="round" strokeLinejoin="round" d="M4 6h16M4 12h16M4 18h16" />
              }
            </svg>
          </button>
        </div>
      </div>

      {/* Mobile dropdown */}
      {menuOpen && (
        <div className="md:hidden border-t border-white/10 bg-primary-dark/95 animate-fade-in">
          <div className="px-3 py-2 space-y-0.5">
            {navLinks.map(({ to, label, icon }) => {
              const active = pathname === to
              return (
                <Link
                  key={to}
                  to={to}
                  onClick={() => setMenuOpen(false)}
                  className={`flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium transition-all duration-150
                    ${active
                      ? 'bg-white/15 text-white'
                      : 'text-sage-light hover:text-white hover:bg-white/10'
                    }`}
                >
                  <span className="text-lg">{icon}</span>
                  <span>{label}</span>
                </Link>
              )
            })}
          </div>
        </div>
      )}
    </nav>
  )
}
