import { FormEvent, useState } from 'react'
import { Navigate, Route, Routes } from 'react-router-dom'
import { Shell } from './components/Shell'
import { login } from './lib/api'
import { AppointmentsPage, ApprovalQueuePage, Dashboard, DraftsPage, EquipmentPage, HospitalsPage, Placeholder, PlannerPage } from './pages'

const pages: Record<string, string> = {
  hospitals: 'โรงพยาบาล', equipment: 'ฐานข้อมูลอุปกรณ์', planner: 'วางแผน PM รายปี', slots: 'รอบ PM',
  intakes: 'ตารางจากช่าง', drafts: 'ตรวจข้อมูลร่าง', approvals: 'คิวอนุมัติ', calendar: 'ปฏิทินนัดหมาย',
  confirmations: 'การยืนยันนัด', reschedules: 'คำขอเลื่อนนัด', history: 'ประวัติการแก้ไข',
  'next-year': 'แผนปีถัดไป', sheets: 'Google Sheets', drive: 'Google Drive', 'line-groups': 'LINE Groups',
  reports: 'รายงาน', settings: 'ตั้งค่า',
}

function LoginPage({ onSuccess }: { onSuccess: () => void }) {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)

  async function submit(event: FormEvent) {
    event.preventDefault()
    setError('')
    setSubmitting(true)
    try {
      await login(email, password)
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
          <label>อีเมล<input type="email" value={email} onChange={(event) => setEmail(event.target.value)} autoComplete="username" required /></label>
          <label>รหัสผ่าน<input type="password" value={password} onChange={(event) => setPassword(event.target.value)} autoComplete="current-password" required /></label>
          {error && <div className="login-error">{error}</div>}
          <button type="submit" disabled={submitting}>{submitting ? 'กำลังตรวจสอบ…' : 'เข้าสู่ระบบ'}</button>
          <small>ไม่มีรหัสผ่านเริ่มต้น ผู้ดูแลต้อง bootstrap บัญชีแรกผ่าน server</small>
        </form>
      </section>
    </main>
  )
}

export default function App() {
  const [authenticated, setAuthenticated] = useState(() => Boolean(localStorage.getItem('ba_access_token')))
  if (!authenticated) return <LoginPage onSuccess={() => setAuthenticated(true)} />
  return (
    <Shell>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/hospitals" element={<HospitalsPage />} />
        <Route path="/equipment" element={<EquipmentPage />} />
        <Route path="/planner" element={<PlannerPage />} />
        <Route path="/drafts" element={<DraftsPage />} />
        <Route path="/intakes" element={<ApprovalQueuePage />} />
        <Route path="/approvals" element={<ApprovalQueuePage />} />
        <Route path="/calendar" element={<AppointmentsPage />} />
        <Route path="/confirmations" element={<AppointmentsPage title="การยืนยันนัด" status="CONFIRMED" />} />
        <Route path="/reschedules" element={<AppointmentsPage title="คำขอเลื่อนนัด" status="RESCHEDULE_REQUESTED" />} />
        <Route path="/history" element={<AppointmentsPage title="ประวัตินัดหมาย" />} />
        {Object.entries(pages).filter(([path]) => !['hospitals', 'equipment', 'planner', 'drafts', 'intakes', 'approvals', 'calendar', 'confirmations', 'reschedules', 'history'].includes(path)).map(([path, title]) => <Route key={path} path={`/${path}`} element={<Placeholder title={title} />} />)}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Shell>
  )
}

