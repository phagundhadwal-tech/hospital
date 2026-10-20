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

// Occupied / free / maintenance split of one ward or department. Reads fine when almost
// every bed is free, which a single occupancy % bar does not.
export function BedBar({ name, occupied, available, maintenance = 0 }) {
  const total = occupied + available + maintenance
  const seg = (n, color) => n > 0 && <div style={{ width: `${n / total * 100}%`, background: color }} />
  return (
    <div>
      <div className="occ-stats" style={{ marginBottom: 6 }}>
        <span style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{name}</span>
        <span>{occupied} occupied · {available} free{maintenance > 0 ? ` · ${maintenance} maintenance` : ''}</span>
      </div>
      <div style={{ display: 'flex', height: 10, borderRadius: 999, overflow: 'hidden', background: 'var(--border)' }}>
        {seg(occupied,    'var(--rose)')}
        {seg(available,   'var(--emerald)')}
        {seg(maintenance, 'var(--amber)')}
      </div>
    </div>
  )
}

export function BedLegend() {
  const dot = c => <span style={{ display: 'inline-block', width: 8, height: 8, borderRadius: 999, background: c, marginRight: 5 }} />
  return (
    <div style={{ display: 'flex', gap: 16, fontSize: '0.72rem', color: 'var(--text-muted)', marginTop: 14 }}>
      <span>{dot('var(--rose)')}Occupied</span>
      <span>{dot('var(--emerald)')}Free</span>
      <span>{dot('var(--amber)')}Maintenance</span>
    </div>
  )
}
