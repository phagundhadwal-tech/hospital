import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import { Lock, Mail, Loader2 } from 'lucide-react'

export default function Login() {
  const { login } = useAuth()
  const navigate  = useNavigate()
  const [email,    setEmail]    = useState('')
  const [password, setPassword] = useState('')
  const [error,    setError]    = useState('')
  const [loading,  setLoading]  = useState(false)

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      await login(email.trim(), password)
      navigate('/overview', { replace: true })
    } catch (err) {
      setError(err.response?.data?.detail || 'Incorrect email or password.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="login-page">
      <div className="login-card fade-up">
        <div className="login-logo">
          <div className="login-icon">🏥</div>
          <div className="login-title">CarePulse</div>
          <div className="login-sub">Hospital Management System</div>
        </div>

        <form onSubmit={handleSubmit} noValidate>
          <div className="form-group">
            <label className="form-label" htmlFor="email">
              <Mail size={13} style={{ display: 'inline', marginRight: 4 }} />
              Email address
            </label>
            <input
              id="email" type="email" autoComplete="email"
              className={`form-input${error ? ' error' : ''}`}
              placeholder="you@carepulse.local"
              value={email} onChange={e => setEmail(e.target.value)}
              required
            />
          </div>

          <div className="form-group">
            <label className="form-label" htmlFor="password">
              <Lock size={13} style={{ display: 'inline', marginRight: 4 }} />
              Password
            </label>
            <input
              id="password" type="password" autoComplete="current-password"
              className={`form-input${error ? ' error' : ''}`}
              placeholder="••••••••"
              value={password} onChange={e => setPassword(e.target.value)}
              required
            />
          </div>

          {error && <div className="form-error" style={{ marginBottom: 10 }}>⚠ {error}</div>}

          <button type="submit" className="btn-login" disabled={loading}>
            {loading ? <Loader2 size={16} style={{ animation: 'spin 1s linear infinite' }} /> : null}
            {loading ? 'Signing in…' : 'Sign in'}
          </button>
        </form>
      </div>
    </div>
  )
}
