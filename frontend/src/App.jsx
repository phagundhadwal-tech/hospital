import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider } from './contexts/AuthContext'
import Layout       from './components/layout/Layout'
import Login        from './pages/Login'
import Overview     from './pages/Overview'
import PatientFlow  from './pages/PatientFlow'
import BedAvailability from './pages/BedAvailability'
import AccessDenied from './pages/AccessDenied'

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/access-denied" element={<AccessDenied />} />

          <Route element={<Layout />}>
            <Route index element={<Navigate to="/overview" replace />} />
            <Route path="/overview"          element={<Overview />} />
            <Route path="/patient-flow"      element={<PatientFlow />} />
            <Route path="/bed-availability"  element={<BedAvailability />} />
          </Route>

          <Route path="*" element={<Navigate to="/overview" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  )
}
