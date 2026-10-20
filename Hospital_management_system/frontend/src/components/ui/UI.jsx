export function Spinner({ text = 'Loading data…' }) {
  return (
    <div className="spinner-wrap">
      <div className="spinner" />
      <span className="spinner-text">{text}</span>
    </div>
  )
}

export function ErrorBanner({ message }) {
  return (
    <div className="error-banner">
      ⚠ {message || 'Something went wrong. Please try again.'}
    </div>
  )
}

export function KPICard({ icon, label, value, sub, color = 'var(--teal)', bgColor = 'var(--teal-glow)', delay = 0 }) {
  return (
    <div className={`kpi-card fade-up`} style={{ animationDelay: `${delay}s` }}>
      <div className="kpi-header">
        <span className="kpi-label">{label}</span>
        <div className="kpi-icon" style={{ background: bgColor }}>{icon}</div>
      </div>
      <div className="kpi-value" style={{ color }}>{value}</div>
      {sub && <div className="kpi-trend">{sub}</div>}
    </div>
  )
}

export function OccBar({ pct, color = 'var(--teal)' }) {
  const clr = pct > 80 ? 'var(--rose)' : pct > 60 ? 'var(--amber)' : color
  return (
    <div className="occ-bar-wrap">
      <div className="occ-bar" style={{ width: `${Math.min(pct, 100)}%`, background: clr }} />
    </div>
  )
}

export function BreakdownBar({ label, count, pct, color }) {
  return (
    <div className="breakdown-row">
      <span className="breakdown-label">{label}</span>
      <div className="breakdown-bar-wrap">
        <div className="breakdown-bar" style={{ width: `${pct}%`, background: color }} />
      </div>
      <span className="breakdown-count">{count.toLocaleString()}</span>
      <span className="breakdown-pct">{pct}%</span>
    </div>
  )
}
