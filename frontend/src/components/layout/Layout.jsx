import { useState } from 'react'
import { Outlet, Navigate, useNavigate } from 'react-router-dom'
import { LogOut } from 'lucide-react'
import { useAuth } from '../../contexts/AuthContext'
import Sidebar from './Sidebar'

export default function Layout() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const [confirmOpen, setConfirmOpen] = useState(false)
  if (!user) return <Navigate to="/login" replace />

  const handleLogout = () => { setConfirmOpen(false); logout(); navigate('/login') }
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
            <button className="logout-btn" onClick={() => setConfirmOpen(true)} title="Log out">
              <LogOut size={15} />
            </button>
          </div>
        </header>
        <Outlet />
      </div>
      {confirmOpen && (
        <div className="confirm-overlay" onClick={() => setConfirmOpen(false)}>
          <div className="confirm-dialog" role="alertdialog" aria-modal="true" aria-labelledby="logout-title" onClick={e => e.stopPropagation()}>
            <h3 id="logout-title">Log out?</h3>
            <p>
              Please make sure you have saved any changes. Unsaved work will be lost.
              Patient data is confidential — ensure no sensitive information is left on screen.
            </p>
            <div className="confirm-actions">
              <button className="confirm-cancel" autoFocus onClick={() => setConfirmOpen(false)}>Cancel</button>
              <button className="confirm-ok" onClick={handleLogout}>Log out</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
