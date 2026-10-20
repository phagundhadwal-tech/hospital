import { NavLink } from 'react-router-dom'
import { LayoutDashboard, Activity, BedDouble } from 'lucide-react'
import { useAuth, PATIENT_FLOW_ROLES, BED_AVAIL_ROLES } from '../../contexts/AuthContext'

export default function Sidebar() {
  const { user } = useAuth()

  return (
    <aside className="sidebar">
      <div className="sidebar-brand">
        <div className="brand-icon">🏥</div>
        <div>
          <div className="brand-text">CarePulse</div>
          <div className="brand-sub">Hospital Management</div>
        </div>
      </div>

      <nav className="sidebar-nav">
        <NavLink to="/overview" className={({ isActive }) => `nav-link${isActive ? ' active' : ''}`}>
          <LayoutDashboard size={17} />
          Hospital Overview
        </NavLink>

        {PATIENT_FLOW_ROLES.has(user?.role) && (
          <NavLink to="/patient-flow" className={({ isActive }) => `nav-link${isActive ? ' active' : ''}`}>
            <Activity size={17} />
            Patient Flow
          </NavLink>
        )}

        {BED_AVAIL_ROLES.has(user?.role) && (
          <NavLink to="/bed-availability" className={({ isActive }) => `nav-link${isActive ? ' active' : ''}`}>
            <BedDouble size={17} />
            Bed Availability
          </NavLink>
        )}
      </nav>
    </aside>
  )
}
