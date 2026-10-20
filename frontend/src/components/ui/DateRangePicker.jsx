import { useState, useEffect, useRef } from 'react'
import { Calendar, ChevronLeft, ChevronRight } from 'lucide-react'

// Calendar popover for choosing a date range. A range is only applied once BOTH days are
// picked (click the first day, then the second), so there is never a half-set range.
// Dates are plain YYYY-MM-DD strings, compared as text, so no time zone can shift a day.

const pad = n => String(n).padStart(2, '0')
const iso = (y, m, d) => `${y}-${pad(m + 1)}-${pad(d)}`            // m is 0-11
const parse = s => { const [y, m, d] = s.split('-').map(Number); return { y, m: m - 1, d } }
const daysIn = (y, m) => new Date(Date.UTC(y, m + 1, 0)).getUTCDate()
const mondayOffset = (y, m) => (new Date(Date.UTC(y, m, 1)).getUTCDay() + 6) % 7   // blanks before the 1st (Mon-first)
const monthTitle = (y, m) => new Date(Date.UTC(y, m, 1)).toLocaleDateString('en-GB', { month: 'long', year: 'numeric', timeZone: 'UTC' })
const fmt = s => new Date(s + 'T00:00:00Z').toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric', timeZone: 'UTC' })
const TODAY = new Date().toISOString().slice(0, 10)
const WEEKDAYS = ['Mo', 'Tu', 'We', 'Th', 'Fr', 'Sa', 'Su']

export default function DateRangePicker({ start, end, onChange, min, max, allowClear = false, placeholder = 'Select dates' }) {
  const [open, setOpen]   = useState(false)
  const [first, setFirst] = useState(null)      // first click of a new range, waiting for the second
  const [hover, setHover] = useState(null)
  const anchor = end || start || max || TODAY
  const [view, setView]   = useState(() => ({ y: parse(anchor).y, m: parse(anchor).m }))
  const wrapRef = useRef(null)

  useEffect(() => {
    if (!open) return
    const onDown = e => { if (!wrapRef.current?.contains(e.target)) setOpen(false) }
    const onKey  = e => { if (e.key === 'Escape') setOpen(false) }
    document.addEventListener('mousedown', onDown)
    document.addEventListener('keydown', onKey)
    return () => { document.removeEventListener('mousedown', onDown); document.removeEventListener('keydown', onKey) }
  }, [open])

  const toggle = () => {
    if (!open) {
      setFirst(null); setHover(null)
      const a = parse(end || start || max || TODAY)
      setView({ y: a.y, m: a.m })
    }
    setOpen(o => !o)
  }

  const shift = n => setView(v => { const t = v.y * 12 + v.m + n; return { y: Math.floor(t / 12), m: t % 12 } })

  const pick = day => {
    if (!first) { setFirst(day); return }
    const [s, e] = day < first ? [day, first] : [first, day]
    onChange(s, e)
    setFirst(null); setOpen(false)
  }

  // The range being shown: the committed one, or first-click → hovered day while picking.
  const shownStart = first ? (hover && hover < first ? hover : first) : start
  const shownEnd   = first ? (hover && hover > first ? hover : first) : end

  const blanks = mondayOffset(view.y, view.m)
  const cells  = [...Array(blanks).fill(null), ...Array.from({ length: daysIn(view.y, view.m) }, (_, i) => iso(view.y, view.m, i + 1))]
  const outside = day => (min && day < min) || (max && day > max)
  const label = start && end ? (start === end ? fmt(start) : `${fmt(start)} – ${fmt(end)}`) : placeholder

  return (
    <div className="drp" ref={wrapRef}>
      <button type="button" className="filter-input drp-trigger" onClick={toggle} aria-haspopup="dialog" aria-expanded={open}>
        <Calendar size={14} /> <span>{label}</span>
      </button>

      {open && (
        <div className="drp-pop" role="dialog" aria-label="Choose a date range">
          <div className="drp-head">
            <button type="button" className="drp-nav" onClick={() => shift(-1)} aria-label="Previous month"><ChevronLeft size={16} /></button>
            <span className="drp-title">{monthTitle(view.y, view.m)}</span>
            <button type="button" className="drp-nav" onClick={() => shift(1)} aria-label="Next month"><ChevronRight size={16} /></button>
          </div>

          <div className="drp-grid drp-weekdays">{WEEKDAYS.map(w => <span key={w}>{w}</span>)}</div>
          <div className="drp-grid">
            {cells.map((day, i) => {
              if (!day) return <span key={`b${i}`} />
              const off = outside(day)
              const isStart = day === shownStart, isEnd = day === shownEnd
              const inRange = shownStart && shownEnd && day > shownStart && day < shownEnd
              const cls = ['drp-day', isStart || isEnd ? 'drp-edge' : '', inRange ? 'drp-in' : '',
                isStart && shownEnd && shownEnd !== shownStart ? 'drp-edge-l' : '',
                isEnd && shownStart && shownEnd !== shownStart ? 'drp-edge-r' : ''].join(' ')
              return (
                <button key={day} type="button" className={cls} disabled={off}
                  onClick={() => pick(day)} onMouseEnter={() => first && setHover(day)}>
                  {Number(day.slice(8))}
                </button>
              )
            })}
          </div>

          <div className="drp-foot">
            <span>{first ? `Start: ${fmt(first)} — now pick the end date` : 'Pick the first day, then the last day'}</span>
            {allowClear && (start || end) && (
              <button type="button" className="drp-clear" onClick={() => { onChange('', ''); setFirst(null); setOpen(false) }}>Clear</button>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
