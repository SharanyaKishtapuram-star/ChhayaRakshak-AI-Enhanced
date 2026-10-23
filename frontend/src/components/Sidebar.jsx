/**
 * Sidebar.jsx — Fixed vertical navigation sidebar
 *
 * Desktop (md+): always-visible 240 px wide sidebar, collapsible to 64 px icon-only mode.
 * Mobile (<md):  hidden by default, slides in as a full-height drawer when the hamburger
 *               button (rendered in the top bar) is tapped.
 *
 * Receives:
 *   collapsed   {boolean}  — icon-only mode (desktop)
 *   onCollapse  {fn}       — toggle collapsed state
 *   mobileOpen  {boolean}  — drawer open (mobile)
 *   onMobileClose {fn}     — close drawer
 *
 * All routing uses React Router <Link> / useLocation — no logic changed.
 */

import { Link, useLocation } from 'react-router-dom'

const NAV_ITEMS = [
  { to: '/',               label: 'Dashboard',       icon: DashboardIcon  },
  { to: '/heat-risk',      label: 'Heat Risk',        icon: HeatIcon       },
  { to: '/shade',          label: 'Shade Detection',  icon: ShadeIcon      },
  { to: '/map',            label: 'Vulnerability Map',icon: MapIcon        },
  { to: '/budget',         label: 'Budget Optimizer', icon: BudgetIcon     },
  { to: '/assistant',      label: 'AI Assistant',     icon: AssistantIcon  },
  { to: '/health-profile', label: 'Health Profile',   icon: HealthIcon     },
]

// ── Inline SVG icons (no external deps) ────────────────────────────────────────
function DashboardIcon({ className }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <rect x="3" y="3" width="7" height="7" rx="1.5"/>
      <rect x="14" y="3" width="7" height="7" rx="1.5"/>
      <rect x="3" y="14" width="7" height="7" rx="1.5"/>
      <rect x="14" y="14" width="7" height="7" rx="1.5"/>
    </svg>
  )
}
function HeatIcon({ className }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M4.93 19.07l1.41-1.41M17.66 6.34l1.41-1.41"/>
      <circle cx="12" cy="12" r="4"/>
    </svg>
  )
}
function ShadeIcon({ className }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M3 17l9-14 9 14H3z"/>
      <line x1="12" y1="17" x2="12" y2="21"/>
    </svg>
  )
}
function MapIcon({ className }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <polygon points="1 6 1 22 8 18 16 22 23 18 23 2 16 6 8 2 1 6"/>
      <line x1="8" y1="2" x2="8" y2="18"/>
      <line x1="16" y1="6" x2="16" y2="22"/>
    </svg>
  )
}
function BudgetIcon({ className }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <line x1="12" y1="1" x2="12" y2="23"/>
      <path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/>
    </svg>
  )
}
function AssistantIcon({ className }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
    </svg>
  )
}
function HealthIcon({ className }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"/>
    </svg>
  )
}
function CollapseIcon({ className }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <line x1="3" y1="12" x2="21" y2="12"/>
      <line x1="3" y1="6" x2="21" y2="6"/>
      <line x1="3" y1="18" x2="21" y2="18"/>
    </svg>
  )
}
function ChevronLeftIcon({ className }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="15 18 9 12 15 6"/>
    </svg>
  )
}

// ── Individual nav link ──────────────────────────────────────────────────────
function NavLink({ item, collapsed, onClick }) {
  const { pathname } = useLocation()
  // Exact match for root (/), prefix match for others
  const active = item.to === '/' ? pathname === '/' : pathname.startsWith(item.to)
  const Icon = item.icon

  return (
    <Link
      to={item.to}
      onClick={onClick}
      title={collapsed ? item.label : undefined}
      aria-current={active ? 'page' : undefined}
      className={`
        group relative flex items-center gap-3 rounded-xl px-3 py-2.5
        text-sm font-medium transition-all duration-150 focus:outline-none
        focus-visible:ring-2 focus-visible:ring-sage focus-visible:ring-offset-1 focus-visible:ring-offset-primary-dark
        ${active
          ? 'bg-white/15 text-white shadow-sm'
          : 'text-sage-light/80 hover:bg-white/10 hover:text-white'
        }
        ${collapsed ? 'justify-center px-2' : ''}
      `}
    >
      {/* Active indicator bar */}
      {active && (
        <span className="absolute left-0 top-1/2 -translate-y-1/2 w-0.5 h-5 bg-accent rounded-r-full" />
      )}

      <Icon className={`flex-shrink-0 transition-colors duration-150 ${collapsed ? 'w-5 h-5' : 'w-4.5 h-4.5'} w-[18px] h-[18px]`} />

      {!collapsed && (
        <span className="truncate">{item.label}</span>
      )}

      {/* Tooltip when collapsed */}
      {collapsed && (
        <span className="
          pointer-events-none absolute left-full ml-2 z-50
          whitespace-nowrap rounded-lg bg-gray-900 px-2.5 py-1.5
          text-xs font-medium text-white shadow-lg
          opacity-0 translate-x-1 group-hover:opacity-100 group-hover:translate-x-0
          transition-all duration-150
        ">
          {item.label}
        </span>
      )}
    </Link>
  )
}

// ── Sidebar component ────────────────────────────────────────────────────────
export default function Sidebar({ collapsed, onCollapse, mobileOpen, onMobileClose }) {
  const sidebarContent = (
    <div className="flex flex-col h-full">

      {/* Logo / brand area */}
      <div className={`flex items-center gap-2.5 px-4 py-5 border-b border-white/10 flex-shrink-0 ${collapsed ? 'justify-center px-2' : ''}`}>
        <div className="w-8 h-8 rounded-lg bg-sage/20 border border-sage/30 flex items-center justify-center text-lg flex-shrink-0">
          🌿
        </div>
        {!collapsed && (
          <div className="min-w-0">
            <div className="text-white font-bold text-sm leading-tight tracking-tight truncate">ChhayaRakshak</div>
            <div className="text-sage-light/60 text-[10px] font-medium truncate">Urban Heat Protection</div>
          </div>
        )}
      </div>

      {/* Nav items */}
      <nav className="flex-1 overflow-y-auto px-2 py-4 space-y-0.5" aria-label="Main navigation">
        {NAV_ITEMS.map(item => (
          <NavLink
            key={item.to}
            item={item}
            collapsed={collapsed}
            onClick={onMobileClose}
          />
        ))}
      </nav>

      {/* Collapse toggle (desktop only) */}
      <div className="px-2 pb-4 border-t border-white/10 pt-3 flex-shrink-0">
        <button
          onClick={onCollapse}
          title={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          className="
            w-full flex items-center gap-2.5 rounded-xl px-3 py-2.5
            text-sage-light/60 hover:text-white hover:bg-white/10
            text-xs font-medium transition-all duration-150
            focus:outline-none focus-visible:ring-2 focus-visible:ring-sage
            focus-visible:ring-offset-1 focus-visible:ring-offset-primary-dark
            hidden md:flex
          "
        >
          <ChevronLeftIcon className={`w-4 h-4 flex-shrink-0 transition-transform duration-200 ${collapsed ? 'rotate-180' : ''}`} />
          {!collapsed && <span>Collapse</span>}
        </button>
      </div>
    </div>
  )

  return (
    <>
      {/* ── Desktop sidebar ─────────────────────────────────────────────────── */}
      <aside
        className={`
          hidden md:flex flex-col fixed left-0 top-0 h-screen z-40
          bg-gradient-to-b from-primary-dark via-primary to-primary-light
          border-r border-white/10 shadow-xl
          transition-all duration-200 ease-in-out
          ${collapsed ? 'w-16' : 'w-60'}
        `}
        aria-label="Sidebar"
      >
        {sidebarContent}
      </aside>

      {/* ── Mobile drawer overlay ────────────────────────────────────────────── */}
      {mobileOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/50 md:hidden"
          onClick={onMobileClose}
          aria-hidden="true"
        />
      )}

      {/* ── Mobile drawer ────────────────────────────────────────────────────── */}
      <aside
        className={`
          fixed left-0 top-0 h-screen z-50 w-64
          bg-gradient-to-b from-primary-dark via-primary to-primary-light
          border-r border-white/10 shadow-2xl
          transition-transform duration-250 ease-in-out md:hidden
          ${mobileOpen ? 'translate-x-0' : '-translate-x-full'}
        `}
        aria-label="Mobile navigation"
      >
        {/* Mobile close button */}
        <button
          onClick={onMobileClose}
          className="absolute top-4 right-4 w-7 h-7 rounded-full bg-white/10 hover:bg-white/20 flex items-center justify-center text-white/70 hover:text-white transition-colors"
          aria-label="Close navigation"
        >
          <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
            <line x1="18" y1="6" x2="6" y2="18"/>
            <line x1="6" y1="6" x2="18" y2="18"/>
          </svg>
        </button>
        {sidebarContent}
      </aside>
    </>
  )
}

// ── Mobile top bar (hamburger + breadcrumb) ──────────────────────────────────
// Exported separately so App.jsx can place it at the top of the content area.
export function MobileTopBar({ onMenuOpen }) {
  const { pathname } = useLocation()
  const current = NAV_ITEMS.find(item =>
    item.to === '/' ? pathname === '/' : pathname.startsWith(item.to)
  )

  return (
    <header className="
      md:hidden sticky top-0 z-30 flex items-center gap-3 px-4 py-3
      bg-white/95 backdrop-blur border-b border-sage-light/40 shadow-sm
    ">
      <button
        onClick={onMenuOpen}
        aria-label="Open navigation menu"
        className="
          w-9 h-9 rounded-xl bg-primary/8 hover:bg-primary/15 flex items-center justify-center
          text-primary transition-colors focus:outline-none
          focus-visible:ring-2 focus-visible:ring-sage
        "
      >
        <CollapseIcon className="w-5 h-5" />
      </button>
      <div className="flex items-center gap-2">
        <span className="text-lg">{current ? '🌿' : '🌿'}</span>
        <span className="font-bold text-primary text-sm">
          {current?.label ?? 'ChhayaRakshak AI'}
        </span>
      </div>
    </header>
  )
}
