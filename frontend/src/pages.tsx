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
type Equipment = { id: string; equipment_code: string; hospital_id: string; equipment_name: string; model: string | null; serial_number: string | null; active: boolean }

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
  const equipment = useQuery({ queryKey: ['equipment'], queryFn: () => api<Equipment[]>('/equipment') })
  const client = useQueryClient()
  const [equipmentId, setEquipmentId] = useState('')
  const [frequency, setFrequency] = useState(4)
  const [startMonth, setStartMonth] = useState(1)
  const [year, setYear] = useState(currentYear + 1)
  const preview = useMutation({
    mutationFn: () => api<{ display_months_th: string[] }>('/plans/preview', {
      method: 'POST', body: JSON.stringify({ plan_year: year, annual_frequency: frequency, planning_mode: 'AUTOMATIC', start_month: startMonth }),
    }),
  })
  const approve = useMutation({
    mutationFn: () => api('/plans/approve', {
      method: 'POST',
      body: JSON.stringify({
        equipment_id: equipmentId,
        plan_year: year,
        annual_frequency: frequency,
        planning_mode: 'AUTOMATIC',
        start_month: startMonth,
      }),
    }),
    onSuccess: () => client.invalidateQueries({ queryKey: ['slots'] }),
  })
  return <>
    <section className="page-heading"><div><p className="eyebrow">ANNUAL PLANNING</p><h1>วางแผน PM รายปี</h1><p>Preview ไม่เขียนข้อมูลจริงจนกว่า Admin จะเลือกอุปกรณ์และอนุมัติ</p></div></section>
    <section className="planner-layout">
      <form className="panel form-panel" onSubmit={(event) => { event.preventDefault(); preview.mutate() }}>
        <label>อุปกรณ์<select value={equipmentId} onChange={(event) => setEquipmentId(event.target.value)} required><option value="">เลือกอุปกรณ์</option>{equipment.data?.map((item) => <option value={item.id} key={item.id}>{item.equipment_code} · {item.equipment_name}</option>)}</select></label>
        <label>ปีแผน (พ.ศ.)<input type="number" value={year + 543} onChange={(event) => setYear(Number(event.target.value) - 543)} /></label>
        <label>จำนวนครั้งต่อปี<select value={frequency} onChange={(event) => setFrequency(Number(event.target.value))}>{[1,2,3,4,6,12].map((value) => <option key={value}>{value}</option>)}</select></label>
        <label>เดือนเริ่มกระจาย<select value={startMonth} onChange={(event) => setStartMonth(Number(event.target.value))}>{['มกราคม','กุมภาพันธ์','มีนาคม','เมษายน','พฤษภาคม','มิถุนายน','กรกฎาคม','สิงหาคม','กันยายน','ตุลาคม','พฤศจิกายน','ธันวาคม'].map((month, index) => <option value={index + 1} key={month}>{month}</option>)}</select></label>
        <button className="secondary" type="submit">คำนวณเดือนตามแผน</button>
        <button className="primary" type="button" disabled={!preview.data || !equipmentId || approve.isPending} onClick={() => approve.mutate()}>อนุมัติและสร้าง PM Slots</button>
        {approve.isSuccess && <div className="success-note">อนุมัติแผนและสร้าง Slots สำเร็จ</div>}
        {approve.error && <div className="login-error">{approve.error.message}</div>}
      </form>
      <article className="panel preview-panel"><span className="panel-kicker">PLAN PREVIEW</span><h2>เดือนที่เสนอ</h2>{preview.data ? <div className="month-grid">{preview.data.display_months_th.map((month) => <span key={month}>{month}</span>)}</div> : <p>กรอกข้อมูลแล้วกดคำนวณเพื่อดูตัวอย่าง</p>}<div className="scope-note">เดือนเริ่มต้นควบคุมการกระจายภายในปี เมื่อวนข้ามธันวาคม ลำดับแสดงผลจะเรียงตามปฏิทิน</div></article>
    </section>
  </>
}

export function EquipmentPage() {
  const client = useQueryClient()
  const hospitals = useQuery({ queryKey: ['hospitals'], queryFn: () => api<Hospital[]>('/hospitals?active=true') })
  const equipment = useQuery({ queryKey: ['equipment'], queryFn: () => api<Equipment[]>('/equipment') })
  const [form, setForm] = useState({ equipment_code: '', hospital_id: '', equipment_name: '', model: '', serial_number: '', room_location: '' })
  const create = useMutation({
    mutationFn: () => api('/equipment', { method: 'POST', body: JSON.stringify({ ...form, model: form.model || null, serial_number: form.serial_number || null, room_location: form.room_location || null }) }),
    onSuccess: () => { setForm({ equipment_code: '', hospital_id: '', equipment_name: '', model: '', serial_number: '', room_location: '' }); client.invalidateQueries({ queryKey: ['equipment'] }) },
  })
  const hospitalNames = new Map(hospitals.data?.map((hospital) => [hospital.id, hospital.hospital_name]))
  return <><section className="page-heading"><div><p className="eyebrow">MASTER DATA</p><h1>ฐานข้อมูลอุปกรณ์</h1><p>อุปกรณ์แต่ละเครื่องผูกกับโรงพยาบาลด้วย stable ID</p></div></section><section className="workspace-grid"><article className="panel"><div className="panel-header"><h2>รายการอุปกรณ์</h2><span className="count-badge">{equipment.data?.length ?? 0}</span></div><div className="data-list">{equipment.data?.map((item) => <div key={item.id}><span className="code-chip">{item.equipment_code}</span><p><strong>{item.equipment_name}</strong><small>{hospitalNames.get(item.hospital_id) ?? 'ไม่พบโรงพยาบาล'}{item.model ? ` · ${item.model}` : ''}</small></p><i className={item.active ? 'active-state' : ''}>{item.active ? 'ใช้งาน' : 'ปิด'}</i></div>)}</div></article><form className="panel form-panel" onSubmit={(event) => { event.preventDefault(); create.mutate() }}><div><span className="panel-kicker">ADD EQUIPMENT</span><h2>เพิ่มอุปกรณ์</h2></div><label>โรงพยาบาล<select value={form.hospital_id} onChange={(event) => setForm({ ...form, hospital_id: event.target.value })} required><option value="">เลือกโรงพยาบาล</option>{hospitals.data?.map((hospital) => <option value={hospital.id} key={hospital.id}>{hospital.hospital_name}</option>)}</select></label><label>รหัสอุปกรณ์<input value={form.equipment_code} onChange={(event) => setForm({ ...form, equipment_code: event.target.value })} required /></label><label>ชื่ออุปกรณ์<input value={form.equipment_name} onChange={(event) => setForm({ ...form, equipment_name: event.target.value })} required /></label><label>รุ่น<input value={form.model} onChange={(event) => setForm({ ...form, model: event.target.value })} /></label><label>Serial number<input value={form.serial_number} onChange={(event) => setForm({ ...form, serial_number: event.target.value })} /></label>{create.error && <div className="login-error">{create.error.message}</div>}<button className="primary" disabled={create.isPending}>บันทึกอุปกรณ์</button></form></section></>
}

type AppointmentSummary = { id: string; reference: string; hospital_name: string; equipment_name: string; plan_year: number; planned_month: number; scheduled_date: string; status: string; revision_number: number; confirmed_date: string | null; admin_changed_after_confirmation: boolean; notification_warning: boolean }
const statusThai: Record<string, string> = { DRAFT: 'ร่าง', PENDING_APPROVAL: 'รออนุมัติ', PENDING_CONFIRMATION: 'รอยืนยัน', CONFIRMED: 'ยืนยันแล้ว', RESCHEDULE_REQUESTED: 'ขอเลื่อนนัด', CANCELLED: 'ยกเลิก', SUPERSEDED: 'แทนที่แล้ว' }

export function AppointmentsPage({ title = 'ปฏิทินนัดหมาย', status }: { title?: string; status?: string }) {
  const query = useQuery({ queryKey: ['appointments', status], queryFn: () => api<AppointmentSummary[]>(`/appointments${status ? `?status=${status}` : ''}`) })
  return <><section className="page-heading"><div><p className="eyebrow">APPOINTMENT OPERATIONS</p><h1>{title}</h1><p>แสดงตาม scheduled date และคง plan year ของ PM Slot เดิม</p></div></section><article className="panel table-panel"><div className="responsive-table"><table><thead><tr><th>อ้างอิง</th><th>วันนัด</th><th>โรงพยาบาล / อุปกรณ์</th><th>รอบแผน</th><th>สถานะ</th><th>Revision</th></tr></thead><tbody>{query.data?.map((item) => <tr key={item.id}><td><span className="code-chip">{item.reference}</span></td><td>{new Date(`${item.scheduled_date}T00:00:00`).toLocaleDateString('th-TH', { dateStyle: 'medium' })}</td><td><strong>{item.hospital_name}</strong><small>{item.equipment_name}</small></td><td>ปี {item.plan_year + 543} · เดือน {item.planned_month}</td><td><span className={`status-pill ${item.status.toLowerCase()}`}>{statusThai[item.status] ?? item.status}</span>{item.admin_changed_after_confirmation && <small className="warning-text">ยืนยันเดิม — Admin เปลี่ยนวัน</small>}{item.notification_warning && <small className="warning-text">แจ้งเตือนไม่สำเร็จ</small>}</td><td>#{item.revision_number}</td></tr>)}</tbody></table></div>{query.data?.length === 0 && <div className="empty-state">ยังไม่มีนัดหมายในรายการนี้</div>}</article></>
}

type Intake = { id: string; source_type: string; source_event_id: string; raw_text: string | null; parsed_data: Record<string, unknown>; state: string; validation_errors: string[]; created_at: string }
export function ApprovalQueuePage() {
  const query = useQuery({ queryKey: ['intakes'], queryFn: () => api<Intake[]>('/intakes') })
  return <><section className="page-heading"><div><p className="eyebrow">ADMIN APPROVAL</p><h1>ตารางจากช่างและคิวอนุมัติ</h1><p>Intake record ยังไม่ใช่นัดที่อนุมัติแล้ว</p></div></section><article className="panel"><div className="data-list">{query.data?.map((item) => <div key={item.id}><span className="code-chip">{item.source_type}</span><p><strong>{item.raw_text || item.source_event_id}</strong><small>{item.validation_errors.length ? item.validation_errors.join(' · ') : 'แยกข้อมูลแล้ว พร้อมตรวจสอบการจับคู่'}</small></p><i>{item.state}</i></div>)}{query.data?.length === 0 && <div className="empty-state">ยังไม่มีตารางจากช่าง</div>}</div></article></>
}

type SyncEvent = { id: string; direction: string; entity_type: string; status: string; attempts: number; last_error: string | null; created_at: string }
export function GoogleSyncPage() {
  const client = useQueryClient()
  const query = useQuery({ queryKey: ['sync-events'], queryFn: () => api<SyncEvent[]>('/google-sync/events') })
  const [form, setForm] = useState({ row_key: '', hospital_code: '', hospital_name: '', short_name: '' })
  const submit = useMutation({
    mutationFn: () => api('/google-sync/hospitals', { method: 'POST', body: JSON.stringify({ ...form, operation: 'CREATE', record_id: null, expected_version: null }) }),
    onSuccess: () => { setForm({ row_key: '', hospital_code: '', hospital_name: '', short_name: '' }); client.invalidateQueries({ queryKey: ['sync-events'] }); client.invalidateQueries({ queryKey: ['hospitals'] }) },
  })
  return <><section className="page-heading"><div><p className="eyebrow">GOOGLE WORKSPACE</p><h1>Google Sheets Sync</h1><p>Spreadsheet ส่ง proposed changes ผ่าน validation และ expected version ก่อน commit</p></div></section><section className="workspace-grid"><article className="panel"><div className="panel-header"><h2>Sync events</h2><span className="count-badge">{query.data?.length ?? 0}</span></div><div className="data-list">{query.data?.map((event) => <div key={event.id}><span className="code-chip">{event.direction}</span><p><strong>{event.entity_type}</strong><small>{event.last_error || `พยายาม ${event.attempts} ครั้ง`}</small></p><i className={event.status === 'APPLIED' ? 'active-state' : ''}>{event.status}</i></div>)}</div></article><form className="panel form-panel" onSubmit={(event) => { event.preventDefault(); submit.mutate() }}><div><span className="panel-kicker">STAGED INPUT SIMULATION</span><h2>จำลอง Hospitals_Input</h2></div><label>Stable row key<input value={form.row_key} onChange={(event) => setForm({ ...form, row_key: event.target.value })} required /></label><label>รหัสโรงพยาบาล<input value={form.hospital_code} onChange={(event) => setForm({ ...form, hospital_code: event.target.value })} required /></label><label>ชื่อโรงพยาบาล<input value={form.hospital_name} onChange={(event) => setForm({ ...form, hospital_name: event.target.value })} required /></label><label>ชื่อย่อ<input value={form.short_name} onChange={(event) => setForm({ ...form, short_name: event.target.value })} /></label>{submit.error && <div className="login-error">{submit.error.message}</div>}<button className="primary" disabled={submit.isPending}>ตรวจสอบและนำเข้า</button></form></section></>
}

type LineGroup = { id: string; line_group_id: string; group_type: string; hospital_id: string | null; active: boolean }
export function LineGroupsPage() {
  const client = useQueryClient()
  const hospitals = useQuery({ queryKey: ['hospitals'], queryFn: () => api<Hospital[]>('/hospitals?active=true') })
  const groups = useQuery({ queryKey: ['line-groups'], queryFn: () => api<LineGroup[]>('/line-groups') })
  const [form, setForm] = useState({ line_group_id: '', group_type: 'HOSPITAL', hospital_id: '' })
  const create = useMutation({ mutationFn: () => api('/line-groups', { method: 'POST', body: JSON.stringify({ ...form, hospital_id: form.group_type === 'HOSPITAL' ? form.hospital_id : null }) }), onSuccess: () => { setForm({ line_group_id: '', group_type: 'HOSPITAL', hospital_id: '' }); client.invalidateQueries({ queryKey: ['line-groups'] }) } })
  const hospitalNames = new Map(hospitals.data?.map((hospital) => [hospital.id, hospital.hospital_name]))
  return <><section className="page-heading"><div><p className="eyebrow">AUTHORIZED DESTINATIONS</p><h1>LINE Group Management</h1><p>Group ID เป็นข้อมูลสิทธิ์ ห้ามอาศัยชื่อโรงพยาบาลจากข้อความแชต</p></div></section><section className="workspace-grid"><article className="panel"><div className="data-list">{groups.data?.map((group) => <div key={group.id}><span className="code-chip">{group.group_type}</span><p><strong>{group.line_group_id}</strong><small>{group.hospital_id ? hospitalNames.get(group.hospital_id) : 'กลุ่มภายในบริษัท'}</small></p><i className={group.active ? 'active-state' : ''}>{group.active ? 'อนุญาต' : 'ปิด'}</i></div>)}</div></article><form className="panel form-panel" onSubmit={(event) => { event.preventDefault(); create.mutate() }}><label>ประเภทกลุ่ม<select value={form.group_type} onChange={(event) => setForm({ ...form, group_type: event.target.value, hospital_id: '' })}><option value="HOSPITAL">Hospital</option><option value="TECHNICIAN">Technician</option><option value="ADMIN">Admin</option></select></label><label>LINE group ID<input value={form.line_group_id} onChange={(event) => setForm({ ...form, line_group_id: event.target.value })} required /></label>{form.group_type === 'HOSPITAL' && <label>โรงพยาบาล<select value={form.hospital_id} onChange={(event) => setForm({ ...form, hospital_id: event.target.value })} required><option value="">เลือกโรงพยาบาล</option>{hospitals.data?.map((hospital) => <option value={hospital.id} key={hospital.id}>{hospital.hospital_name}</option>)}</select></label>}{create.error && <div className="login-error">{create.error.message}</div>}<button className="primary">ลงทะเบียนกลุ่ม</button></form></section></>
}

export function ReportsPage() {
  const [year, setYear] = useState(currentYear)
  const query = useQuery({ queryKey: ['dashboard', year], queryFn: () => api<Metrics>(`/dashboard?year=${year}`) })
  const rows = [
    ['รอบ PM ตามแผน', query.data?.total_pm_slots ?? 0], ['นัดที่มี confirmation', query.data?.confirmed_appointments ?? 0],
    ['รอการยืนยัน', query.data?.pending_confirmation ?? 0], ['ยังไม่ได้นัด', query.data?.unscheduled_slots ?? 0],
    ['ขอเลื่อนนัด', query.data?.reschedule_requests ?? 0], ['Admin เปลี่ยนวัน', query.data?.admin_changed_appointments ?? 0],
    ['ยกเลิกนัด', query.data?.cancelled_appointments ?? 0], ['PM backlog', query.data?.unscheduled_backlog ?? 0],
  ] as const
  return <><section className="page-heading"><div><p className="eyebrow">PLANNING REPORTS</p><h1>รายงานสถานะนัดหมาย</h1><p>รายงานตาม plan year และไม่อนุมานว่างานบริการเสร็จ</p></div><div className="heading-actions"><label>ปีแผน<select value={year} onChange={(event) => setYear(Number(event.target.value))}><option value={currentYear}>{currentYear + 543}</option><option value={currentYear + 1}>{currentYear + 544}</option></select></label></div></section><article className="panel report-grid">{rows.map(([label, value]) => <div key={label}><span>{label}</span><strong>{value.toLocaleString('th-TH')}</strong></div>)}</article><div className="scope-note"><CalendarCheck2 size={18} /><span>จำนวน confirmation เป็นการยอมรับวันนัดล่วงหน้า ไม่มีข้อมูล Completed หรือ actual service count ในรายงานนี้</span></div></>
}

type Health = { status: string; database: string; integrations: Record<string, string> }
export function SettingsPage() {
  const query = useQuery({ queryKey: ['health'], queryFn: () => api<Health>('/health') })
  return <><section className="page-heading"><div><p className="eyebrow">OPERATIONS</p><h1>ตั้งค่าและสถานะระบบ</h1><p>แสดงสถานะจริงจาก backend โดยไม่จำลองว่าเชื่อมต่อสำเร็จ</p></div></section><article className="panel settings-grid"><div><span>PostgreSQL</span><strong>{query.data?.database ?? 'กำลังตรวจสอบ'}</strong></div>{Object.entries(query.data?.integrations ?? {}).map(([name, value]) => <div key={name}><span>{name}</span><strong>{value}</strong></div>)}</article><div className="callout"><AlertTriangle size={19} /><span>Notification ส่งจริงถูกปิดตามค่าเริ่มต้น ต้องตั้ง credentials, allowlist และปิด kill switch หลังได้รับอนุมัติ production เท่านั้น</span></div></>
}

type Draft = { id: string; draft_type: string; status: string; original_text: string; suggestions: { label: string; score: number }[] }
export function DraftsPage() {
  const query = useQuery({ queryKey: ['drafts'], queryFn: () => api<Draft[]>('/drafts?status=PENDING') })
  return <><section className="page-heading"><div><p className="eyebrow">ADMIN REVIEW</p><h1>ตรวจข้อมูลร่าง</h1><p>ข้อมูลไม่แน่ชัดจะไม่ถูกสร้างเป็น Master Data จนกว่า Admin พิจารณา</p></div></section><article className="panel"><div className="data-list">{query.data?.map((draft) => <div key={draft.id}><span className="code-chip">{draft.draft_type}</span><p><strong>{draft.original_text}</strong><small>{draft.suggestions[0] ? `ใกล้เคียง ${draft.suggestions[0].label} · ${draft.suggestions[0].score}%` : 'ไม่พบข้อมูลใกล้เคียง'}</small></p><i>{draft.status}</i></div>)}{query.data?.length === 0 && <div className="empty-state">ไม่มี Draft รอตรวจสอบ</div>}</div></article></>
}

