import axios from 'axios'

const api = axios.create({ baseURL: '/api' })

// Attach JWT to every request
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('cp_token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

// On 401, clear token and redirect to login.
// A 401 from the login call itself means wrong credentials: let the login page
// show its error instead of reloading the page and wiping the message.
api.interceptors.response.use(
  (res) => res,
  (err) => {
    const isLoginRequest = err.config?.url?.endsWith('/auth/login')
    if (err.response?.status === 401 && !isLoginRequest) {
      localStorage.removeItem('cp_token')
      localStorage.removeItem('cp_user')
      window.location.href = '/login'
    }
    return Promise.reject(err)
  }
)

export default api

// ── Endpoint helpers ───────────────────────────────────────────────────────

export const authApi = {
  login: (email, password) => api.post('/auth/login', { email, password }),
  me:    ()                => api.get('/auth/me'),
}

// Every call accepts an optional AbortSignal so a newer request can cancel an older one
// (prevents a slow, stale response from overwriting fresher filter results).
export const analyticsApi = {
  kpis:            (params, signal) => api.get('/analytics/kpis',             { params, signal }),
  monthlyTrend:    (params, signal) => api.get('/analytics/monthly-trend',    { params, signal }),
  deptActivity:    (params, signal) => api.get('/analytics/dept-activity',    { params, signal }),
  patientFlow:     (params, signal) => api.get('/analytics/patient-flow',     { params, signal }),
  bedAvailability: (params, signal) => api.get('/analytics/bed-availability', { params, signal }),
  recentArrivals:  (params, signal) => api.get('/analytics/recent-arrivals',  { params, signal }),
  dataRange:       (signal)         => api.get('/analytics/data-range',       { signal }),
  nurseInsights:   (params, signal) => api.get('/analytics/nurse-insights',   { params, signal }),
  departments:     (signal)        => api.get('/analytics/departments',      { signal }),
}

// True when a request was cancelled on purpose (not a real failure).
export const isCancelled = (err) => err?.code === 'ERR_CANCELED' || err?.name === 'CanceledError'

// Human-readable message for any failed request. Never falls back to mock data.
export function describeError(err, fallback) {
  if (err?.response?.data?.detail) {
    const d = err.response.data.detail
    return typeof d === 'string' ? d : fallback
  }
  if (!err?.response) return 'Cannot reach the CarePulse API. Make sure the backend is running on port 8000.'
  return fallback
}
