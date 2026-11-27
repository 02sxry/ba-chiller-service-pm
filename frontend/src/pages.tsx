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
  return <section className="page-heading"><div><p className="eyebrow">BA_PMnotification</p><h1>{title}</h1><p>โมดูลนี้เชื่อมกับ business API และสิทธิ์ผู้ใช้งานจากระบบกลาง</p></div></section>
}

type Hospital = { id: string; hospital_code: string; hospital_name: string; active: boolean }
type Equipment = { id: string; equipment_code: string; hospital_id: string; equipment_name: string; model: string | null; serial_number: string | null; room_location?: string | null; active: boolean }
const EQUIPMENT_NAMES = ['Varian', 'C-Rad', 'Chiller', 'VisionRT']

function normalizeEquipmentNumber(form: { equipment_name: string; serial_number: string }) {
  const serialNumber = form.serial_number.trim()
  if (!serialNumber) return ''
  const isChiller = form.equipment_name.toLowerCase() === 'chiller'
  const baseSerialNumber = serialNumber.replace(/-CH$/i, '')
  return isChiller ? `${baseSerialNumber}-CH` : baseSerialNumber
}

function equipmentPlanLabel(item: Equipment, hospitalName?: string) {
  return [
    hospitalName || 'ไม่พบโรงพยาบาล',
    item.equipment_name,
    item.model ? `รุ่น ${item.model}` : null,
    item.serial_number ? `เลขเครื่อง ${item.serial_number}` : null,
    item.room_location ? `สถานที่ ${item.room_location}` : null,
  ].filter(Boolean).join(' · ')
}

export function HospitalsPage() {
  const client = useQueryClient()
  const query = useQuery({ queryKey: ['hospitals', 'active'], queryFn: () => api<Hospital[]>('/hospitals?active=true') })
  const [form, setForm] = useState({ hospital_code: '', hospital_name: '' })
  const create = useMutation({
    mutationFn: () => api<Hospital>('/hospitals', { method: 'POST', body: JSON.stringify({ ...form, hospital_code: form.hospital_code.trim() || null }) }),
    onSuccess: () => { setForm({ hospital_code: '', hospital_name: '' }); client.invalidateQueries({ queryKey: ['hospitals'] }) },
  })
  return <>
    <section className="page-heading"><div><p className="eyebrow">MASTER DATA</p><h1>โรงพยาบาล</h1><p>ระบบสร้างรหัสภายในอัตโนมัติ และใช้ aliases เพื่อจับคู่ชื่อจากตารางช่าง</p></div></section>
    <section className="workspace-grid">
      <article className="panel"><div className="panel-header"><h2>รายการโรงพยาบาล</h2><span className="count-badge">{query.data?.length ?? 0}</span></div>
        <div className="data-list">{query.data?.map((hospital) => <div key={hospital.id}><p><strong>{hospital.hospital_name}</strong><small>รหัสภายใน {hospital.hospital_code}</small></p><i className={hospital.active ? 'active-state' : ''}>{hospital.active ? 'ใช้งาน' : 'ปิด'}</i></div>)}</div>
      </article>
      <form className="panel form-panel" onSubmit={(event) => { event.preventDefault(); create.mutate() }}>
        <div><span className="panel-kicker">ADD MASTER DATA</span><h2>เพิ่มโรงพยาบาล</h2></div>
        <label>ชื่อโรงพยาบาล<input value={form.hospital_name} onChange={(event) => setForm({ ...form, hospital_name: event.target.value })} required /></label>
        {create.error && <div className="login-error">{create.error.message}</div>}
        <button className="primary" disabled={create.isPending}>บันทึกโรงพยาบาล</button>
      </form>
    </section>
  </>
}

export function PlannerPage() {
  const equipment = useQuery({ queryKey: ['equipment'], queryFn: () => api<Equipment[]>('/equipment') })
  const hospitals = useQuery({ queryKey: ['hospitals', 'active'], queryFn: () => api<Hospital[]>('/hospitals?active=true') })
  const client = useQueryClient()
  const [equipmentId, setEquipmentId] = useState('')
  const [frequency, setFrequency] = useState(4)
  const [startMonth, setStartMonth] = useState(1)
  const [year, setYear] = useState(currentYear + 1)
  const hospitalNames = new Map(hospitals.data?.map((hospital) => [hospital.id, hospital.hospital_name]))
  const activeHospitalIds = new Set(hospitals.data?.map((hospital) => hospital.id))
  const preview = useMutation({
    mutationFn: () => api<{ display_periods_th: string[] }>('/plans/preview', {
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
  const recalculate = useMutation({
    mutationFn: () => api('/plans/recalculate', {
      method: 'PUT',
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
        <label>โรงพยาบาลและอุปกรณ์<select value={equipmentId} onChange={(event) => setEquipmentId(event.target.value)} required><option value="">เลือกโรงพยาบาลและอุปกรณ์</option>{equipment.data?.filter((item) => item.active && activeHospitalIds.has(item.hospital_id)).map((item) => <option value={item.id} key={item.id}>{equipmentPlanLabel(item, hospitalNames.get(item.hospital_id))}</option>)}</select></label>
        <label>ปีแผน (พ.ศ.)<input type="number" value={year + 543} onChange={(event) => setYear(Number(event.target.value) - 543)} /></label>
        <label>จำนวนครั้งต่อปี<select value={frequency} onChange={(event) => setFrequency(Number(event.target.value))}>{[1,2,3,4,6,12].map((value) => <option key={value}>{value}</option>)}</select></label>
        <label>เดือนเริ่มกระจาย<select value={startMonth} onChange={(event) => setStartMonth(Number(event.target.value))}>{['มกราคม','กุมภาพันธ์','มีนาคม','เมษายน','พฤษภาคม','มิถุนายน','กรกฎาคม','สิงหาคม','กันยายน','ตุลาคม','พฤศจิกายน','ธันวาคม'].map((month, index) => <option value={index + 1} key={month}>{month}</option>)}</select></label>
        <button className="secondary" type="submit">คำนวณเดือนตามแผน</button>
        <button className="primary" type="button" disabled={!preview.data || !equipmentId || approve.isPending} onClick={() => approve.mutate()}>อนุมัติและสร้าง PM Slots</button>
        <button className="secondary" type="button" disabled={!preview.data || !equipmentId || recalculate.isPending} onClick={() => window.confirm('คำนวณรอบของแผนเดิมใหม่ใช่หรือไม่ ระบบจะทำได้เฉพาะแผนที่ยังไม่มีนัดหมาย') && recalculate.mutate()}>คำนวณแผนเดิมใหม่</button>
        {approve.isSuccess && <div className="success-note">อนุมัติแผนและสร้าง Slots สำเร็จ</div>}
        {recalculate.isSuccess && <div className="success-note">คำนวณรอบของแผนเดิมใหม่แล้ว</div>}
        {(approve.error || recalculate.error) && <div className="login-error">{(approve.error || recalculate.error)?.message}</div>}
      </form>
      <article className="panel preview-panel"><span className="panel-kicker">PLAN PREVIEW</span><h2>รอบที่เสนอ</h2>{preview.data ? <div className="month-grid">{preview.data.display_periods_th.map((period) => <span key={period}>{period}</span>)}</div> : <p>กรอกข้อมูลแล้วกดคำนวณเพื่อดูตัวอย่าง</p>}<div className="scope-note">ระบบนับต่อเนื่องจากเดือนเริ่มต้นเป็นเวลา 12 เดือน และแสดงปีให้ชัดเจนเมื่อรอบข้ามปี</div></article>
    </section>
  </>
}

export function EquipmentPage() {
  const client = useQueryClient()
  const hospitals = useQuery({ queryKey: ['hospitals', 'active'], queryFn: () => api<Hospital[]>('/hospitals?active=true') })
  const equipment = useQuery({ queryKey: ['equipment'], queryFn: () => api<Equipment[]>('/equipment') })
  const me = useQuery({ queryKey: ['current-user'], queryFn: () => api<{ role: string }>('/auth/me') })
  const [form, setForm] = useState({ hospital_id: '', equipment_name: '', model: '', serial_number: '', room_location: '' })
  const create = useMutation({
    mutationFn: () => api('/equipment', { method: 'POST', body: JSON.stringify({ ...form, model: form.model || null, serial_number: normalizeEquipmentNumber(form) || null, room_location: form.room_location || null }) }),
    onSuccess: () => { setForm({ hospital_id: '', equipment_name: '', model: '', serial_number: '', room_location: '' }); client.invalidateQueries({ queryKey: ['equipment'] }) },
  })
  const archive = useMutation({
    mutationFn: (id: string) => api<Equipment>(`/equipment/${id}`, { method: 'DELETE' }),
    onSuccess: () => {
      client.invalidateQueries({ queryKey: ['equipment'] })
      client.invalidateQueries({ queryKey: ['equipment-archive'] })
      client.invalidateQueries({ queryKey: ['slots'] })
      client.invalidateQueries({ queryKey: ['dashboard'] })
      client.invalidateQueries({ queryKey: ['appointments'] })
    },
  })
  const hospitalNames = new Map(hospitals.data?.map((hospital) => [hospital.id, hospital.hospital_name]))
  const activeHospitalIds = new Set(hospitals.data?.map((hospital) => hospital.id))
  return <>
    <section className="page-heading"><div><p className="eyebrow">MASTER DATA</p><h1>ฐานข้อมูลอุปกรณ์</h1><p>ระบบสร้างรหัสภายในให้อัตโนมัติ ผู้ใช้ไม่ต้องกรอกรหัส · อุปกรณ์ที่เก็บแล้วจะอยู่ใน Archive และจะปิดแผน PM ที่ยังใช้งานอยู่ตามไปด้วย</p></div></section>
    <section className="workspace-grid">
      <article className="panel">
        <div className="panel-header"><h2>รายการอุปกรณ์</h2><span className="count-badge">{equipment.data?.filter((item) => item.active && activeHospitalIds.has(item.hospital_id)).length ?? 0}</span></div>
        <div className="data-list">{equipment.data?.filter((item) => item.active && activeHospitalIds.has(item.hospital_id)).map((item) => <div key={item.id}><p><strong>{item.equipment_name}</strong><small>{hospitalNames.get(item.hospital_id) ?? 'ไม่พบโรงพยาบาล'}{item.model ? ` · รุ่น ${item.model}` : ''}{item.serial_number ? ` · เลขเครื่อง ${item.serial_number}` : ''}{item.room_location ? ` · สถานที่ ${item.room_location}` : ''}</small></p><i className="active-state">ใช้งาน</i>{me.data?.role === 'ADMIN' && <button className="text-button" type="button" onClick={() => window.confirm(`เก็บ ${item.equipment_name} เข้า Archive ใช่หรือไม่`) && archive.mutate(item.id)}>เก็บเข้า Archive</button>}</div>)}</div>
      </article>
      <form className="panel form-panel" onSubmit={(event) => { event.preventDefault(); create.mutate() }}>
        <div><span className="panel-kicker">ADD EQUIPMENT</span><h2>เพิ่มอุปกรณ์</h2></div>
        <label>โรงพยาบาล<select value={form.hospital_id} onChange={(event) => setForm({ ...form, hospital_id: event.target.value })} required><option value="">เลือกโรงพยาบาล</option>{hospitals.data?.map((hospital) => <option value={hospital.id} key={hospital.id}>{hospital.hospital_name}</option>)}</select></label>
        <label>ชื่ออุปกรณ์<select value={form.equipment_name} onChange={(event) => setForm({ ...form, equipment_name: event.target.value })} required><option value="">เลือกชื่ออุปกรณ์</option>{EQUIPMENT_NAMES.map((name) => <option value={name} key={name}>{name}</option>)}</select></label>
        <label>รุ่น<input value={form.model} onChange={(event) => setForm({ ...form, model: event.target.value })} placeholder="ถ้ามีให้กรอก" /></label>
        <label>เลขเครื่อง<input value={form.serial_number} onChange={(event) => setForm({ ...form, serial_number: event.target.value })} onBlur={() => setForm({ ...form, serial_number: normalizeEquipmentNumber(form) })} required placeholder="เช่น 001" />{form.equipment_name === 'Chiller' && <small>ระบบจะเติม -CH ต่อท้ายอัตโนมัติ</small>}</label>
        <label>สถานที่ติดตั้ง<input value={form.room_location} onChange={(event) => setForm({ ...form, room_location: event.target.value })} /></label>
        {(create.error || archive.error) && <div className="login-error">{(create.error || archive.error)?.message}</div>}
        <button className="primary" disabled={create.isPending}>บันทึกอุปกรณ์</button>
      </form>
    </section>
  </>
}

export function EquipmentArchivePage() {
  const client = useQueryClient()
  const hospitals = useQuery({ queryKey: ['hospitals', 'all'], queryFn: () => api<Hospital[]>('/hospitals') })
  const archived = useQuery({ queryKey: ['equipment-archive'], queryFn: () => api<Equipment[]>('/equipment/archive') })
  const remove = useMutation({
    mutationFn: (id: string) => api<Equipment>(`/equipment/${id}/permanent`, { method: 'DELETE' }),
    onSuccess: () => { client.invalidateQueries({ queryKey: ['equipment-archive'] }); client.invalidateQueries({ queryKey: ['equipment'] }) },
  })
  const hospitalNames = new Map(hospitals.data?.map((hospital) => [hospital.id, hospital.hospital_name]))
  return <>
    <section className="page-heading"><div><p className="eyebrow">EQUIPMENT ARCHIVE</p><h1>Archive อุปกรณ์</h1><p>อุปกรณ์ที่เก็บจากหน้าฐานข้อมูลอุปกรณ์ การลบถาวรทำได้เฉพาะหน้านี้และเฉพาะ Admin ถ้ามีนัดหมายอยู่ ระบบจะให้เก็บประวัติไว้</p></div></section>
    <article className="panel">
      <div className="panel-header"><h2>รายการใน Archive</h2><span className="count-badge">{archived.data?.length ?? 0}</span></div>
      {remove.error && <div className="login-error">{remove.error.message}</div>}
      <div className="data-list">{archived.data?.map((item) => <div key={item.id}><p><strong>{item.equipment_name}</strong><small>{item.equipment_code} · {hospitalNames.get(item.hospital_id) ?? 'ไม่พบโรงพยาบาล'}{item.model ? ` · รุ่น ${item.model}` : ''}{item.serial_number ? ` · เลขเครื่อง ${item.serial_number}` : ''}</small></p><i>Archived</i><button className="text-button" type="button" onClick={() => window.confirm(`ลบ ${item.equipment_name} ถาวรใช่หรือไม่\n\nแผน PM ที่ปิดแล้วจะถูกลบด้วย และการลบนี้ย้อนกลับไม่ได้`) && remove.mutate(item.id)}>ลบถาวร</button></div>)}{archived.data?.length === 0 && <div className="empty-state">ยังไม่มีอุปกรณ์ใน Archive</div>}</div>
    </article>
  </>
}

export function DatabaseEntryPage() {
  const client = useQueryClient();
  const hospitals = useQuery({
    queryKey: ["hospitals", "active"],
    queryFn: () => api<Hospital[]>("/hospitals?active=true"),
  });
  const equipment = useQuery({
    queryKey: ["equipment"],
    queryFn: () => api<Equipment[]>("/equipment"),
  });
  const activeHospitalIds = new Set(
    hospitals.data?.map((hospital) => hospital.id),
  );
  const [hospitalForm, setHospitalForm] = useState({ hospital_name: "" });
  const [equipmentForm, setEquipmentForm] = useState({
    hospital_id: "",
    equipment_name: "",
    model: "",
    serial_number: "",
    room_location: "",
  });
  const [planForm, setPlanForm] = useState({
    equipment_id: "",
    year: currentYear + 1,
    frequency: 4,
    start_month: 1,
  });
  const [planPreview, setPlanPreview] = useState<string[]>([]);
  const [editingHospital, setEditingHospital] = useState<Hospital | null>(null);
  const [editingEquipment, setEditingEquipment] = useState<Equipment | null>(
    null,
  );
  const createHospital = useMutation({
    mutationFn: () =>
      api<Hospital>("/hospitals", {
        method: "POST",
        body: JSON.stringify(hospitalForm),
      }),
    onSuccess: () => {
      setHospitalForm({ hospital_name: "" });
      client.invalidateQueries({ queryKey: ["hospitals"] });
    },
  });
  const updateHospital = useMutation({
    mutationFn: () =>
      api<Hospital>(`/hospitals/${editingHospital?.id}`, {
        method: "PATCH",
        body: JSON.stringify(hospitalForm),
      }),
    onSuccess: () => {
      setEditingHospital(null);
      setHospitalForm({ hospital_name: "" });
      client.invalidateQueries({ queryKey: ["hospitals"] });
    },
  });
  const deactivateHospital = useMutation({
    mutationFn: (id: string) =>
      api<Hospital>(`/hospitals/${id}`, { method: "DELETE" }),
    onSuccess: () => client.invalidateQueries({ queryKey: ["hospitals"] }),
  });
  const createEquipment = useMutation({
    mutationFn: () =>
      api<Equipment>("/equipment", {
        method: "POST",
        body: JSON.stringify({
          ...equipmentForm,
          model: equipmentForm.model || null,
          serial_number: normalizeEquipmentNumber(equipmentForm) || null,
          room_location: equipmentForm.room_location || null,
        }),
      }),
    onSuccess: () => {
      setEquipmentForm({
        hospital_id: "",
        equipment_name: "",
        model: "",
        serial_number: "",
        room_location: "",
      });
      client.invalidateQueries({ queryKey: ["equipment"] });
    },
  });
  const updateEquipment = useMutation({
    mutationFn: () =>
      api<Equipment>(`/equipment/${editingEquipment?.id}`, {
        method: "PATCH",
        body: JSON.stringify({
          ...equipmentForm,
          model: equipmentForm.model || null,
          serial_number: normalizeEquipmentNumber(equipmentForm) || null,
          room_location: equipmentForm.room_location || null,
        }),
      }),
    onSuccess: () => {
      setEditingEquipment(null);
      setEquipmentForm({
        hospital_id: "",
        equipment_name: "",
        model: "",
        serial_number: "",
        room_location: "",
      });
      client.invalidateQueries({ queryKey: ["equipment"] });
    },
  });
  const deactivateEquipment = useMutation({
    mutationFn: (id: string) =>
      api<Equipment>(`/equipment/${id}`, { method: "DELETE" }),
    onSuccess: () => {
      client.invalidateQueries({ queryKey: ["equipment"] });
      client.invalidateQueries({ queryKey: ["equipment-archive"] });
      client.invalidateQueries({ queryKey: ["slots"] });
      client.invalidateQueries({ queryKey: ["dashboard"] });
      client.invalidateQueries({ queryKey: ["appointments"] });
    },
  });
  const previewPlan = useMutation({
    mutationFn: () =>
      api<{ display_periods_th: string[] }>("/plans/preview", {
        method: "POST",
        body: JSON.stringify({
          plan_year: planForm.year,
          annual_frequency: planForm.frequency,
          planning_mode: "AUTOMATIC",
          start_month: planForm.start_month,
        }),
      }),
    onSuccess: (data) => setPlanPreview(data.display_periods_th),
  });
  const createPlan = useMutation({
    mutationFn: () =>
      api("/plans/approve", {
        method: "POST",
        body: JSON.stringify({
          equipment_id: planForm.equipment_id,
          plan_year: planForm.year,
          annual_frequency: planForm.frequency,
          planning_mode: "AUTOMATIC",
          start_month: planForm.start_month,
        }),
      }),
    onSuccess: () => {
      setPlanPreview([]);
      client.invalidateQueries({ queryKey: ["slots"] });
      client.invalidateQueries({ queryKey: ["dashboard"] });
    },
  });
  const recalculatePlan = useMutation({
    mutationFn: () =>
      api("/plans/recalculate", {
        method: "PUT",
        body: JSON.stringify({
          equipment_id: planForm.equipment_id,
          plan_year: planForm.year,
          annual_frequency: planForm.frequency,
          planning_mode: "AUTOMATIC",
          start_month: planForm.start_month,
        }),
      }),
    onSuccess: () => {
      client.invalidateQueries({ queryKey: ["slots"] });
      client.invalidateQueries({ queryKey: ["dashboard"] });
    },
  });
  const months = [
    "มกราคม",
    "กุมภาพันธ์",
    "มีนาคม",
    "เมษายน",
    "พฤษภาคม",
    "มิถุนายน",
    "กรกฎาคม",
    "สิงหาคม",
    "กันยายน",
    "ตุลาคม",
    "พฤศจิกายน",
    "ธันวาคม",
  ];
  return (
    <>
      <section className="page-heading">
        <div>
          <p className="eyebrow">DATABASE ENTRY</p>
          <h1>กรอกข้อมูลฐานข้อมูล</h1>
          <p>
            หน้า Admin สำหรับเพิ่ม แก้ไข และปิดใช้งานข้อมูลหลัก
            ข้อมูลจะบันทึกเข้า SQL Server
          </p>
        </div>
      </section>
      <section className="workspace-grid">
        <form
          className="panel form-panel"
          onSubmit={(event) => {
            event.preventDefault();
            editingHospital ? updateHospital.mutate() : createHospital.mutate();
          }}
        >
          <div>
            <span className="panel-kicker">STEP 1</span>
            <h2>{editingHospital ? "แก้ไขโรงพยาบาล" : "เพิ่มโรงพยาบาล"}</h2>
          </div>
          <label>
            ชื่อโรงพยาบาล
            <input
              value={hospitalForm.hospital_name}
              onChange={(event) =>
                setHospitalForm({
                  ...hospitalForm,
                  hospital_name: event.target.value,
                })
              }
              required
            />
          </label>
          {(createHospital.error || updateHospital.error) && (
            <div className="login-error">
              {(createHospital.error || updateHospital.error)?.message}
            </div>
          )}
          <button
            className="primary"
            disabled={createHospital.isPending || updateHospital.isPending}
          >
            {editingHospital ? "บันทึกการแก้ไข" : "บันทึกโรงพยาบาล"}
          </button>
          {editingHospital && (
            <button
              className="secondary"
              type="button"
              onClick={() => {
                setEditingHospital(null);
                setHospitalForm({ hospital_name: "" });
              }}
            >
              ยกเลิกการแก้ไข
            </button>
          )}
        </form>
        <form
          className="panel form-panel"
          onSubmit={(event) => {
            event.preventDefault();
            editingEquipment
              ? updateEquipment.mutate()
              : createEquipment.mutate();
          }}
        >
          <div>
            <span className="panel-kicker">STEP 2</span>
            <h2>{editingEquipment ? "แก้ไขอุปกรณ์" : "เพิ่มอุปกรณ์"}</h2>
          </div>
          <label>
            โรงพยาบาล
            <select
              value={equipmentForm.hospital_id}
              onChange={(event) =>
                setEquipmentForm({
                  ...equipmentForm,
                  hospital_id: event.target.value,
                })
              }
              required
            >
              <option value="">เลือกโรงพยาบาล</option>
              {hospitals.data?.map((hospital) => (
                <option value={hospital.id} key={hospital.id}>
                  {hospital.hospital_name}
                </option>
              ))}
            </select>
          </label>
          <label>
            ชื่ออุปกรณ์
            <select
              value={equipmentForm.equipment_name}
              onChange={(event) =>
                setEquipmentForm({
                  ...equipmentForm,
                  equipment_name: event.target.value,
                })
              }
              required
            >
              <option value="">เลือกชื่ออุปกรณ์</option>
              {EQUIPMENT_NAMES.map((name) => (
                <option value={name} key={name}>
                  {name}
                </option>
              ))}
            </select>
          </label>
          <label>
            รุ่น
            <input
              value={equipmentForm.model}
              onChange={(event) =>
                setEquipmentForm({
                  ...equipmentForm,
                  model: event.target.value,
                })
              }
              placeholder="ถ้ามีให้กรอก"
            />
          </label>
          <label>
            เลขเครื่อง
            <input
              value={equipmentForm.serial_number}
              onChange={(event) =>
                setEquipmentForm({
                  ...equipmentForm,
                  serial_number: event.target.value,
                })
              }
              onBlur={() =>
                setEquipmentForm({
                  ...equipmentForm,
                  serial_number: normalizeEquipmentNumber(equipmentForm),
                })
              }
              required
              placeholder="เช่น 001"
            />
            {equipmentForm.equipment_name === "Chiller" && (
              <small>ระบบจะเติม -CH ต่อท้ายอัตโนมัติ</small>
            )}
          </label>
          <label>
            สถานที่ติดตั้ง
            <input
              value={equipmentForm.room_location}
              onChange={(event) =>
                setEquipmentForm({
                  ...equipmentForm,
                  room_location: event.target.value,
                })
              }
            />
          </label>
          {(createEquipment.error || updateEquipment.error) && (
            <div className="login-error">
              {(createEquipment.error || updateEquipment.error)?.message}
            </div>
          )}
          <button
            className="primary"
            disabled={createEquipment.isPending || updateEquipment.isPending}
          >
            {editingEquipment ? "บันทึกการแก้ไข" : "บันทึกอุปกรณ์"}
          </button>
          {editingEquipment && (
            <button
              className="secondary"
              type="button"
              onClick={() => {
                setEditingEquipment(null);
                setEquipmentForm({
                  hospital_id: "",
                  equipment_name: "",
                  model: "",
                  serial_number: "",
                  room_location: "",
                });
              }}
            >
              ยกเลิกการแก้ไข
            </button>
          )}
        </form>
        <form
          className="panel form-panel"
          onSubmit={(event) => {
            event.preventDefault();
            previewPlan.mutate();
          }}
        >
          <div>
            <span className="panel-kicker">STEP 3</span>
            <h2>สร้างแผน PM</h2>
          </div>
          <label>
            โรงพยาบาลและอุปกรณ์
            <select
              value={planForm.equipment_id}
              onChange={(event) =>
                setPlanForm({ ...planForm, equipment_id: event.target.value })
              }
              required
            >
              <option value="">เลือกโรงพยาบาลและอุปกรณ์</option>
              {equipment.data
                ?.filter(
                  (item) =>
                    item.active && activeHospitalIds.has(item.hospital_id),
                )
                .map((item) => (
                  <option value={item.id} key={item.id}>
                    {equipmentPlanLabel(
                      item,
                      hospitals.data?.find(
                        (hospital) => hospital.id === item.hospital_id,
                      )?.hospital_name,
                    )}
                  </option>
                ))}
            </select>
          </label>
          <label>
            ปีแผน (พ.ศ.)
            <input
              type="number"
              value={planForm.year + 543}
              onChange={(event) =>
                setPlanForm({
                  ...planForm,
                  year: Number(event.target.value) - 543,
                })
              }
              required
            />
          </label>
          <label>
            จำนวนครั้งต่อปี
            <select
              value={planForm.frequency}
              onChange={(event) =>
                setPlanForm({
                  ...planForm,
                  frequency: Number(event.target.value),
                })
              }
            >
              {[1, 2, 3, 4, 6, 12].map((value) => (
                <option key={value} value={value}>
                  {value} ครั้ง
                </option>
              ))}
            </select>
          </label>
          <label>
            เดือนเริ่มต้น
            <select
              value={planForm.start_month}
              onChange={(event) =>
                setPlanForm({
                  ...planForm,
                  start_month: Number(event.target.value),
                })
              }
            >
              {months.map((month, index) => (
                <option value={index + 1} key={month}>
                  {month}
                </option>
              ))}
            </select>
          </label>
          <button
            className="secondary"
            type="submit"
            disabled={previewPlan.isPending}
          >
            คำนวณแผน
          </button>
          {planPreview.length > 0 && (
            <>
              <div className="month-grid">
                {planPreview.map((month) => (
                  <span key={month}>{month}</span>
                ))}
              </div>
              <button
                className="primary"
                type="button"
                disabled={createPlan.isPending}
                onClick={() => createPlan.mutate()}
              >
                ยืนยันและสร้างรอบ PM
              </button>
              <button
                className="secondary"
                type="button"
                disabled={recalculatePlan.isPending}
                onClick={() =>
                  window.confirm(
                    "คำนวณรอบของแผนเดิมใหม่ใช่หรือไม่ ระบบจะทำได้เฉพาะแผนที่ยังไม่มีนัดหมาย",
                  ) && recalculatePlan.mutate()
                }
              >
                คำนวณแผนเดิมใหม่
              </button>
            </>
          )}
          {(createPlan.error || recalculatePlan.error) && (
            <div className="login-error">
              {(createPlan.error || recalculatePlan.error)?.message}
            </div>
          )}
          {createPlan.isSuccess && (
            <div className="success-note">สร้างแผน PM และรอบ PM แล้ว</div>
          )}
          {recalculatePlan.isSuccess && (
            <div className="success-note">คำนวณรอบของแผนเดิมใหม่แล้ว</div>
          )}
        </form>
      </section>
      <section className="workspace-grid">
        <article className="panel">
          <div className="panel-header">
            <h2>โรงพยาบาลที่มีอยู่</h2>
            <span className="count-badge">{hospitals.data?.length ?? 0}</span>
          </div>
          <div className="data-list">
            {hospitals.data?.map((hospital) => (
              <div key={hospital.id}>
                <p>
                  <strong>{hospital.hospital_name}</strong>
                  <small>รหัสภายใน {hospital.hospital_code}</small>
                </p>
                <button
                  className="text-button"
                  type="button"
                  onClick={() => {
                    setEditingHospital(hospital);
                    setHospitalForm({ hospital_name: hospital.hospital_name });
                  }}
                >
                  แก้ไข
                </button>
                <button
                  className="text-button"
                  type="button"
                  onClick={() =>
                    window.confirm(
                      `ปิดใช้งาน ${hospital.hospital_name} ใช่หรือไม่`,
                    ) && deactivateHospital.mutate(hospital.id)
                  }
                >
                  ปิดใช้งาน
                </button>
              </div>
            ))}
          </div>
        </article>
        <article className="panel">
          <div className="panel-header">
            <h2>อุปกรณ์ที่มีอยู่</h2>
            <span className="count-badge">
              {equipment.data?.filter(
                (item) =>
                  item.active && activeHospitalIds.has(item.hospital_id),
              ).length ?? 0}
            </span>
          </div>
          <div className="data-list">
            {equipment.data
              ?.filter(
                (item) =>
                  item.active && activeHospitalIds.has(item.hospital_id),
              )
              .map((item) => (
                <div key={item.id}>
                  <p>
                    <strong>{item.equipment_name}</strong>
                    <small>
                      {hospitals.data?.find(
                        (hospital) => hospital.id === item.hospital_id,
                      )?.hospital_name || "ไม่พบโรงพยาบาล"}
                      {item.model ? ` · รุ่น ${item.model}` : ""}
                      {item.serial_number
                        ? ` · เลขเครื่อง ${item.serial_number}`
                        : ""}
                      {item.room_location
                        ? ` · สถานที่ ${item.room_location}`
                        : ""}
                    </small>
                  </p>
                  <button
                    className="text-button"
                    type="button"
                    onClick={() => {
                      setEditingEquipment(item);
                      setEquipmentForm({
                        hospital_id: item.hospital_id,
                        equipment_name: item.equipment_name,
                        model: item.model || "",
                        serial_number: item.serial_number || "",
                        room_location: item.room_location || "",
                      });
                    }}
                  >
                    แก้ไข
                  </button>
                  <button
                    className="text-button"
                    type="button"
                    onClick={() =>
                      window.confirm(
                        `ปิดใช้งาน ${item.equipment_name} ใช่หรือไม่`,
                      ) && deactivateEquipment.mutate(item.id)
                    }
                  >
                    ปิดใช้งาน
                  </button>
                </div>
              ))}
          </div>
        </article>
      </section>
    </>
  );
}

type Slot = {
  id: string;
  equipment_id: string;
  yearly_plan_id: string;
  plan_year: number;
  planned_month: number;
  active: boolean;
  version: number;
};

export function SlotsPage() {
  const slots = useQuery({
    queryKey: ["slots"],
    queryFn: () => api<Slot[]>("/slots"),
  });
  const equipment = useQuery({
    queryKey: ["equipment"],
    queryFn: () => api<Equipment[]>("/equipment"),
  });
  const hospitals = useQuery({
    queryKey: ["hospitals", "all"],
    queryFn: () => api<Hospital[]>("/hospitals"),
  });
  const [equipmentId, setEquipmentId] = useState("");
  const [hospitalId, setHospitalId] = useState("");
  const [model, setModel] = useState("");
  const [year, setYear] = useState("");
  const [month, setMonth] = useState("");
  const monthNames = [
    "มกราคม",
    "กุมภาพันธ์",
    "มีนาคม",
    "เมษายน",
    "พฤษภาคม",
    "มิถุนายน",
    "กรกฎาคม",
    "สิงหาคม",
    "กันยายน",
    "ตุลาคม",
    "พฤศจิกายน",
    "ธันวาคม",
  ];
  const equipmentById = new Map(equipment.data?.map((item) => [item.id, item]));
  const hospitalById = new Map(hospitals.data?.map((item) => [item.id, item]));
  const activeHospitalIds = new Set(
    hospitals.data?.filter((item) => item.active).map((item) => item.id),
  );
  const years = [
    ...new Set(slots.data?.map((slot) => slot.plan_year) ?? []),
  ].sort((a, b) => a - b);
  const visible =
    slots.data?.filter((slot) => {
      const item = equipmentById.get(slot.equipment_id);
      return (
        (!equipmentId || slot.equipment_id === equipmentId) &&
        (!hospitalId || item?.hospital_id === hospitalId) &&
        (!model || item?.model === model) &&
        (!year || slot.plan_year === Number(year)) &&
        (!month || slot.planned_month === Number(month))
      );
    }) ?? [];
  const models = [
    ...new Set(
      equipment.data
        ?.filter(
          (item) =>
            item.active &&
            activeHospitalIds.has(item.hospital_id) &&
            (!hospitalId || item.hospital_id === hospitalId),
        )
        .map((item) => item.model)
        .filter((item): item is string => Boolean(item)) ?? [],
    ),
  ].sort();
  return (
    <>
      <section className="page-heading">
        <div>
          <p className="eyebrow">PM SLOTS</p>
          <h1>รอบ PM</h1>
          <p>รอบที่สร้างจาก PM Plan และเชื่อมต่อกับอุปกรณ์จริง</p>
        </div>
      </section>
      <section className="panel">
        <div className="heading-actions filter-row">
          <label>
            โรงพยาบาล
            <select
              value={hospitalId}
              onChange={(event) => setHospitalId(event.target.value)}
            >
              <option value="">ทั้งหมด</option>
              {hospitals.data?.filter((item) => item.active).map((item) => (
                <option value={item.id} key={item.id}>
                  {item.hospital_name}
                </option>
              ))}
            </select>
          </label>
          <label>
            เครื่อง
            <select
              value={equipmentId}
              onChange={(event) => setEquipmentId(event.target.value)}
            >
              <option value="">ทั้งหมด</option>
              {equipment.data
                ?.filter(
                  (item) =>
                    item.active &&
                    activeHospitalIds.has(item.hospital_id) &&
                    (!hospitalId || item.hospital_id === hospitalId),
                )
                .map((item) => (
                  <option value={item.id} key={item.id}>
                    {item.equipment_name}
                  </option>
                ))}
            </select>
          </label>
          <label>
            รุ่น
            <select
              value={model}
              onChange={(event) => setModel(event.target.value)}
            >
              <option value="">ทั้งหมด</option>
              {models.map((item) => (
                <option value={item} key={item}>
                  {item}
                </option>
              ))}
            </select>
          </label>
          <label>
            ปี
            <select
              value={year}
              onChange={(event) => setYear(event.target.value)}
            >
              <option value="">ทั้งหมด</option>
              {years.map((item) => (
                <option value={item} key={item}>
                  {item + 543}
                </option>
              ))}
            </select>
          </label>
          <label>
            เดือน
            <select
              value={month}
              onChange={(event) => setMonth(event.target.value)}
            >
              <option value="">ทั้งหมด</option>
              {monthNames.map((item, index) => (
                <option value={index + 1} key={item}>
                  {item}
                </option>
              ))}
            </select>
          </label>
        </div>
        <div className="data-list">
          {visible.map((slot) => {
            const item = equipmentById.get(slot.equipment_id);
            return (
              <div key={slot.id}>
                <p>
                  <strong>{item?.equipment_name ?? "ไม่พบอุปกรณ์"}</strong>
                  <small>
                    {item
                      ? `${hospitalById.get(item.hospital_id)?.hospital_name ?? ""}${item.model ? ` · รุ่น ${item.model}` : ""}`
                      : ""}{" "}
                    · ปี {slot.plan_year + 543} · เดือน {slot.planned_month}
                  </small>
                </p>
                <i className="active-state">สร้างแล้ว</i>
              </div>
            );
          })}
          {visible.length === 0 && (
            <div className="empty-state">ยังไม่มี PM Slot ตามตัวกรอง</div>
          )}
        </div>
      </section>
    </>
  );
}

type AppointmentSummary = {
  id: string;
  reference: string;
  pm_slot_id: string;
  hospital_id: string;
  equipment_id: string;
  hospital_name: string;
  equipment_name: string;
  plan_year: number;
  planned_month: number;
  scheduled_date: string;
  status: string;
  revision_number: number;
  confirmed_date: string | null;
  admin_changed_after_confirmation: boolean;
  notification_warning: boolean;
};
const statusThai: Record<string, string> = {
  DRAFT: "ร่าง",
  PENDING_APPROVAL: "รออนุมัติ",
  PENDING_CONFIRMATION: "รอยืนยัน",
  CONFIRMED: "ยืนยันแล้ว",
  RESCHEDULE_REQUESTED: "ขอเลื่อนนัด",
  CANCELLED: "ยกเลิก",
  SUPERSEDED: "แทนที่แล้ว",
};

export function AppointmentsPage({
  title = "ปฏิทินนัดหมาย",
  status,
}: {
  title?: string;
  status?: string;
}) {
  const query = useQuery({
    queryKey: ["appointments", status],
    queryFn: () =>
      api<AppointmentSummary[]>(
        `/appointments${status ? `?status=${status}` : ""}`,
      ),
  });
  const equipment = useQuery({
    queryKey: ["equipment"],
    queryFn: () => api<Equipment[]>("/equipment"),
  });
  const hospitals = useQuery({
    queryKey: ["hospitals", "all"],
    queryFn: () => api<Hospital[]>("/hospitals"),
  });
  const activeHospitalIds = new Set(
    hospitals.data?.filter((item) => item.active).map((item) => item.id),
  );
  const [equipmentId, setEquipmentId] = useState("");
  const [hospitalId, setHospitalId] = useState("");
  const visible =
    query.data?.filter(
      (item) =>
        (!equipmentId || item.equipment_id === equipmentId) &&
        (!hospitalId || item.hospital_id === hospitalId),
    ) ?? [];
  return (
    <>
      <section className="page-heading">
        <div>
          <p className="eyebrow">APPOINTMENT OPERATIONS</p>
          <h1>{title}</h1>
          <p>เลือกดูเฉพาะโรงพยาบาลหรือเครื่องที่ต้องการได้</p>
        </div>
      </section>
      <article className="panel table-panel">
        <div className="heading-actions filter-row">
          <label>
            โรงพยาบาล
            <select
              value={hospitalId}
              onChange={(event) => setHospitalId(event.target.value)}
            >
              <option value="">ทั้งหมด</option>
              {hospitals.data?.filter((item) => item.active).map((item) => (
                <option value={item.id} key={item.id}>
                  {item.hospital_name}
                </option>
              ))}
            </select>
          </label>
          <label>
            เครื่อง
            <select
              value={equipmentId}
              onChange={(event) => setEquipmentId(event.target.value)}
            >
              <option value="">ทั้งหมด</option>
              {equipment.data
                ?.filter(
                  (item) =>
                    item.active &&
                    activeHospitalIds.has(item.hospital_id) &&
                    (!hospitalId || item.hospital_id === hospitalId),
                )
                .map((item) => (
                  <option value={item.id} key={item.id}>
                    {item.equipment_name}
                  </option>
                ))}
            </select>
          </label>
        </div>
        <div className="responsive-table">
          <table>
            <thead>
              <tr>
                <th>อ้างอิง</th>
                <th>วันนัด</th>
                <th>โรงพยาบาล / อุปกรณ์</th>
                <th>รอบแผน</th>
                <th>สถานะ</th>
                <th>Revision</th>
              </tr>
            </thead>
            <tbody>
              {visible.map((item) => (
                <tr key={item.id}>
                  <td>
                    <span className="code-chip">{item.reference}</span>
                  </td>
                  <td>
                    {new Date(
                      `${item.scheduled_date}T00:00:00`,
                    ).toLocaleDateString("th-TH", { dateStyle: "medium" })}
                  </td>
                  <td>
                    <strong>{item.hospital_name}</strong>
                    <small>{item.equipment_name}</small>
                  </td>
                  <td>
                    ปี {item.plan_year + 543} · เดือน {item.planned_month}
                  </td>
                  <td>
                    <span
                      className={`status-pill ${item.status.toLowerCase()}`}
                    >
                      {statusThai[item.status] ?? item.status}
                    </span>
                    {item.admin_changed_after_confirmation && (
                      <small className="warning-text">
                        ยืนยันเดิม — Admin เปลี่ยนวัน
                      </small>
                    )}
                    {item.notification_warning && (
                      <small className="warning-text">แจ้งเตือนไม่สำเร็จ</small>
                    )}
                  </td>
                  <td>#{item.revision_number}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {visible.length === 0 && (
          <div className="empty-state">ยังไม่มีนัดหมายตามตัวกรอง</div>
        )}
      </article>
    </>
  );
}

type IntakeItem = { hospital_text?: string | null; equipment_text?: string | null; proposed_date?: string | null; notes?: string | null; appointment_id?: string }
type Intake = { id: string; source_event_id: string; raw_text: string | null; parsed_data: IntakeItem & { items?: IntakeItem[] }; state: string; validation_errors: string[] }
type IntakeSelection = { intakeId: string; index: number; item: IntakeItem }

function IntakeApprovalForm({ selection, onSuccess }: { selection: IntakeSelection; onSuccess: () => void }) {
  const [hospitalId, setHospitalId] = useState('')
  const [equipmentId, setEquipmentId] = useState('')
  const [slotId, setSlotId] = useState('')
  const [date, setDate] = useState(selection.item.proposed_date ?? '')
  const hospitals = useQuery({ queryKey: ['hospitals', 'active'], queryFn: () => api<Hospital[]>('/hospitals?active=true') })
  const equipment = useQuery({ queryKey: ['equipment'], queryFn: () => api<Equipment[]>('/equipment') })
  const slots = useQuery({ queryKey: ['slots'], queryFn: () => api<Slot[]>('/slots') })
  const appointments = useQuery({ queryKey: ['appointments', undefined], queryFn: () => api<AppointmentSummary[]>('/appointments') })
  const occupiedSlots = new Set(appointments.data?.map((appointment) => appointment.pm_slot_id))
  const availableSlots = slots.data?.filter((slot) => slot.equipment_id === equipmentId && !occupiedSlots.has(slot.id)) ?? []
  const selectedSlot = availableSlots.find((slot) => slot.id === slotId)
  const approve = useMutation({
    mutationFn: () => api(`/intakes/${selection.intakeId}/items/${selection.index}/approve`, {
      method: 'POST',
      body: JSON.stringify({
        hospital_id: hospitalId,
        equipment_id: equipmentId,
        pm_slot_id: slotId,
        scheduled_date: date,
        expected_slot_version: selectedSlot?.version,
      }),
    }),
    onSuccess,
  })
  const selectedEquipment = equipment.data?.find((item) => item.id === equipmentId)
  const [year, month, day] = date.split('-')
  const proposalDate = date ? `${day}/${month}/${String(Number(year) + 543).slice(-2)}` : ''
  const scheduledMonth = selectedSlot && `${selectedSlot.plan_year}-${String(selectedSlot.planned_month).padStart(2, '0')}`

  return <form className="panel form-panel" onSubmit={(event) => {
    event.preventDefault()
    if (selectedSlot && date) approve.mutate()
  }}>
    <h2>ตรวจข้อมูลและอนุมัตินัด</h2>
    <p>{selection.item.notes || [selection.item.hospital_text, selection.item.equipment_text].filter(Boolean).join(' · ')}</p>
    <label>โรงพยาบาล<select required value={hospitalId} onChange={(event) => {
      setHospitalId(event.target.value)
      setEquipmentId('')
      setSlotId('')
    }}>
      <option value="">เลือกโรงพยาบาล</option>
      {hospitals.data?.map((item) => <option value={item.id} key={item.id}>{item.hospital_name}</option>)}
    </select></label>
    <label>อุปกรณ์<select required value={equipmentId} disabled={!hospitalId} onChange={(event) => {
      setEquipmentId(event.target.value)
      setSlotId('')
    }}>
      <option value="">เลือกอุปกรณ์</option>
      {equipment.data?.filter((item) => item.active && item.hospital_id === hospitalId).map((item) =>
        <option value={item.id} key={item.id}>{[item.equipment_name, item.model, item.serial_number].filter(Boolean).join(' · ')}</option>
      )}
    </select></label>
    <label>วันเสนอเข้าดำเนินงาน<input type="date" required value={date} onChange={(event) => setDate(event.target.value)} /></label>
    <label>รอบ PM<select required value={slotId} disabled={!availableSlots.length} onChange={(event) => setSlotId(event.target.value)}>
      <option value="">เลือกรอบ PM</option>
      {availableSlots.map((slot) => <option value={slot.id} key={slot.id}>เดือน {slot.planned_month} / {slot.plan_year + 543}</option>)}
    </select></label>
    {equipmentId && slots.isSuccess && appointments.isSuccess && !availableSlots.length && <p>ไม่มีรอบ PM ว่างสำหรับอุปกรณ์นี้</p>}
    {date && scheduledMonth && !date.startsWith(scheduledMonth) && <p className="warning-text">วันนัดอยู่คนละเดือนกับรอบ PM ที่เลือก</p>}
    {selectedEquipment && proposalDate && <div className="scope-note">
      <span>ขออนุญาตแจ้งวันเข้า PM {selectedEquipment.equipment_name}<br />
      {selectedEquipment.room_location || 'สถานที่ติดตั้ง'} - {proposalDate}<br />
      ไม่ทราบว่าสะดวกไหมครับ</span>
    </div>}
    {(approve.error || hospitals.error || equipment.error || slots.error || appointments.error) &&
      <div className="login-error" role="alert">{(approve.error || hospitals.error || equipment.error || slots.error || appointments.error)?.message}</div>}
    <button className="primary" disabled={!selectedSlot || !date || !appointments.isSuccess || approve.isPending}>อนุมัติและสร้างนัด</button>
  </form>
}

export function ApprovalQueuePage() {
  const client = useQueryClient()
  const query = useQuery({ queryKey: ['intakes'], queryFn: () => api<Intake[]>('/intakes') })
  const [selection, setSelection] = useState<IntakeSelection | null>(null)
  const [saved, setSaved] = useState(false)
  return <>
    <section className="page-heading"><div><p className="eyebrow">ADMIN APPROVAL</p><h1>ตารางจากช่างและคิวอนุมัติ</h1><p>ตรวจชื่อโรงพยาบาล อุปกรณ์ และวันที่ก่อนอนุมัตินัด</p></div></section>
    <section className={selection ? 'workspace-grid' : undefined}>
      <article className="panel">
        {saved && <div className="success-note" role="status">สร้างนัดแล้ว · รอโรงพยาบาลยืนยัน</div>}
        {query.isError && <div className="login-error" role="alert">{query.error.message}</div>}
        <div className="data-list">
          {query.data?.flatMap((intake) => (intake.parsed_data.items ?? [intake.parsed_data]).map((item, index) => {
            const label = [item.hospital_text, item.equipment_text, item.proposed_date].filter(Boolean).join(' · ')
            const canApprove = !item.appointment_id && ['PARSED', 'NEEDS_REVIEW', 'READY_FOR_APPROVAL'].includes(intake.state)
            return <div key={`${intake.id}:${index}`}>
              <p><strong>{label || item.notes || intake.raw_text || intake.source_event_id}</strong>
                {label && <small>{item.notes || intake.raw_text}</small>}
                {intake.validation_errors.length > 0 && <small>{intake.validation_errors.join(' · ')}</small>}
              </p>
              {item.appointment_id && <i className="active-state">สร้างนัดแล้ว</i>}
              {canApprove && <button className="text-button" onClick={() => {
                setSaved(false)
                setSelection({ intakeId: intake.id, index, item })
              }}>ตรวจและสร้างนัด</button>}
            </div>
          }))}
          {query.data?.length === 0 && <div className="empty-state">ยังไม่มีตารางจากช่าง</div>}
        </div>
      </article>
      {selection && <IntakeApprovalForm
        key={`${selection.intakeId}:${selection.index}`}
        selection={selection}
        onSuccess={() => {
          setSelection(null)
          setSaved(true)
          void client.invalidateQueries({ queryKey: ['intakes'] })
          void client.invalidateQueries({ queryKey: ['appointments'] })
          void client.invalidateQueries({ queryKey: ['dashboard'] })
        }}
      />}
    </section>
  </>
}

type SyncEvent = { id: string; direction: string; entity_type: string; status: string; attempts: number; last_error: string | null; created_at: string }
export function GoogleSyncPage() {
  const client = useQueryClient()
  const query = useQuery({ queryKey: ['sync-events'], queryFn: () => api<SyncEvent[]>('/google-sync/events') })
  const action = useMutation({
    mutationFn: ({ id, kind }: { id: string; kind: 'run' | 'retry' }) => api<SyncEvent>(`/google-sync/events/${id}/${kind}`, { method: 'POST' }),
    onSuccess: () => client.invalidateQueries({ queryKey: ['sync-events'] }),
  })
  return <><section className="page-heading"><div><p className="eyebrow">GOOGLE WORKSPACE</p><h1>Google Sheets Sync</h1><p>กรอกและแก้ไขข้อมูลผ่าน Dashboard แล้วระบบส่งข้อมูลไป Google Sheets เป็นรายงาน</p></div></section><section className="workspace-grid"><article className="panel"><div className="panel-header"><h2>Sync events</h2><span className="count-badge">{query.data?.length ?? 0}</span></div><div className="data-list">{query.data?.map((event) => <div key={event.id}><span className="code-chip">{event.direction}</span><p><strong>{event.entity_type}</strong><small>{event.last_error || `พยายาม ${event.attempts} ครั้ง`}</small></p><i className={event.status === 'APPLIED' ? 'active-state' : ''}>{event.status}</i>{event.direction === 'OUTBOUND' && event.status === 'PENDING' && <button className="text-button" onClick={() => action.mutate({ id: event.id, kind: 'run' })} disabled={action.isPending}>ส่งตอนนี้</button>}{event.direction === 'OUTBOUND' && ['FAILED', 'CONFLICT'].includes(event.status) && <button className="text-button" onClick={() => action.mutate({ id: event.id, kind: 'retry' })} disabled={action.isPending}>ลองใหม่</button>}</div>)}</div></article><article className="panel form-panel"><span className="panel-kicker">DASHBOARD FIRST</span><h2>การกรอกข้อมูล</h2><p>ไม่ต้องกรอกข้อมูลซ้ำใน Google Sheets ให้สร้างหรือแก้ไขโรงพยาบาล อุปกรณ์ และแผน PM จากเมนูใน Dashboard แล้วระบบจะส่งข้อมูลไปยังชีต View ตามรอบ sync</p><p>ชีต Input ใช้เป็นพื้นที่รับข้อมูลของระบบเท่านั้น ผู้ใช้ไม่ควรแก้ไขโดยตรง</p></article></section></>
}

type LineGroup = { id: string; line_group_id: string; group_type: string; hospital_id: string | null; active: boolean }
export function LineGroupsPage() {
  const client = useQueryClient()
  const hospitals = useQuery({ queryKey: ['hospitals', 'active'], queryFn: () => api<Hospital[]>('/hospitals?active=true') })
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
  return <><section className="page-heading"><div><p className="eyebrow">OPERATIONS</p><h1>ตั้งค่าและสถานะระบบ</h1><p>แสดงสถานะจริงจาก backend โดยไม่จำลองว่าเชื่อมต่อสำเร็จ</p></div></section><article className="panel settings-grid"><div><span>SQL Server</span><strong>{query.data?.database ?? 'กำลังตรวจสอบ'}</strong></div>{Object.entries(query.data?.integrations ?? {}).map(([name, value]) => <div key={name}><span>{name}</span><strong>{value}</strong></div>)}</article><div className="callout"><AlertTriangle size={19} /><span>Notification ส่งจริงถูกปิดตามค่าเริ่มต้น ต้องตั้ง credentials, allowlist และปิด kill switch หลังได้รับอนุมัติ production เท่านั้น</span></div></>
}

type UserRecord = { id: string; username: string | null; display_name: string; role: 'ADMIN' | 'VIEWER'; active: boolean }
export function UsersPage() {
  const client = useQueryClient()
  const users = useQuery({ queryKey: ['users'], queryFn: () => api<UserRecord[]>('/users') })
  const me = useQuery({ queryKey: ['current-user'], queryFn: () => api<UserRecord>('/auth/me') })
  const [form, setForm] = useState({ username: '', display_name: '', password: '', role: 'VIEWER' })
  const [editingUser, setEditingUser] = useState<UserRecord | null>(null)
  const create = useMutation({
    mutationFn: () => api<UserRecord>('/users', { method: 'POST', body: JSON.stringify(form) }),
    onSuccess: () => { setForm({ username: '', display_name: '', password: '', role: 'VIEWER' }); client.invalidateQueries({ queryKey: ['users'] }) },
  })
  const update = useMutation({
    mutationFn: () => api<UserRecord>(`/users/${editingUser?.id}`, { method: 'PATCH', body: JSON.stringify({ display_name: form.display_name, role: form.role, ...(form.password ? { password: form.password } : {}) }) }),
    onSuccess: () => { setEditingUser(null); setForm({ username: '', display_name: '', password: '', role: 'VIEWER' }); client.invalidateQueries({ queryKey: ['users'] }); client.invalidateQueries({ queryKey: ['current-user'] }) },
  })
  const deactivate = useMutation({
    mutationFn: (id: string) => api<UserRecord>(`/users/${id}`, { method: 'DELETE' }),
    onSuccess: () => client.invalidateQueries({ queryKey: ['users'] }),
  })
  const removePermanently = useMutation({
    mutationFn: (id: string) => api<UserRecord>(`/users/${id}/permanent`, { method: 'DELETE' }),
    onSuccess: () => { resetForm(); client.invalidateQueries({ queryKey: ['users'] }) },
  })
  const resetForm = () => { setEditingUser(null); setForm({ username: '', display_name: '', password: '', role: 'VIEWER' }) }
  return <><section className="page-heading"><div><p className="eyebrow">ACCESS CONTROL</p><h1>ผู้ใช้งานและสิทธิ์</h1><p>เฉพาะ Admin เท่านั้นที่สร้าง แก้ไขสิทธิ์ ปิดใช้งาน และลบบัญชีผู้ใช้ได้</p></div></section><section className="workspace-grid"><article className="panel"><div className="panel-header"><h2>ผู้ใช้งาน</h2><span className="count-badge">{users.data?.length ?? 0}</span></div><div className="data-list">{users.data?.map((user) => <div key={user.id}><p><strong>{user.username}</strong><small>{user.display_name}</small></p><i className={user.active ? 'active-state' : ''}>{user.active ? (user.role === 'ADMIN' ? 'Admin' : 'Viewer') : 'ปิดใช้งาน'}</i><button className="text-button" type="button" onClick={() => { setEditingUser(user); setForm({ username: user.username || '', display_name: user.display_name, password: '', role: user.role }) }}>แก้ไข</button>{user.id !== me.data?.id && user.active && <button className="text-button" type="button" onClick={() => window.confirm(`ปิดใช้งาน User ${user.username} ใช่หรือไม่`) && deactivate.mutate(user.id)}>ปิดใช้งาน</button>}{user.id !== me.data?.id && <button className="text-button" type="button" onClick={() => window.confirm(`ลบบัญชี User ${user.username} ถาวรใช่หรือไม่\n\nการลบนี้ย้อนกลับไม่ได้`) && removePermanently.mutate(user.id)}>ลบถาวร</button>}</div>)}</div></article><form className="panel form-panel" onSubmit={(event) => { event.preventDefault(); editingUser ? update.mutate() : create.mutate() }}><h2>{editingUser ? 'แก้ไขผู้ใช้งาน' : 'สร้างผู้ใช้ใหม่'}</h2><label>User ID<input value={form.username} disabled={Boolean(editingUser)} onChange={(event) => setForm({ ...form, username: event.target.value })} required /></label><label>ชื่อที่แสดง<input value={form.display_name} onChange={(event) => setForm({ ...form, display_name: event.target.value })} required /></label><label>รหัสผ่าน {editingUser ? '(เว้นว่างได้ถ้าไม่เปลี่ยน)' : '(อย่างน้อย 4 ตัวอักษร)'}<input type="password" value={form.password} onChange={(event) => setForm({ ...form, password: event.target.value })} minLength={editingUser ? undefined : 4} required={!editingUser} /></label><label>สิทธิ์<select value={form.role} onChange={(event) => setForm({ ...form, role: event.target.value })}><option value="VIEWER">Viewer — ดูข้อมูล</option><option value="ADMIN">Admin — จัดการระบบ</option></select></label>{(create.error || update.error || removePermanently.error) && <div className="login-error">{(create.error || update.error || removePermanently.error)?.message}</div>}<button className="primary" disabled={create.isPending || update.isPending}>{editingUser ? 'บันทึกการแก้ไข' : 'สร้างผู้ใช้'}</button>{editingUser && <button className="secondary" type="button" onClick={resetForm}>ยกเลิก</button>}</form></section></>
}

type Draft = { id: string; draft_type: string; status: string; original_text: string; suggestions: { label: string; score: number }[] }
export function DraftsPage() {
  const query = useQuery({ queryKey: ['drafts'], queryFn: () => api<Draft[]>('/drafts?status=PENDING') })
  return <><section className="page-heading"><div><p className="eyebrow">ADMIN REVIEW</p><h1>ตรวจข้อมูลร่าง</h1><p>ข้อมูลไม่แน่ชัดจะไม่ถูกสร้างเป็น Master Data จนกว่า Admin พิจารณา</p></div></section><article className="panel"><div className="data-list">{query.data?.map((draft) => <div key={draft.id}><span className="code-chip">{draft.draft_type}</span><p><strong>{draft.original_text}</strong><small>{draft.suggestions[0] ? `ใกล้เคียง ${draft.suggestions[0].label} · ${draft.suggestions[0].score}%` : 'ไม่พบข้อมูลใกล้เคียง'}</small></p><i>{draft.status}</i></div>)}{query.data?.length === 0 && <div className="empty-state">ไม่มี Draft รอตรวจสอบ</div>}</div></article></>
}

