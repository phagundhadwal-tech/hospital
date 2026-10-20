import { useState, useEffect, useCallback, useRef } from 'react'
import {
  Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, Legend, ResponsiveContainer, BarChart
} from 'recharts'
import { Users, TrendingUp, BedDouble, Clock, Activity, Filter, Hourglass } from 'lucide-react'
import { analyticsApi, isCancelled, describeError } from '../api/client'
import { useAuth, ROLES } from '../contexts/AuthContext'
import DateRangePicker from '../components/ui/DateRangePicker'
import { KPICard, Spinner, ErrorBanner, BreakdownBar, BedBar, BedLegend } from '../components/ui/UI'
import {
  bedsByDepartment, arrivalRows, VISIT_TYPE_COLORS, PRESETS, DEFAULT_PRESET, presetRange, periodLabel, fmtDayLong,
} from './overviewData'

const TOOLTIP_STYLE = { background:'var(--bg-elevated)', border:'1px solid var(--border-glow)', borderRadius:8 }

// Overview = recent arrivals plus the live bed picture and staffing. The period filter drives the
// admissions/discharges/wait cards and the arrivals chart; bed counts are always a live snapshot.
// The month-by-month
// admissions/discharges trend and department activity live on the Patient Flow page.
export default function Overview() {
  const { user } = useAuth()
  const isDean  = user?.role === ROLES.DEAN
  const isNurse = user?.role === ROLES.NURSE
  const [kpis,    setKpis]     = useState(null)
  const [depts,    setDepts]     = useState([])
  const [nurse,    setNurse]     = useState(null)   // nurse-only: staffing, age mix, bed stay
  const [beds,     setBeds]      = useState(null)   // ward-by-ward bed snapshot
  const [arrivals, setArrivals]  = useState(null)   // daily arrivals, last 14 days of data
  const [loading,  setLoading]   = useState(true)
  const [error,    setError]     = useState('')

  const [deptFilter, setDeptFilter] = useState('')
  const [preset,      setPreset]      = useState(DEFAULT_PRESET)
  const [customStart, setCustomStart] = useState('')
  const [customEnd,   setCustomEnd]   = useState('')
  const [dataRange,   setDataRange]   = useState(null)   // first/last day that has data; anchors the presets

  const abortRef = useRef(null)

  // Department list (for the dropdown) — loaded once. Scoped roles only receive their own department.
  useEffect(() => {
    const ctl = new AbortController()
    analyticsApi.departments(ctl.signal)
      .then(r => setDepts(r.data))
      .catch(e => { if (!isCancelled(e)) setError(describeError(e, 'Failed to load departments.')) })
    return () => ctl.abort()
  }, [])

  useEffect(() => {
    const ctl = new AbortController()
    analyticsApi.dataRange(ctl.signal)
      .then(r => setDataRange(r.data))
      .catch(e => { if (!isCancelled(e)) setError(describeError(e, 'Failed to load the data range.')) })
    return () => ctl.abort()
  }, [])

  const fetchAll = useCallback(async () => {
    if (!dataRange) return                          // presets need the latest data day first
    abortRef.current?.abort()                       // a newer request replaces any older one
    const ctl = new AbortController()
    abortRef.current = ctl
    setLoading(true); setError('')
    try {
      const params = {}
      if (deptFilter) params.department_id = deptFilter

      // Dates for the period cards (All time = no limit) and for the arrivals chart (always explicit).
      const { start, end } = presetRange(preset, dataRange, customStart, customEnd)
      const cardParams = { ...params }
      if (preset !== 'all') {
        if (start) cardParams.start_date = start
        if (end)   cardParams.end_date   = end
      }
      const chartParams = { ...params }
      if (start) chartParams.start_date = start
      if (end)   chartParams.end_date   = end

      const [kRes, nRes, bRes, rRes] = await Promise.all([
        analyticsApi.kpis(cardParams, ctl.signal),
        isNurse ? analyticsApi.nurseInsights(cardParams, ctl.signal) : Promise.resolve(null),
        analyticsApi.bedAvailability(params, ctl.signal),
        analyticsApi.recentArrivals(chartParams, ctl.signal),
      ])
      if (ctl.signal.aborted) return
      setKpis(kRes.data)
      setNurse(nRes ? nRes.data : null)
      setBeds(bRes.data)
      setArrivals(rRes.data)
      setLoading(false)
    } catch (e) {
      if (isCancelled(e)) return                    // superseded by a newer request: keep waiting for it
      setKpis(null); setNurse(null); setBeds(null); setArrivals(null)
      setError(describeError(e, 'Failed to load data.'))
      setLoading(false)
    }
  }, [deptFilter, isNurse, preset, customStart, customEnd, dataRange])

  useEffect(() => { fetchAll(); return () => abortRef.current?.abort() }, [fetchAll])

  // Switching to "Custom dates" starts from the range you were already looking at, so it is never half empty.
  const choosePreset = key => {
    if (key === 'custom') {
      const { start, end } = presetRange(preset, dataRange, customStart, customEnd)
      setCustomStart(start ?? ''); setCustomEnd(end ?? '')
    }
    setPreset(key)
  }

  const period = periodLabel(preset)
  const fmtHours = h => h == null ? '—' : h >= 48 ? `${(h / 24).toFixed(1)} days` : `${h} h`

  // KPI set per role: Dean = hospital-wide throughput; Doctor = own patients & waits; Nurse = ward load
  const kpiCards = []
  if (kpis) {
    const cards = {
      admissions: { icon: <Users size={16} />, label: 'Admissions', value: kpis.admissions.toLocaleString(),
        color: 'var(--teal)', bgColor: 'var(--teal-glow)', sub: `Patients admitted ${period}` },
      discharges: { icon: <TrendingUp size={16} />, label: 'Discharges', value: kpis.discharges.toLocaleString(),
        color: 'var(--emerald)', bgColor: 'rgba(52,211,153,0.12)', sub: `Patients discharged ${period}` },
      wait: { icon: <Clock size={16} />, label: 'Avg Wait Time',
        value: kpis.avg_wait_minutes == null ? '—' : `${kpis.avg_wait_minutes} min`,
        color: 'var(--amber)', bgColor: 'rgba(251,191,36,0.12)',
        sub: kpis.avg_wait_minutes == null ? 'No patients seen yet'
          : `Registration to consultation · ${kpis.wait_samples.toLocaleString()} patients seen` },
      occupancy: { icon: <BedDouble size={16} />, label: 'Bed Occupancy', value: `${kpis.bed_occupancy_pct}%`,
        color: kpis.bed_occupancy_pct > 80 ? 'var(--rose)' : 'var(--violet)', bgColor: 'rgba(167,139,250,0.12)',
        sub: isDean ? `${kpis.current_admissions} patients currently admitted` : 'Of operational beds' },
      active: { icon: <Activity size={16} />, label: 'Active Patients', value: kpis.current_admissions.toLocaleString(),
        color: 'var(--rose)', bgColor: 'rgba(251,113,133,0.12)', sub: 'Currently admitted' },
      waiting: { icon: <Hourglass size={16} />, label: 'Waiting to be Seen', value: kpis.waiting_now.toLocaleString(),
        color: kpis.waiting_now > 0 ? 'var(--amber)' : 'var(--emerald)', bgColor: 'rgba(251,191,36,0.12)',
        sub: 'Registered, consultation not started' },
      bedStay: { icon: <BedDouble size={16} />, label: 'Avg Bed Stay', value: fmtHours(nurse?.avg_bed_stay_hours),
        color: 'var(--teal)', bgColor: 'var(--teal-glow)',
        sub: nurse ? `Finished bed stays · ${nurse.bed_stay_samples.toLocaleString()} stays` : '' },
    }
    const order =
      isDean  ? ['admissions', 'discharges', 'wait', 'occupancy'] :
      isNurse ? ['active', 'occupancy', 'discharges', 'bedStay'] :
                ['active', 'waiting', 'wait', 'occupancy']
    order.forEach(k => kpiCards.push({ key: k, props: cards[k] }))
  }

  const wards = beds?.ward_occupancy ?? []
  const deptBeds = isDean ? bedsByDepartment(wards) : []
  const arrivalData = arrivals ? arrivalRows(arrivals.days, arrivals.bucket) : []
  // Label every bar up to 10 bars; beyond that only about 6 evenly spaced labels, the tooltip gives the exact day.
  const tickInterval = arrivalData.length <= 10 ? 0 : Math.ceil(arrivalData.length / 6) - 1
  const arrivalTypes = [...new Set(arrivals?.days.flatMap(d => Object.keys(d.by_type)) ?? [])]

  const arrivalsCard = (
    <div className="chart-card fade-up fade-up-3">
      <div className="chart-title"><Activity size={16} color="var(--teal)" /> Arrivals</div>
      {arrivalData.every(d => d.total === 0) ? (
        <div className="empty-state">No visits were registered in the selected dates.</div>
      ) : (
        <>
          <ResponsiveContainer width="100%" height={230}>
            <BarChart data={arrivalData} margin={{ top:4, right:8, left:-10, bottom:0 }}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="label" interval={tickInterval} tickMargin={6}
                tick={{ fontSize:11, fill:'var(--text-muted)' }} />
              <YAxis allowDecimals={false} tick={{ fontSize:11, fill:'var(--text-muted)' }} />
              <Tooltip contentStyle={TOOLTIP_STYLE} labelStyle={{ color:'var(--text-primary)' }} />
              <Legend wrapperStyle={{ fontSize:12 }} />
              {arrivalTypes.map(t => (
                <Bar key={t} dataKey={t} stackId="a" fill={VISIT_TYPE_COLORS[t] || '#64748b'} maxBarSize={22} />
              ))}
            </BarChart>
          </ResponsiveContainer>
          <div className="card-sub" style={{ marginTop:6 }}>
            {fmtDayLong(arrivals.days[0].date)} – {fmtDayLong(arrivals.through)}
            {arrivals.bucket === 'week' ? ' · weekly totals' : ''}
          </div>
        </>
      )}
    </div>
  )

  const bedsCard = (
    <div className="chart-card fade-up fade-up-4">
      <div className="chart-title">
        <BedDouble size={16} color="var(--rose)" /> {isDean ? 'Beds by Department' : 'Beds by Ward'}
      </div>
      {(isDean ? deptBeds : wards).length === 0 ? (
        <div className="empty-state">No beds to show.</div>
      ) : (
        <>
          <div style={{ display:'flex', flexDirection:'column', gap:14, marginTop:12 }}>
            {isDean
              ? deptBeds.map(d => <BedBar key={d.department_name} name={d.department_name}
                  occupied={d.occupied} available={d.available} maintenance={d.maintenance} />)
              : wards.map(w => <BedBar key={w.ward_id} name={w.ward_name}
                  occupied={w.occupied} available={w.available} maintenance={w.maintenance} />)}
          </div>
          <BedLegend />
        </>
      )}
    </div>
  )

  return (
    <div className="page-content">
      <div className="page-header fade-up">
        <h1 className="page-title">Hospital Overview</h1>
        <p className="page-desc">
          Real-time KPIs {user?.department_name ? `· ${user.department_name}` : '· All Departments'}
        </p>
      </div>

      {/* Period (cards + arrivals) and, for roles that see several departments, the department */}
      <div className="filters-bar fade-up fade-up-1">
        <Filter size={14} color="var(--text-muted)" />
        <select className="filter-select" value={preset} onChange={e => choosePreset(e.target.value)}>
          {PRESETS.map(p => <option key={p.key} value={p.key}>{p.label}</option>)}
        </select>
        {preset === 'custom' && (
          <DateRangePicker start={customStart} end={customEnd} min={dataRange?.earliest} max={dataRange?.latest}
            onChange={(a, b) => { setCustomStart(a); setCustomEnd(b) }} />
        )}
        {depts.length > 1 && (
          <select className="filter-select" value={deptFilter} onChange={e => setDeptFilter(e.target.value)}>
            <option value="">All Departments</option>
            {depts.map(d => <option key={d.Department_ID} value={d.Department_ID}>{d.Department_Name}</option>)}
          </select>
        )}
        <button className="btn-ghost" onClick={() => { setPreset(DEFAULT_PRESET); setCustomStart(''); setCustomEnd(''); setDeptFilter('') }}>Reset</button>
      </div>

      {error   && <ErrorBanner message={error} />}
      {loading && <Spinner />}

      {!loading && kpis && (
        <>
          {/* KPI Cards */}
          <div className={`kpi-grid ${kpiCards.length === 4 ? 'kpi-grid-4' : 'kpi-grid-3'}`}>
            {kpiCards.map((c, i) => <KPICard key={c.key} delay={0.05 * i} {...c.props} />)}
          </div>

          {/* Recent activity and the bed picture */}
          <div className="charts-grid">
            {isNurse ? <>{bedsCard}{arrivalsCard}</> : <>{arrivalsCard}{bedsCard}</>}
          </div>

          {/* Nurse: patient mix and who is on the ward */}
          {isNurse && nurse && (
            <div className="charts-grid">
              <div className="chart-card fade-up fade-up-4">
                <div className="chart-title"><Users size={16} color="var(--violet)" /> Current Patients by Age</div>
                {nurse.age_groups.every(g => g.count === 0) ? (
                  <div className="empty-state">No patients are currently admitted.</div>
                ) : (
                  <div className="breakdown-list" style={{ marginTop:12 }}>
                    {nurse.age_groups.map(g => (
                      <BreakdownBar key={g.group} label={g.group} count={g.count} pct={g.pct} color="var(--violet)" />
                    ))}
                  </div>
                )}
              </div>

              <div className="chart-card fade-up fade-up-5">
                <div className="chart-title"><Users size={16} color="var(--teal)" /> Staff on Each Shift</div>
                <ResponsiveContainer width="100%" height={220}>
                  <BarChart data={nurse.staff_by_shift} margin={{ top:4, right:8, left:-10, bottom:0 }}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="shift" tick={{ fontSize:11, fill:'var(--text-muted)' }} />
                    <YAxis allowDecimals={false} tick={{ fontSize:11, fill:'var(--text-muted)' }} />
                    <Tooltip contentStyle={TOOLTIP_STYLE} labelStyle={{ color:'var(--text-primary)' }} />
                    <Legend wrapperStyle={{ fontSize:12 }} />
                    <Bar dataKey="nurses"  name="Nurses"  fill="var(--teal)"   radius={[4,4,0,0]} maxBarSize={28} />
                    <Bar dataKey="doctors" name="Doctors" fill="var(--violet)" radius={[4,4,0,0]} maxBarSize={28} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  )
}
