import { useState, useEffect, useCallback, useRef } from 'react'
import {
  ComposedChart, Bar, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend,
  ResponsiveContainer, PieChart, Pie, Cell, BarChart
} from 'recharts'
import { Activity, Users, TrendingUp, Clock, Filter } from 'lucide-react'
import { analyticsApi, isCancelled, describeError } from '../api/client'
import { useAuth, PATIENT_FLOW_ROLES } from '../contexts/AuthContext'
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
  const [data,    setData]    = useState(null)
  const [loading, setLoading] = useState(true)
  const [error,   setError]   = useState('')
  const [startDate, setStartDate] = useState('')
  const [endDate,   setEndDate]   = useState('')

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

  useEffect(() => { fetchData(); return () => abortRef.current?.abort() }, [fetchData])

  return (
    <div className="page-content">
      <div className="page-header fade-up">
        <h1 className="page-title">Patient Flow Analytics</h1>
        <p className="page-desc">Visit patterns, wait times, and status breakdown</p>
      </div>

      <div className="filters-bar fade-up fade-up-1">
        <Filter size={14} color="var(--text-muted)" />
        <span className="filter-label">From</span>
        <input type="date" className="filter-input" value={startDate} onChange={e => setStartDate(e.target.value)} />
        <span className="filter-label">To</span>
        <input type="date" className="filter-input" value={endDate} onChange={e => setEndDate(e.target.value)} />
        <button className="btn-primary" onClick={fetchData}>Apply</button>
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

          <div className="charts-grid">
            {/* Monthly trend */}
            <div className="chart-card fade-up fade-up-2">
              <div className="chart-title"><TrendingUp size={16} color="var(--teal)" /> Monthly Trend</div>
              {data.monthly_trend.length === 0 ? <div className="empty-state">No admissions or discharges match the selected dates.</div> : (
              <ResponsiveContainer width="100%" height={220}>
                <ComposedChart data={data.monthly_trend} margin={{ top:4, right:8, left:-10, bottom:0 }}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="month" tick={{ fontSize:11, fill:'var(--text-muted)' }} />
                  <YAxis tick={{ fontSize:11, fill:'var(--text-muted)' }} />
                  <Tooltip contentStyle={{ background:'var(--bg-elevated)', border:'1px solid var(--border-glow)', borderRadius:8 }} />
                  <Legend wrapperStyle={{ fontSize:12 }} />
                  <Bar dataKey="admissions" fill="var(--teal)"    radius={[4,4,0,0]} maxBarSize={18} />
                  <Line type="monotone" dataKey="discharges" stroke="var(--emerald)" strokeWidth={2} dot={false} />
                </ComposedChart>
              </ResponsiveContainer>
              )}
            </div>

            {/* Department activity */}
            <div className="chart-card fade-up fade-up-3">
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
            </div>
          </div>

          {/* Breakdowns */}
          <div className="charts-grid">
            {/* Visit type */}
            <div className="chart-card fade-up fade-up-4">
              <div className="chart-title"><Users size={16} color="var(--teal)" /> Visit Type Breakdown</div>
              {data.visit_type_breakdown.length === 0 ? <div className="empty-state">No visits match the selected dates.</div> : (
              <div style={{ display:'flex', gap:24, alignItems:'center' }}>
                <PieChart width={160} height={160}>
                  <Pie data={data.visit_type_breakdown} dataKey="count" nameKey="visit_type" cx={76} cy={76} outerRadius={68} innerRadius={36}>
                    {data.visit_type_breakdown.map((e,i) => (
                      <Cell key={i} fill={PIE_COLORS[e.visit_type] || '#64748b'} />
                    ))}
                  </Pie>
                  <Tooltip contentStyle={{ background:'var(--bg-elevated)', border:'1px solid var(--border-glow)', borderRadius:8, fontSize:12 }} />
                </PieChart>
                <div className="breakdown-list" style={{ flex:1 }}>
                  {data.visit_type_breakdown.map((item,i) => (
                    <BreakdownBar key={i} label={item.visit_type} count={item.count} pct={item.pct} color={PIE_COLORS[item.visit_type] || '#64748b'} />
                  ))}
                </div>
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
        </>
      )}
    </div>
  )
}
