import { useNavigate } from 'react-router-dom'
import { ShieldOff, ArrowLeft } from 'lucide-react'

export default function AccessDenied() {
  const navigate = useNavigate()
  return (
    <div className="page-content">
      <div className="access-denied fade-up">
        <div className="access-denied-icon"><ShieldOff size={56} color="var(--rose)" /></div>
        <h2>Access Denied</h2>
        <p>Your role does not have permission to view this page. Contact your Hospital Administrator if you believe this is an error.</p>
        <button className="btn-ghost" onClick={() => navigate('/overview')}>
          <ArrowLeft size={14} style={{ display:'inline', marginRight:6 }} />
          Back to Overview
        </button>
      </div>
    </div>
  )
}
