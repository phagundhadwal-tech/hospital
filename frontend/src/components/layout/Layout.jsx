import { Outlet, Navigate, useNavigate } from 'react-router-dom'
import { LogOut } from 'lucide-react'
import { useAuth } from '../../contexts/AuthContext'
import Sidebar from './Sidebar'

export default function Layout() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  if (!user) return <Navigate to="/login" replace />

  const handleLogout = () => { logout(); navigate('/login') }
  const initials = user.full_name?.split(' ').map(w => w[0]).join('').slice(0,2).toUpperCase() || '??'

  return (
    <div className="app-shell">
      <Sidebar />
      <div className="main-area">
        <header className="topbar">
          <div className="user-chip">
            <div className="user-avatar">{initials}</div>
            <div className="user-info">
              <div className="user-name">{user.full_name || user.email}</div>
              <div className="user-role">{user.role}</div>
            </div>
            <button className="logout-btn" onClick={handleLogout} title="Log out">
              <LogOut size={15} />
            </button>
          </div>
        </header>
        <Outlet />
      </div>
    </div>
  )
}
