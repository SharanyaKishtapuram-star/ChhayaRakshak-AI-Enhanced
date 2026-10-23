import { useState } from 'react'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import Sidebar, { MobileTopBar } from './components/Sidebar'
import Home from './pages/Home'
import HeatRisk from './pages/HeatRisk'
import ShadeDetection from './pages/ShadeDetection'
import VulnerabilityMap from './pages/VulnerabilityMap'
import BudgetOptimizer from './pages/BudgetOptimizer'
import Assistant from './pages/Assistant'
import HealthProfile from './pages/HealthProfile'

export default function App() {
  const [collapsed, setCollapsed]     = useState(false)
  const [mobileOpen, setMobileOpen]   = useState(false)

  // Sidebar width as a CSS value — used to offset main content on desktop
  const sidebarW = collapsed ? '4rem' : '15rem'  // 64px / 240px

  return (
    <BrowserRouter>
      {/* ── Sidebar ─────────────────────────────────────────────────────────── */}
      <Sidebar
        collapsed={collapsed}
        onCollapse={() => setCollapsed(c => !c)}
        mobileOpen={mobileOpen}
        onMobileClose={() => setMobileOpen(false)}
      />

      {/* ── Main content area ─────────────────────────────────────────────── */}
      {/*
        On desktop (md+): offset left margin to clear the sidebar.
        On mobile: full width (sidebar is a drawer overlay).
        Transition matches sidebar animation duration.
      */}
      <div
        className="flex flex-col min-h-screen bg-cream transition-all duration-200"
        style={{ marginLeft: `var(--sidebar-w, 0)` }}
      >
        {/* Inject sidebar width CSS variable for desktop */}
        <style>{`@media (min-width: 768px) { :root { --sidebar-w: ${sidebarW}; } }`}</style>

        {/* Mobile top bar (hamburger + page title) */}
        <MobileTopBar onMenuOpen={() => setMobileOpen(true)} />

        {/* Page content */}
        <main className="flex-1">
          <Routes>
            <Route path="/"              element={<Home />} />
            <Route path="/heat-risk"     element={<HeatRisk />} />
            <Route path="/shade"         element={<ShadeDetection />} />
            <Route path="/map"           element={<VulnerabilityMap />} />
            <Route path="/budget"        element={<BudgetOptimizer />} />
            <Route path="/assistant"     element={<Assistant />} />
            <Route path="/health-profile" element={<HealthProfile />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  )
}
