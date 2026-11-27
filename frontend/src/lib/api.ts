export type Metrics = {
  total_pm_slots: number
  confirmed_appointments: number
  pending_confirmation: number
  pending_approval: number
  reschedule_requests: number
  unscheduled_slots: number
  upcoming_appointments: number
  past_due_unconfirmed: number
  unscheduled_backlog: number
  cancelled_appointments: number
  admin_changed_appointments: number
  failed_notifications: number
  sync_errors: number
}

const API_BASE = import.meta.env.VITE_API_BASE ?? '/api/v1'

export async function api<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = localStorage.getItem('ba_access_token')
  const headers = new Headers(options.headers)
  if (!headers.has('Content-Type')) headers.set('Content-Type', 'application/json')
  if (token) headers.set('Authorization', `Bearer ${token}`)
  const response = await fetch(`${API_BASE}${path}`, { ...options, headers })
  if (!response.ok) {
    const body = await response.json().catch(() => ({ detail: 'ไม่สามารถเชื่อมต่อระบบได้' }))
    const detail = body.detail
    const message = Array.isArray(detail)
      ? detail.map((item) => typeof item === 'string' ? item : item?.msg ?? JSON.stringify(item)).join(' · ')
      : typeof detail === 'object' && detail !== null
        ? JSON.stringify(detail)
        : detail ?? 'เกิดข้อผิดพลาด'
    throw new Error(message)
  }
  return response.json() as Promise<T>
}

export async function login(username: string, password: string) {
  const result = await api<{ access_token: string }>('/auth/token', {
    method: 'POST',
    body: JSON.stringify({ username, password }),
  })
  localStorage.setItem('ba_access_token', result.access_token)
}

