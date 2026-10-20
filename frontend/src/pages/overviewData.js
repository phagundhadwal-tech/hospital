// Roll the per-ward bed snapshot up to one row per department.
export function bedsByDepartment(wards) {
  const byDept = new Map()
  for (const w of wards) {
    const d = byDept.get(w.department_name) ?? { department_name: w.department_name, occupied: 0, available: 0, maintenance: 0 }
    d.occupied    += w.occupied
    d.available   += w.available
    d.maintenance += w.maintenance
    byDept.set(w.department_name, d)
  }
  return [...byDept.values()].sort((a, b) => a.department_name.localeCompare(b.department_name))
}

const fmtDay = iso => new Date(iso + 'T00:00:00').toLocaleDateString('en-GB', { day: 'numeric', month: 'short' })
export const fmtDayLong = iso => new Date(iso + 'T00:00:00').toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' })

// recharts wants one flat object per bucket: { label, Emergency: n, Inpatient: n, ... }
export function arrivalRows(days, bucket = 'day') {
  return days.map(d => ({
    label: bucket === 'week' ? `Wk ${fmtDay(d.date)}` : fmtDay(d.date),
    ...d.by_type,
    total: d.total,
  }))
}

export const VISIT_TYPE_COLORS = { Inpatient: '#0284c7', Outpatient: '#059669', Emergency: '#e11d48' }

// ── Date presets ──────────────────────────────────────────────────────────────
// Presets end on the latest day that has data (not today), so "Last 7 days" is never half empty.
export const PRESETS = [
  { key: '7',      label: 'Last 7 days' },
  { key: '14',     label: 'Last 14 days' },
  { key: '30',     label: 'Last 30 days' },
  { key: '90',     label: 'Last 90 days' },
  { key: 'all',    label: 'All time' },
  { key: 'custom', label: 'Custom dates' },
]
export const DEFAULT_PRESET = '14'

export function addDays(iso, n) {
  const [y, m, d] = iso.split('-').map(Number)
  return new Date(Date.UTC(y, m - 1, d + n)).toISOString().slice(0, 10)
}

// → { start, end } as YYYY-MM-DD (either may be undefined)
export function presetRange(preset, dataRange, customStart, customEnd) {
  if (preset === 'custom') return { start: customStart || undefined, end: customEnd || undefined }
  if (!dataRange?.latest) return {}
  if (preset === 'all') return { start: dataRange.earliest, end: dataRange.latest }
  return { start: addDays(dataRange.latest, -(Number(preset) - 1)), end: dataRange.latest }
}

export function periodLabel(preset) {
  return preset === 'all' ? 'all time' : preset === 'custom' ? 'in the selected dates' : `in the last ${preset} days`
}
