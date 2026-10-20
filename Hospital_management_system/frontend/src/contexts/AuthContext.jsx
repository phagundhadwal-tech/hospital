import { createContext, useContext, useState, useCallback } from 'react'
import { authApi } from '../api/client'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(() => {
    try { return JSON.parse(localStorage.getItem('cp_user')) } catch { return null }
  })

  const login = useCallback(async (email, password) => {
    const { data } = await authApi.login(email, password)
    localStorage.setItem('cp_token', data.access_token)
    const me = { email, role: data.role, department_id: data.department_id,
                 department_name: data.department_name, staff_id: data.staff_id,
                 full_name: data.full_name }
    localStorage.setItem('cp_user', JSON.stringify(me))
    setUser(me)
    return me
  }, [])

  const logout = useCallback(() => {
    localStorage.removeItem('cp_token')
    localStorage.removeItem('cp_user')
    setUser(null)
  }, [])

  return (
    <AuthContext.Provider value={{ user, login, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export const useAuth = () => useContext(AuthContext)

// Role constants (mirror backend)
export const ROLES = {
  DEAN:   'Dean',
  DOCTOR: 'Doctor',
  NURSE:  'Nurse',
}

export const PATIENT_FLOW_ROLES = new Set([
  ROLES.DEAN,
  ROLES.DOCTOR,
])

export const BED_AVAIL_ROLES = new Set([
  ROLES.DEAN,
  ROLES.DOCTOR,
  ROLES.NURSE,
])

export const FULL_ACCESS_ROLES = new Set([
  ROLES.DEAN,
])
