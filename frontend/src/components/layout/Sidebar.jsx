import { useNavigate, NavLink } from 'react-router-dom'
import { LayoutDashboard, Activity, BedDouble, LogOut } from 'lucide-react'
import { useAuth, PATIENT_FLOW_ROLES, BED_AVAIL_ROLES } from '../../contexts/AuthContext'

export default function Sidebar() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  const handleLogout = () => { logout(); navigate('/login') }
  const initials = user?.full_name?.split(' ').map(w => w[0]).join('').slice(0,2).toUpperCase() || '??'

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

      <div className="sidebar-footer">
        <div className="user-chip">
          <div className="user-avatar">{initials}</div>
          <div className="user-info">
            <div className="user-name">{user?.full_name || user?.email}</div>
            <div className="user-role">{user?.role}</div>
          </div>
          <button className="logout-btn" onClick={handleLogout} title="Log out">
            <LogOut size={15} />
          </button>
        </div>
      </div>
    </aside>
  )
}
