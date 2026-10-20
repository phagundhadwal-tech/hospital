import { useState, useEffect, useCallback, useRef } from 'react'
import {
  ComposedChart, Bar, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, Legend, ResponsiveContainer, BarChart
} from 'recharts'
import { Users, TrendingUp, BedDouble, Clock, Activity, Filter } from 'lucide-react'
import { analyticsApi, isCancelled, describeError } from '../api/client'
import { useAuth } from '../contexts/AuthContext'
import { KPICard, Spinner, ErrorBanner } from '../components/ui/UI'

export default function Overview() {
  const { user } = useAuth()
  const [kpis,     setKpis]     = useState(null)
  const [trend,    setTrend]     = useState([])
  const [activity, setActivity]  = useState([])
  const [depts,    setDepts]     = useState([])
  const [loading,  setLoading]   = useState(true)
  const [error,    setError]     = useState('')

  const [startDate, setStartDate] = useState('')
  const [endDate,   setEndDate]   = useState('')
  const [deptFilter, setDeptFilter] = useState('')

  const abortRef = useRef(null)

  // Department list (for the dropdown) — loaded once. Scoped roles only receive their own department.
  useEffect(() => {
    const ctl = new AbortController()
    analyticsApi.departments(ctl.signal)
      .then(r => setDepts(r.data))
      .catch(e => { if (!isCancelled(e)) setError(describeError(e, 'Failed to load departments.')) })
    return () => ctl.abort()
  }, [])

  const fetchAll = useCallback(async () => {
    abortRef.current?.abort()                       // a newer request replaces any older one
    const ctl = new AbortController()
    abortRef.current = ctl
    setLoading(true); setError('')
    try {
      const params = {}
      if (startDate)  params.start_date    = startDate
      if (endDate)    params.end_date      = endDate
      if (deptFilter) params.department_id = deptFilter

      const [kRes, tRes, aRes] = await Promise.all([
        analyticsApi.kpis(params, ctl.signal),
        analyticsApi.monthlyTrend(params, ctl.signal),
        analyticsApi.deptActivity(params, ctl.signal),
      ])
      if (ctl.signal.aborted) return
      setKpis(kRes.data)
      setTrend(tRes.data.data)
      setActivity(aRes.data.data)
      setLoading(false)
    } catch (e) {
      if (isCancelled(e)) return                    // superseded by a newer request: keep waiting for it
      setKpis(null); setTrend([]); setActivity([])
      setError(describeError(e, 'Failed to load data.'))
      setLoading(false)
    }
  }, [startDate, endDate, deptFilter])

  useEffect(() => { fetchAll(); return () => abortRef.current?.abort() }, [fetchAll])

  const hasActivity = activity.some(d => d.visit_count > 0 || d.admission_count > 0)

  return (
    <div className="page-content">
      <div className="page-header fade-up">
        <h1 className="page-title">Hospital Overview</h1>
        <p className="page-desc">
          Real-time KPIs {user?.department_name ? `· ${user.department_name}` : '· All Departments'}
        </p>
      </div>

      {/* Filters */}
      <div className="filters-bar fade-up fade-up-1">
        <Filter size={14} color="var(--text-muted)" />
        <span className="filter-label">From</span>
        <input type="date" className="filter-input" value={startDate} onChange={e => setStartDate(e.target.value)} />
        <span className="filter-label">To</span>
        <input type="date" className="filter-input" value={endDate} onChange={e => setEndDate(e.target.value)} />
        {depts.length > 1 && (
          <select className="filter-select" value={deptFilter} onChange={e => setDeptFilter(e.target.value)}>
            <option value="">All Departments</option>
            {depts.map(d => <option key={d.Department_ID} value={d.Department_ID}>{d.Department_Name}</option>)}
          </select>
        )}
        <button className="btn-primary" onClick={fetchAll}>Apply</button>
        <button className="btn-ghost" onClick={() => { setStartDate(''); setEndDate(''); setDeptFilter('') }}>Reset</button>
      </div>

      {error   && <ErrorBanner message={error} />}
      {loading && <Spinner />}

      {!loading && kpis && (
        <>
          {/* KPI Cards */}
          <div className="kpi-grid">
            <KPICard delay={0.0} label="Total Admissions" value={kpis.admissions.toLocaleString()}
              icon={<Users size={16} />} color="var(--teal)" bgColor="var(--teal-glow)"
              sub="Visits with an Admission_Time in range" />
            <KPICard delay={0.05} label="Discharges" value={kpis.discharges.toLocaleString()}
              icon={<TrendingUp size={16} />} color="var(--emerald)" bgColor="rgba(52,211,153,0.12)"
              sub="Visits with a Discharge_Time in range" />
            <KPICard delay={0.10} label="Avg Wait Time"
              value={kpis.avg_wait_minutes == null ? '—' : `${kpis.avg_wait_minutes} min`}
              icon={<Clock size={16} />} color="var(--amber)" bgColor="rgba(251,191,36,0.12)"
              sub={kpis.avg_wait_minutes == null ? 'No valid visits in range' : `Registration → Consultation start · ${kpis.wait_samples.toLocaleString()} visits`} />
            <KPICard delay={0.15} label="Bed Occupancy" value={`${kpis.bed_occupancy_pct}%`}
              icon={<BedDouble size={16} />} color={kpis.bed_occupancy_pct > 80 ? 'var(--rose)' : 'var(--violet)'}
              bgColor="rgba(167,139,250,0.12)" sub={`${kpis.current_admissions} currently admitted`} />
            <KPICard delay={0.20} label="Active Patients" value={kpis.current_admissions.toLocaleString()}
              icon={<Activity size={16} />} color="var(--rose)" bgColor="rgba(251,113,133,0.12)"
              sub="Admitted, not yet discharged" />
          </div>

          {/* Charts */}
          <div className="charts-grid">
            {/* Monthly Trend */}
            <div className="chart-card fade-up fade-up-3">
              <div className="chart-title"><TrendingUp size={16} color="var(--teal)" /> Monthly Admissions & Discharges</div>
              {trend.length === 0 ? (
                <div className="empty-state">No admissions or discharges match the selected filters.</div>
              ) : (
                <ResponsiveContainer width="100%" height={240}>
                  <ComposedChart data={trend} margin={{ top:4, right:8, left:-10, bottom:0 }}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="month" tick={{ fontSize:11, fill:'var(--text-muted)' }} />
                    <YAxis tick={{ fontSize:11, fill:'var(--text-muted)' }} />
                    <Tooltip contentStyle={{ background:'var(--bg-elevated)', border:'1px solid var(--border-glow)', borderRadius:8 }}
                      labelStyle={{ color:'var(--text-primary)' }} itemStyle={{ color:'var(--text-muted)' }} />
                    <Legend wrapperStyle={{ fontSize:12 }} />
                    <Bar dataKey="admissions" fill="var(--teal)" radius={[4,4,0,0]} maxBarSize={20} />
                    <Line type="monotone" dataKey="discharges" stroke="var(--emerald)" strokeWidth={2} dot={false} />
                  </ComposedChart>
                </ResponsiveContainer>
              )}
            </div>

            {/* Department Activity */}
            <div className="chart-card fade-up fade-up-4">
              <div className="chart-title"><Activity size={16} color="var(--violet)" /> Department Activity</div>
              {!hasActivity ? (
                <div className="empty-state">No department activity matches the selected filters.</div>
              ) : (
                <ResponsiveContainer width="100%" height={240}>
                  <BarChart data={activity} margin={{ top:4, right:8, left:-10, bottom:0 }}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="department_name" tick={{ fontSize:11, fill:'var(--text-muted)' }} />
                    <YAxis tick={{ fontSize:11, fill:'var(--text-muted)' }} />
                    <Tooltip contentStyle={{ background:'var(--bg-elevated)', border:'1px solid var(--border-glow)', borderRadius:8 }}
                      labelStyle={{ color:'var(--text-primary)' }} />
                    <Legend wrapperStyle={{ fontSize:12 }} />
                    <Bar dataKey="visit_count"     name="Total Visits"     fill="var(--teal)"    radius={[4,4,0,0]} maxBarSize={28} />
                    <Bar dataKey="admission_count" name="Admissions"       fill="var(--violet)"  radius={[4,4,0,0]} maxBarSize={28} />
                  </BarChart>
                </ResponsiveContainer>
              )}
            </div>
          </div>
        </>
      )}
    </div>
  )
}
