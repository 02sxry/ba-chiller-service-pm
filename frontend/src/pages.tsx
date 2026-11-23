import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { AlertTriangle, ArrowUpRight, CalendarCheck2, CircleCheckBig, Clock3, Layers3, RefreshCcw, Wrench } from 'lucide-react'
import { useState } from 'react'
import { api, type Metrics } from './lib/api'

const currentYear = new Date().getFullYear()
const buddhistYear = currentYear + 543

function MetricCard({ title, value, note, tone, icon: Icon }: { title: string; value: number; note: string; tone: string; icon: typeof Layers3 }) {
  return (
    <article className={`metric-card ${tone}`}>
      <div className="metric-heading"><span>{title}</span><div className="metric-icon"><Icon size={19} /></div></div>
      <strong>{value.toLocaleString('th-TH')}</strong>
      <small>{note}</small>
    </article>
  )
}

export function Dashboard() {
  const [year, setYear] = useState(currentYear)
  const query = useQuery({
    queryKey: ['dashboard', year],
    queryFn: () => api<Metrics>(`/dashboard?year=${year}`),
  })
  const data = query.data
  return (
    <>
      <section className="page-heading">
        <div><p className="eyebrow">ศูนย์ควบคุมงานบริการ</p><h1>ภาพรวมการนัดหมาย PM</h1><p>ติดตามภาระตามแผนและสถานะนัดหมาย โดยไม่อนุมานผลการเข้าบริการ</p></div>
        <div className="heading-actions">
          <label>ปีแผน<select value={year} onChange={(event) => setYear(Number(event.target.value))}><option value={currentYear}>{buddhistYear}</option><option value={currentYear + 1}>{buddhistYear + 1}</option></select></label>
          <button className="secondary" onClick={() => query.refetch()}><RefreshCcw size={16} /> อัปเดต</button>
        </div>
      </section>
      {query.isError && <div className="callout danger"><AlertTriangle size={20} /><span>โหลดข้อมูลไม่ได้ กรุณาตรวจสอบ API และเข้าสู่ระบบ</span></div>}
      <section className="metrics-grid">
        <MetricCard title="รอบ PM ทั้งปี" value={data?.total_pm_slots ?? 0} note={`แผนปี ${year + 543}`} tone="navy" icon={Layers3} />
        <MetricCard title="โรงพยาบาลยืนยัน" value={data?.confirmed_appointments ?? 0} note="ยืนยันวันนัดล่วงหน้า" tone="green" icon={CircleCheckBig} />
        <MetricCard title="รอการยืนยัน" value={data?.pending_confirmation ?? 0} note="ส่งข้อเสนอแล้ว" tone="amber" icon={Clock3} />
        <MetricCard title="ยังไม่ได้นัด" value={data?.unscheduled_slots ?? 0} note="PM Slot ไม่มีนัดปัจจุบัน" tone="blue" icon={CalendarCheck2} />
      </section>
      <section className="dashboard-columns">
        <article className="panel">
          <div className="panel-header"><div><span className="panel-kicker">งานที่ต้องติดตาม</span><h2>คิวปฏิบัติการ</h2></div><button className="text-button">ดูทั้งหมด <ArrowUpRight size={15} /></button></div>
          <div className="queue-list">
            <div><span className="queue-icon red"><AlertTriangle /></span><p><strong>คำขอเลื่อนนัด</strong><small>รอ Admin ตรวจสอบและเสนอวันใหม่</small></p><b>{data?.reschedule_requests ?? 0}</b></div>
            <div><span className="queue-icon amber"><Clock3 /></span><p><strong>รออนุมัติจาก Admin</strong><small>ตารางจากช่างที่จับคู่ข้อมูลแล้ว</small></p><b>{data?.pending_approval ?? 0}</b></div>
            <div><span className="queue-icon blue"><Wrench /></span><p><strong>รอบ PM ค้างนัด</strong><small>เดือนตามแผนผ่านแล้วและยังไม่มีนัด</small></p><b>{data?.unscheduled_backlog ?? 0}</b></div>
          </div>
        </article>
        <article className="panel health-panel">
          <div className="panel-header"><div><span className="panel-kicker">INTEGRATION HEALTH</span><h2>สถานะการเชื่อมต่อ</h2></div></div>
          <div className="health-row"><span><i className="status-dot mock" /> LINE Messaging API</span><em>Mock</em></div>
          <div className="health-row"><span><i className="status-dot mock" /> Google Workspace</span><em>Mock</em></div>
          <div className="health-row"><span><i className="status-dot off" /> Gemini</span><em>ปิดใช้งาน</em></div>
          <div className="health-row"><span><i className={(data?.failed_notifications ?? 0) > 0 ? 'status-dot error' : 'status-dot ok'} /> Notification jobs</span><em>{data?.failed_notifications ?? 0} ผิดพลาด</em></div>
        </article>
      </section>
      <div className="scope-note"><CalendarCheck2 size={18} /><span><strong>ความหมายของ “ยืนยันแล้ว”</strong> โรงพยาบาลยอมรับวันนัดล่วงหน้า ระบบไม่ถือว่าเป็นหลักฐานว่างาน PM ดำเนินการเสร็จแล้ว</span></div>
    </>
  )
}

export function Placeholder({ title }: { title: string }) {
  return <section className="page-heading"><div><p className="eyebrow">BA CHILLER SERVICE & PM</p><h1>{title}</h1><p>โมดูลนี้เชื่อมกับ business API และสิทธิ์ผู้ใช้งานจากระบบกลาง</p></div></section>
}

type Hospital = { id: string; hospital_code: string; hospital_name: string; short_name: string | null; active: boolean }

export function HospitalsPage() {
  const client = useQueryClient()
  const query = useQuery({ queryKey: ['hospitals'], queryFn: () => api<Hospital[]>('/hospitals') })
  const [form, setForm] = useState({ hospital_code: '', hospital_name: '', short_name: '' })
  const create = useMutation({
    mutationFn: () => api<Hospital>('/hospitals', { method: 'POST', body: JSON.stringify(form) }),
    onSuccess: () => { setForm({ hospital_code: '', hospital_name: '', short_name: '' }); client.invalidateQueries({ queryKey: ['hospitals'] }) },
  })
  return <>
    <section className="page-heading"><div><p className="eyebrow">MASTER DATA</p><h1>โรงพยาบาล</h1><p>ใช้รหัสถาวรและ aliases เพื่อจับคู่ชื่อจากตารางช่าง</p></div></section>
    <section className="workspace-grid">
      <article className="panel"><div className="panel-header"><h2>รายการโรงพยาบาล</h2><span className="count-badge">{query.data?.length ?? 0}</span></div>
        <div className="data-list">{query.data?.map((hospital) => <div key={hospital.id}><span className="code-chip">{hospital.hospital_code}</span><p><strong>{hospital.hospital_name}</strong><small>{hospital.short_name || 'ยังไม่มีชื่อย่อ'}</small></p><i className={hospital.active ? 'active-state' : ''}>{hospital.active ? 'ใช้งาน' : 'ปิด'}</i></div>)}</div>
      </article>
      <form className="panel form-panel" onSubmit={(event) => { event.preventDefault(); create.mutate() }}>
        <div><span className="panel-kicker">ADD MASTER DATA</span><h2>เพิ่มโรงพยาบาล</h2></div>
        <label>รหัสโรงพยาบาล<input value={form.hospital_code} onChange={(event) => setForm({ ...form, hospital_code: event.target.value })} required /></label>
        <label>ชื่อโรงพยาบาล<input value={form.hospital_name} onChange={(event) => setForm({ ...form, hospital_name: event.target.value })} required /></label>
        <label>ชื่อย่อ<input value={form.short_name} onChange={(event) => setForm({ ...form, short_name: event.target.value })} /></label>
        {create.error && <div className="login-error">{create.error.message}</div>}
        <button className="primary" disabled={create.isPending}>บันทึกโรงพยาบาล</button>
      </form>
    </section>
  </>
}

export function PlannerPage() {
  const [frequency, setFrequency] = useState(4)
  const [startMonth, setStartMonth] = useState(1)
  const [year, setYear] = useState(currentYear + 1)
  const preview = useMutation({
    mutationFn: () => api<{ display_months_th: string[] }>('/plans/preview', {
      method: 'POST', body: JSON.stringify({ plan_year: year, annual_frequency: frequency, planning_mode: 'AUTOMATIC', start_month: startMonth }),
    }),
  })
  return <>
    <section className="page-heading"><div><p className="eyebrow">ANNUAL PLANNING</p><h1>วางแผน PM รายปี</h1><p>Preview ไม่เขียนข้อมูลจริงจนกว่า Admin จะเลือกอุปกรณ์และอนุมัติ</p></div></section>
    <section className="planner-layout">
      <form className="panel form-panel" onSubmit={(event) => { event.preventDefault(); preview.mutate() }}>
        <label>ปีแผน (พ.ศ.)<input type="number" value={year + 543} onChange={(event) => setYear(Number(event.target.value) - 543)} /></label>
        <label>จำนวนครั้งต่อปี<select value={frequency} onChange={(event) => setFrequency(Number(event.target.value))}>{[1,2,3,4,6,12].map((value) => <option key={value}>{value}</option>)}</select></label>
        <label>เดือนเริ่มกระจาย<select value={startMonth} onChange={(event) => setStartMonth(Number(event.target.value))}>{['มกราคม','กุมภาพันธ์','มีนาคม','เมษายน','พฤษภาคม','มิถุนายน','กรกฎาคม','สิงหาคม','กันยายน','ตุลาคม','พฤศจิกายน','ธันวาคม'].map((month, index) => <option value={index + 1} key={month}>{month}</option>)}</select></label>
        <button className="primary">คำนวณเดือนตามแผน</button>
      </form>
      <article className="panel preview-panel"><span className="panel-kicker">PLAN PREVIEW</span><h2>เดือนที่เสนอ</h2>{preview.data ? <div className="month-grid">{preview.data.display_months_th.map((month) => <span key={month}>{month}</span>)}</div> : <p>กรอกข้อมูลแล้วกดคำนวณเพื่อดูตัวอย่าง</p>}<div className="scope-note">เดือนเริ่มต้นควบคุมการกระจายภายในปี เมื่อวนข้ามธันวาคม ลำดับแสดงผลจะเรียงตามปฏิทิน</div></article>
    </section>
  </>
}

type Draft = { id: string; draft_type: string; status: string; original_text: string; suggestions: { label: string; score: number }[] }
export function DraftsPage() {
  const query = useQuery({ queryKey: ['drafts'], queryFn: () => api<Draft[]>('/drafts?status=PENDING') })
  return <><section className="page-heading"><div><p className="eyebrow">ADMIN REVIEW</p><h1>ตรวจข้อมูลร่าง</h1><p>ข้อมูลไม่แน่ชัดจะไม่ถูกสร้างเป็น Master Data จนกว่า Admin พิจารณา</p></div></section><article className="panel"><div className="data-list">{query.data?.map((draft) => <div key={draft.id}><span className="code-chip">{draft.draft_type}</span><p><strong>{draft.original_text}</strong><small>{draft.suggestions[0] ? `ใกล้เคียง ${draft.suggestions[0].label} · ${draft.suggestions[0].score}%` : 'ไม่พบข้อมูลใกล้เคียง'}</small></p><i>{draft.status}</i></div>)}{query.data?.length === 0 && <div className="empty-state">ไม่มี Draft รอตรวจสอบ</div>}</div></article></>
}

