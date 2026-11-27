import { FormEvent, ReactNode, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Navigate, Route, Routes } from 'react-router-dom'
import { Shell } from './components/Shell'
import { api, login } from './lib/api'
import { AppointmentsPage, ApprovalQueuePage, Dashboard, DatabaseEntryPage, DraftsPage, EquipmentArchivePage, EquipmentPage, GoogleSyncPage, HospitalsPage, LineGroupsPage, Placeholder, PlannerPage, ReportsPage, SettingsPage, SlotsPage, UsersPage } from './pages'

const pages: Record<string, string> = {
  'data-entry': 'กรอกข้อมูลฐานข้อมูล', hospitals: 'โรงพยาบาล', equipment: 'ฐานข้อมูลอุปกรณ์', 'equipment-archive': 'Archive อุปกรณ์', planner: 'วางแผน PM รายปี', slots: 'รอบ PM', users: 'ผู้ใช้งานและสิทธิ์',
  intakes: 'ตารางจากช่าง', drafts: 'ตรวจข้อมูลร่าง', approvals: 'คิวอนุมัติ', calendar: 'ปฏิทินนัดหมาย',
  confirmations: 'การยืนยันนัด', reschedules: 'คำขอเลื่อนนัด', history: 'ประวัติการแก้ไข',
  'next-year': 'แผนปีถัดไป', sheets: 'Google Sheets', drive: 'Google Drive', 'line-groups': 'LINE Groups',
  reports: 'รายงาน', settings: 'ตั้งค่า',
}

function LoginPage({ onSuccess }: { onSuccess: () => void }) {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)

  async function submit(event: FormEvent) {
    event.preventDefault()
    setError('')
    setSubmitting(true)
    try {
      await login(username, password)
      onSuccess()
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'เข้าสู่ระบบไม่สำเร็จ')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <main className="login-page">
      <section className="login-aside">
        <div className="login-brand">BA<span>CHILLER</span></div>
        <div><p className="eyebrow">SERVICE & PM ASSISTANT</p><h1>จัดการแผน PM<br />และนัดหมาย<br /><em>ในที่เดียว</em></h1><p>ฐานข้อมูลกลางสำหรับทีมบริการ โรงพยาบาล และผู้ดูแลระบบ</p></div>
        <small>CONFIRMED หมายถึงโรงพยาบาลยอมรับวันนัดล่วงหน้า</small>
      </section>
      <section className="login-card-wrap">
        <form className="login-card" onSubmit={submit}>
          <div><p className="eyebrow">SECURE ACCESS</p><h2>เข้าสู่ระบบ</h2><p>ใช้บัญชีที่ผู้ดูแลระบบสร้างให้</p></div>
          <label>User ID<input type="text" value={username} onChange={(event) => setUsername(event.target.value)} autoComplete="username" required /></label>
          <label>รหัสผ่าน<input type="password" value={password} onChange={(event) => setPassword(event.target.value)} autoComplete="current-password" required /></label>
          {error && <div className="login-error">{error}</div>}
          <button type="submit" disabled={submitting}>{submitting ? 'กำลังตรวจสอบ…' : 'เข้าสู่ระบบ'}</button>
          <small>ผู้ดูแลเริ่มต้นใช้ User ID admin</small>
        </form>
      </section>
    </main>
  )
}

function AdminOnly({ children }: { children: ReactNode }) {
  const user = useQuery({ queryKey: ['current-user'], queryFn: () => api<{ role: string; display_name?: string }>('/auth/me') })
  if (user.isLoading) return <section className="page-heading"><div><h1>กำลังตรวจสอบสิทธิ์…</h1></div></section>
  if (user.isError) return <section className="page-heading"><div><h1>ตรวจสอบสิทธิ์ไม่สำเร็จ</h1><p>Token หมดอายุหรือ Backend ที่เปิดอยู่ยังเป็นเวอร์ชันเก่า กรุณาออกจากระบบแล้วเข้าใหม่</p><button className="primary" onClick={() => { localStorage.removeItem('ba_access_token'); window.location.reload() }}>ออกจากระบบและเข้าใหม่</button></div></section>
  if (user.data?.role?.toUpperCase() !== 'ADMIN') return <section className="page-heading"><div><h1>หน้านี้สำหรับ Admin เท่านั้น</h1><p>บัญชีนี้มีสิทธิ์ {user.data?.role || 'ไม่ทราบสิทธิ์'} จึงยังเปิดหน้ากรอกข้อมูลไม่ได้ ให้รันคำสั่ง `python -m app.cli ensure-admin` ใน Backend แล้วออกจากระบบเข้าใหม่</p></div></section>
  return children
}

export default function App() {
  const [authenticated, setAuthenticated] = useState(() => Boolean(localStorage.getItem('ba_access_token')))
  if (!authenticated) return <LoginPage onSuccess={() => setAuthenticated(true)} />
  return (
    <Shell onLogout={() => setAuthenticated(false)}>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/data-entry" element={<AdminOnly><DatabaseEntryPage /></AdminOnly>} />
        <Route path="/hospitals" element={<HospitalsPage />} />
        <Route path="/equipment" element={<EquipmentPage />} />
        <Route path="/equipment-archive" element={<AdminOnly><EquipmentArchivePage /></AdminOnly>} />
        <Route path="/planner" element={<PlannerPage />} />
        <Route path="/slots" element={<SlotsPage />} />
        <Route path="/users" element={<AdminOnly><UsersPage /></AdminOnly>} />
        <Route path="/drafts" element={<DraftsPage />} />
        <Route path="/intakes" element={<AdminOnly><ApprovalQueuePage /></AdminOnly>} />
        <Route path="/approvals" element={<AdminOnly><ApprovalQueuePage /></AdminOnly>} />
        <Route path="/calendar" element={<AppointmentsPage />} />
        <Route path="/confirmations" element={<AppointmentsPage title="การยืนยันนัด" status="CONFIRMED" />} />
        <Route path="/reschedules" element={<AppointmentsPage title="คำขอเลื่อนนัด" status="RESCHEDULE_REQUESTED" />} />
        <Route path="/history" element={<AppointmentsPage title="ประวัตินัดหมาย" />} />
        <Route path="/sheets" element={<GoogleSyncPage />} />
        <Route path="/line-groups" element={<LineGroupsPage />} />
        <Route path="/reports" element={<ReportsPage />} />
        <Route path="/settings" element={<SettingsPage />} />
        {Object.entries(pages).filter(([path]) => !['data-entry', 'hospitals', 'equipment', 'equipment-archive', 'planner', 'slots', 'users', 'drafts', 'intakes', 'approvals', 'calendar', 'confirmations', 'reschedules', 'history', 'sheets', 'line-groups', 'reports', 'settings'].includes(path)).map(([path, title]) => <Route key={path} path={`/${path}`} element={<Placeholder title={title} />} />)}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Shell>
  )
}

