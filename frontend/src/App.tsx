import { FormEvent, useState } from 'react'
import { Navigate, Route, Routes } from 'react-router-dom'
import { Shell } from './components/Shell'
import { login } from './lib/api'
import { AppointmentsPage, ApprovalQueuePage, Dashboard, DatabaseEntryPage, DraftsPage, EquipmentPage, GoogleSyncPage, HospitalsPage, LineGroupsPage, Placeholder, PlannerPage, ReportsPage, SettingsPage, SlotsPage, UsersPage } from './pages'

const pages: Record<string, string> = {
  'data-entry': 'กรอกข้อมูลฐานข้อมูล', hospitals: 'โรงพยาบาล', equipment: 'ฐานข้อมูลอุปกรณ์', planner: 'วางแผน PM รายปี', slots: 'รอบ PM', users: 'ผู้ใช้งานและสิทธิ์',
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

export default function App() {
  const [authenticated, setAuthenticated] = useState(() => Boolean(localStorage.getItem('ba_access_token')))
  if (!authenticated) return <LoginPage onSuccess={() => setAuthenticated(true)} />
  return (
    <Shell onLogout={() => setAuthenticated(false)}>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/data-entry" element={<DatabaseEntryPage />} />
        <Route path="/hospitals" element={<HospitalsPage />} />
        <Route path="/equipment" element={<EquipmentPage />} />
        <Route path="/planner" element={<PlannerPage />} />
        <Route path="/slots" element={<SlotsPage />} />
        <Route path="/users" element={<UsersPage />} />
        <Route path="/drafts" element={<DraftsPage />} />
        <Route path="/intakes" element={<ApprovalQueuePage />} />
        <Route path="/approvals" element={<ApprovalQueuePage />} />
        <Route path="/calendar" element={<AppointmentsPage />} />
        <Route path="/confirmations" element={<AppointmentsPage title="การยืนยันนัด" status="CONFIRMED" />} />
        <Route path="/reschedules" element={<AppointmentsPage title="คำขอเลื่อนนัด" status="RESCHEDULE_REQUESTED" />} />
        <Route path="/history" element={<AppointmentsPage title="ประวัตินัดหมาย" />} />
        <Route path="/sheets" element={<GoogleSyncPage />} />
        <Route path="/line-groups" element={<LineGroupsPage />} />
        <Route path="/reports" element={<ReportsPage />} />
        <Route path="/settings" element={<SettingsPage />} />
        {Object.entries(pages).filter(([path]) => !['data-entry', 'hospitals', 'equipment', 'planner', 'slots', 'users', 'drafts', 'intakes', 'approvals', 'calendar', 'confirmations', 'reschedules', 'history', 'sheets', 'line-groups', 'reports', 'settings'].includes(path)).map(([path, title]) => <Route key={path} path={`/${path}`} element={<Placeholder title={title} />} />)}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Shell>
  )
}

