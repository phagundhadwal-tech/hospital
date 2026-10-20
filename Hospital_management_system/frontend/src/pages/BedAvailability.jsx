import { useState, useEffect, useCallback, useRef } from 'react'
import { BedDouble, CheckCircle, Wrench, Clock } from 'lucide-react'
import { analyticsApi, isCancelled, describeError } from '../api/client'
import { useAuth, BED_AVAIL_ROLES } from '../contexts/AuthContext'
import { KPICard, Spinner, ErrorBanner, OccBar, BreakdownBar } from '../components/ui/UI'
import AccessDenied from './AccessDenied'

const STATUS_COLORS = {
  Occupied:    'var(--rose)',
  Available:   'var(--emerald)',
  Maintenance: 'var(--amber)',
  Reserved:    'var(--violet)',
}

export default function BedAvailability() {
  const { user } = useAuth()
  if (!BED_AVAIL_ROLES.has(user?.role)) return <AccessDenied />
  return <BedAvailabilityContent user={user} />
}

function BedAvailabilityContent({ user }) {
  const [data,    setData]    = useState(null)
  const [loading, setLoading] = useState(true)
  const [error,   setError]   = useState('')
  const [typeFilter, setTypeFilter] = useState('')

  const abortRef = useRef(null)

  const load = useCallback(async () => {
    abortRef.current?.abort()
    const ctl = new AbortController()
    abortRef.current = ctl
    setLoading(true); setError('')
    try {
      const r = await analyticsApi.bedAvailability({}, ctl.signal)
      if (ctl.signal.aborted) return
      setData(r.data)
      setLoading(false)
    } catch (e) {
      if (isCancelled(e)) return
      setData(null)
      setError(describeError(e, 'Failed to load bed data.'))
      setLoading(false)
    }
  }, [])

  useEffect(() => { load(); return () => abortRef.current?.abort() }, [load])

  const visibleWards = data?.ward_occupancy?.filter(w =>
    !typeFilter || w.ward_type === typeFilter
  ) ?? []

  const wardTypes = [...new Set(data?.ward_occupancy?.map(w => w.ward_type) ?? [])]

  return (
    <div className="page-content">
      <div className="page-header fade-up">
        <h1 className="page-title">Bed Availability</h1>
        <p className="page-desc">
          Live bed snapshot {user?.department_name ? `· ${user.department_name}` : '· All Departments'}
        </p>
      </div>

      {error   && <ErrorBanner message={error} />}
      {loading && <Spinner />}

      {!loading && data && (
        <>
          {/* KPI Cards */}
          <div className="kpi-grid">
            <KPICard delay={0.00} label="Total Beds"   value={data.total_beds}
              icon={<BedDouble size={16} />}  color="var(--teal)"    bgColor="var(--teal-glow)"
              sub={`${data.operational_beds} operational`} />
            <KPICard delay={0.05} label="Occupied"     value={data.occupied}
              icon={<BedDouble size={16} />}  color="var(--rose)"    bgColor="rgba(251,113,133,0.12)"
              sub={`${data.occupancy_pct}% of operational beds`} />
            <KPICard delay={0.10} label="Available"    value={data.available}
              icon={<CheckCircle size={16} />} color="var(--emerald)" bgColor="rgba(52,211,153,0.12)" />
            <KPICard delay={0.15} label="Maintenance"  value={data.maintenance}
              icon={<Wrench size={16} />}     color="var(--amber)"   bgColor="rgba(251,191,36,0.12)"
              sub="Excluded from occupancy" />
            <KPICard delay={0.20} label="Reserved"     value={data.reserved}
              icon={<Clock size={16} />}      color="var(--violet)"  bgColor="rgba(167,139,250,0.12)" />
          </div>

          {/* Status breakdown */}
          <div className="charts-grid" style={{ marginBottom: 28 }}>
            <div className="chart-card fade-up fade-up-3">
              <div className="chart-title"><BedDouble size={16} color="var(--teal)" /> Status Breakdown</div>
              <div className="breakdown-list" style={{ marginTop: 12 }}>
                {data.status_breakdown.map((item,i) => (
                  <BreakdownBar key={i} label={item.status} count={item.count}
                    pct={item.pct} color={STATUS_COLORS[item.status] || 'var(--teal)'} />
                ))}
              </div>
            </div>

            <div className="chart-card fade-up fade-up-4" style={{ display:'flex', flexDirection:'column', justifyContent:'center', gap:14 }}>
              <div className="chart-title"><BedDouble size={16} color="var(--violet)" /> Occupancy Gauge</div>
              <div style={{ textAlign:'center' }}>
                <div style={{ fontSize:'3.5rem', fontWeight:800, letterSpacing:'-0.04em',
                  color: data.occupancy_pct > 80 ? 'var(--rose)' : data.occupancy_pct > 60 ? 'var(--amber)' : 'var(--emerald)' }}>
                  {data.occupancy_pct}%
                </div>
                <div style={{ color:'var(--text-muted)', fontSize:'0.8rem', marginTop:4 }}>Current bed occupancy</div>
              </div>
              <OccBar pct={data.occupancy_pct} />
              <div style={{ display:'flex', justifyContent:'space-between', fontSize:'0.72rem', color:'var(--text-dim)' }}>
                <span>{data.occupied} occupied</span>
                <span>{data.operational_beds} operational</span>
              </div>
            </div>
          </div>

          {/* Ward cards */}
          <div className="section-header fade-up">
            <h2 className="section-title">Ward Breakdown</h2>
            <div style={{ marginLeft:'auto', display:'flex', gap:8 }}>
              <select className="filter-select" value={typeFilter} onChange={e => setTypeFilter(e.target.value)}>
                <option value="">All Types</option>
                {wardTypes.map(t => <option key={t} value={t}>{t}</option>)}
              </select>
            </div>
          </div>

          {visibleWards.length === 0 && (
            <div className="empty-state">No wards match the selected filter.</div>
          )}
          <div className="ward-grid">
            {visibleWards.map((ward, i) => (
              <div key={ward.ward_id} className={`ward-card fade-up`} style={{ animationDelay: `${0.03*i}s` }}>
                <div className="ward-header">
                  <div>
                    <div className="ward-name">{ward.ward_name}</div>
                    <div style={{ fontSize:'0.7rem', color:'var(--text-dim)', marginTop:2 }}>{ward.department_name}</div>
                  </div>
                  <span className={`ward-type ${ward.ward_type}`}>{ward.ward_type}</span>
                </div>
                <OccBar pct={ward.occupancy_pct} />
                <div className="occ-stats">
                  <span>{ward.occupied}/{ward.operational_beds} occupied</span>
                  <span style={{ fontWeight:600, color: ward.occupancy_pct > 80 ? 'var(--rose)' : ward.occupancy_pct > 60 ? 'var(--amber)' : 'var(--emerald)' }}>
                    {ward.occupancy_pct.toFixed(0)}%
                  </span>
                </div>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  )
}
