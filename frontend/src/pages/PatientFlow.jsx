import { useState, useEffect, useCallback, useRef } from 'react'
import {
  Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend,
  ResponsiveContainer, BarChart
} from 'recharts'
import { Activity, Users, TrendingUp, Clock, Filter, Stethoscope, BedDouble, XCircle } from 'lucide-react'
import { analyticsApi, isCancelled, describeError } from '../api/client'
import { useAuth, PATIENT_FLOW_ROLES, FULL_ACCESS_ROLES } from '../contexts/AuthContext'
import DateRangePicker from '../components/ui/DateRangePicker'
import { KPICard, Spinner, ErrorBanner, BreakdownBar } from '../components/ui/UI'
import AccessDenied from './AccessDenied'

const PIE_COLORS = { Inpatient:'#0284c7', Outpatient:'#059669', Emergency:'#e11d48' }
const STATUS_COLORS = ['#0284c7','#059669','#d97706','#e11d48','#7c3aed','#64748b']

export default function PatientFlow() {
  const { user } = useAuth()
  if (!PATIENT_FLOW_ROLES.has(user?.role)) return <AccessDenied />
  return <PatientFlowContent />
}

function PatientFlowContent() {
  const { user } = useAuth()
  const isDean = FULL_ACCESS_ROLES.has(user?.role)   // department comparison only makes sense across departments
  const [data,   setData]    = useState(null)
  const [loading, setLoading] = useState(true)
  const [error,   setError]   = useState('')
  const [startDate, setStartDate] = useState('')
  const [endDate,   setEndDate]   = useState('')
  const [dataRange, setDataRange]   = useState(null)   // days with data; the calendar greys out everything else

  const abortRef = useRef(null)

  const fetchData = useCallback(async () => {
    abortRef.current?.abort()                       // newer request replaces any older one
    const ctl = new AbortController()
    abortRef.current = ctl
    setLoading(true); setError('')
    try {
      const params = {}
      if (startDate) params.start_date = startDate
      if (endDate)   params.end_date   = endDate
      const res = await analyticsApi.patientFlow(params, ctl.signal)
      if (ctl.signal.aborted) return
      setData(res.data)
      setLoading(false)
    } catch (e) {
      if (isCancelled(e)) return
      setData(null)
      setError(describeError(e, 'Failed to load patient flow data.'))
      setLoading(false)
    }
  }, [startDate, endDate])

  useEffect(() => {
    const ctl = new AbortController()
    analyticsApi.dataRange(ctl.signal).then(r => setDataRange(r.data)).catch(() => {})   // cosmetic only
    return () => ctl.abort()
  }, [])

  useEffect(() => { fetchData(); return () => abortRef.current?.abort() }, [fetchData])

  const fmtMin   = m => m == null ? '—' : `${m} min`
  const fmtHours = h => h == null ? '—' : h >= 48 ? `${(h / 24).toFixed(1)} days` : `${h} h`
  const t = data?.timings
  const stages = t ? [
    { stage: 'Registration → Triage',  minutes: t.reg_to_triage_min,     n: t.reg_to_triage_n },
    { stage: 'Triage → Consultation',  minutes: t.triage_to_consult_min, n: t.triage_to_consult_n },
    { stage: 'Consultation length',    minutes: t.consultation_min,      n: t.consultation_n },
  ] : []
  const cancelled = data?.status_breakdown.find(s => s.status === 'Cancelled')?.count ?? 0

  return (
    <div className="page-content">
      <div className="page-header fade-up">
        <h1 className="page-title">Patient Flow Analytics</h1>
        <p className="page-desc">Visit patterns, wait times, and status breakdown</p>
      </div>

      <div className="filters-bar fade-up fade-up-1">
        <Filter size={14} color="var(--text-muted)" />
        <DateRangePicker start={startDate} end={endDate} allowClear placeholder="All dates"
          min={dataRange?.earliest} max={dataRange?.latest}
          onChange={(a, b) => { setStartDate(a); setEndDate(b) }} />
        <button className="btn-ghost" onClick={() => { setStartDate(''); setEndDate('') }}>Reset</button>
      </div>

      {error   && <ErrorBanner message={error} />}
      {loading && <Spinner />}

      {!loading && data && (
        <>
          {/* KPI summary */}
          <div className="kpi-grid">
            <KPICard delay={0.00} label="Total Visits"    value={data.total_visits.toLocaleString()} icon={<Users size={16} />}     color="var(--teal)"    bgColor="var(--teal-glow)" />
            <KPICard delay={0.05} label="Admissions"      value={data.admissions.toLocaleString()}   icon={<TrendingUp size={16} />} color="var(--emerald)" bgColor="rgba(52,211,153,0.12)" />
            <KPICard delay={0.10} label="Discharges"      value={data.discharges.toLocaleString()}   icon={<Activity size={16} />}  color="var(--violet)"  bgColor="rgba(167,139,250,0.12)" />
            <KPICard delay={0.15} label="Avg Wait Time"   value={data.avg_wait_minutes == null ? '—' : `${data.avg_wait_minutes} min`} icon={<Clock size={16} />}     color="var(--amber)"   bgColor="rgba(251,191,36,0.12)" />
          </div>
          <div className="kpi-grid kpi-grid-3">
            <KPICard delay={0.20} label="Avg Consultation" value={fmtMin(t.consultation_min)} icon={<Stethoscope size={16} />}
              color="var(--teal)" bgColor="var(--teal-glow)" sub={`Start to end · ${t.consultation_n.toLocaleString()} visits`} />
            <KPICard delay={0.25} label="Avg Length of Stay" value={fmtHours(t.avg_stay_hours)} icon={<BedDouble size={16} />}
              color="var(--emerald)" bgColor="rgba(52,211,153,0.12)" sub={`Admission to discharge · ${t.stay_n.toLocaleString()} stays`} />
            <KPICard delay={0.30} label="Cancelled Visits" value={cancelled.toLocaleString()} icon={<XCircle size={16} />}
              color="var(--rose)" bgColor="rgba(251,113,133,0.12)"
              sub={data.total_visits ? `${(cancelled / data.total_visits * 100).toFixed(1)}% of all visits` : 'No visits in range'} />
          </div>

          <div className="charts-grid" style={isDean ? undefined : { gridTemplateColumns: '1fr' }}>
            {/* Monthly trend */}
            <div className="chart-card fade-up fade-up-2">
              <div className="chart-title"><TrendingUp size={16} color="var(--teal)" /> Monthly Trend</div>
              {data.monthly_trend.length === 0 ? <div className="empty-state">No admissions or discharges match the selected dates.</div> : (
              <ResponsiveContainer width="100%" height={220}>
                <BarChart data={data.monthly_trend} margin={{ top:4, right:8, left:-10, bottom:0 }}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="month" tick={{ fontSize:11, fill:'var(--text-muted)' }} />
                  <YAxis tick={{ fontSize:11, fill:'var(--text-muted)' }} />
                  <Tooltip contentStyle={{ background:'var(--bg-elevated)', border:'1px solid var(--border-glow)', borderRadius:8 }} />
                  <Legend wrapperStyle={{ fontSize:12 }} />
                  <Bar dataKey="admissions" fill="var(--teal)"    radius={[4,4,0,0]} maxBarSize={18} />
                  <Bar dataKey="discharges" fill="var(--emerald)" radius={[4,4,0,0]} maxBarSize={18} />
                </BarChart>
              </ResponsiveContainer>
              )}
            </div>

            {/* Department activity */}
            {isDean && <div className="chart-card fade-up fade-up-3">
              <div className="chart-title"><Activity size={16} color="var(--violet)" /> Department Activity</div>
              {!data.dept_activity.some(d => d.visit_count > 0 || d.admission_count > 0) ? <div className="empty-state">No department activity matches the selected dates.</div> : (
              <ResponsiveContainer width="100%" height={220}>
                <BarChart data={data.dept_activity} margin={{ top:4, right:8, left:-10, bottom:0 }}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="department_name" tick={{ fontSize:11, fill:'var(--text-muted)' }} />
                  <YAxis tick={{ fontSize:11, fill:'var(--text-muted)' }} />
                  <Tooltip contentStyle={{ background:'var(--bg-elevated)', border:'1px solid var(--border-glow)', borderRadius:8 }} />
                  <Legend wrapperStyle={{ fontSize:12 }} />
                  <Bar dataKey="visit_count"     name="Visits"      fill="var(--teal)"   radius={[4,4,0,0]} maxBarSize={24} />
                  <Bar dataKey="admission_count" name="Admissions"  fill="var(--violet)" radius={[4,4,0,0]} maxBarSize={24} />
                </BarChart>
              </ResponsiveContainer>
              )}
            </div>}
          </div>

          {/* Where the time goes, and when patients arrive */}
          <div className="charts-grid">
            <div className="chart-card fade-up fade-up-4">
              <div className="chart-title"><Clock size={16} color="var(--amber)" /> Time at Each Stage (avg minutes)</div>
              {stages.every(s => s.minutes == null) ? <div className="empty-state">No timed visits match the selected dates.</div> : (
              <>
                <ResponsiveContainer width="100%" height={200}>
                  <BarChart data={stages} layout="vertical" margin={{ top:4, right:24, left:8, bottom:0 }}>
                    <CartesianGrid strokeDasharray="3 3" horizontal={false} />
                    <XAxis type="number" tick={{ fontSize:11, fill:'var(--text-muted)' }} />
                    <YAxis type="category" dataKey="stage" width={130} tick={{ fontSize:11, fill:'var(--text-muted)' }} />
                    <Tooltip contentStyle={{ background:'var(--bg-elevated)', border:'1px solid var(--border-glow)', borderRadius:8 }}
                      formatter={(v, _n, p) => [`${v} min · ${p.payload.n.toLocaleString()} visits`, 'Average']} />
                    <Bar dataKey="minutes" fill="var(--amber)" radius={[0,4,4,0]} maxBarSize={26} />
                  </BarChart>
                </ResponsiveContainer>
                <div className="card-sub" style={{ marginTop:6 }}>
                  Triage time is only recorded for {t.reg_to_triage_n.toLocaleString()} visits, so the first two bars use those visits only.
                </div>
              </>
              )}
            </div>

            <div className="chart-card fade-up fade-up-5">
              <div className="chart-title"><Activity size={16} color="var(--teal)" /> Arrivals by Hour of Day</div>
              {data.total_visits === 0 ? <div className="empty-state">No visits match the selected dates.</div> : (
              <ResponsiveContainer width="100%" height={220}>
                <BarChart data={data.visits_by_hour} margin={{ top:4, right:8, left:-10, bottom:0 }}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="hour" interval={2} tickFormatter={h => `${String(h).padStart(2, '0')}:00`} tick={{ fontSize:11, fill:'var(--text-muted)' }} />
                  <YAxis allowDecimals={false} tick={{ fontSize:11, fill:'var(--text-muted)' }} />
                  <Tooltip contentStyle={{ background:'var(--bg-elevated)', border:'1px solid var(--border-glow)', borderRadius:8 }}
                    labelFormatter={h => `${String(h).padStart(2, '0')}:00 – ${String(h).padStart(2, '0')}:59`} />
                  <Bar dataKey="count" name="Visits registered" fill="var(--teal)" radius={[4,4,0,0]} maxBarSize={18} />
                </BarChart>
              </ResponsiveContainer>
              )}
            </div>
          </div>

          {/* Breakdowns */}
          <div className="charts-grid">
            {/* Visit type */}
            <div className="chart-card fade-up fade-up-4">
              <div className="chart-title"><Users size={16} color="var(--teal)" /> Visit Type Breakdown</div>
              {data.visit_type_breakdown.length === 0 ? <div className="empty-state">No visits match the selected dates.</div> : (
              <div className="breakdown-list" style={{ marginTop:8 }}>
                {data.visit_type_breakdown.map((item,i) => (
                  <BreakdownBar key={i} label={item.visit_type} count={item.count} pct={item.pct} color={PIE_COLORS[item.visit_type] || '#64748b'} />
                ))}
              </div>
              )}
            </div>

            {/* Visit status */}
            <div className="chart-card fade-up fade-up-5">
              <div className="chart-title"><Activity size={16} color="var(--violet)" /> Visit Status Breakdown</div>
              {data.status_breakdown.length === 0 && <div className="empty-state">No visits match the selected dates.</div>}
              <div className="breakdown-list" style={{ marginTop:8 }}>
                {data.status_breakdown.map((item,i) => (
                  <BreakdownBar key={i} label={item.status} count={item.count} pct={item.pct} color={STATUS_COLORS[i % STATUS_COLORS.length]} />
                ))}
              </div>
            </div>
          </div>

          {/* Why visits were cancelled */}
          <div className="chart-card fade-up fade-up-5" style={{ marginBottom:28 }}>
            <div className="chart-title"><XCircle size={16} color="var(--rose)" /> Why Visits Were Cancelled</div>
            {data.cancellation_reasons.length === 0 ? <div className="empty-state">No cancelled visits in the selected dates.</div> : (
            <div className="breakdown-list" style={{ marginTop:8 }}>
              {data.cancellation_reasons.map(r => (
                <BreakdownBar key={r.reason} label={r.reason} count={r.count} pct={r.pct} color="var(--rose)" />
              ))}
            </div>
            )}
          </div>
        </>
      )}
    </div>
  )
}
