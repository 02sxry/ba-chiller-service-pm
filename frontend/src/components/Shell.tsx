import { type ReactNode, useState } from 'react'
import {
  Activity, Bell, Building2, CalendarDays, ChevronLeft, ChevronRight, ClipboardCheck,
  Database, FileClock, FileSpreadsheet, Gauge, HardDrive, History, Hospital,
  Menu, Settings, ShieldCheck, Stethoscope, Users, Wrench, X,
} from 'lucide-react'
import { NavLink } from 'react-router-dom'

const navigation = [
  ['ภาพรวม', '/', Gauge],
  ['โรงพยาบาล', '/hospitals', Hospital],
  ['ฐานข้อมูลอุปกรณ์', '/equipment', Database],
  ['วางแผน PM รายปี', '/planner', CalendarDays],
  ['รอบ PM', '/slots', FileClock],
  ['ตารางจากช่าง', '/intakes', Wrench],
  ['ตรวจข้อมูลร่าง', '/drafts', ClipboardCheck],
  ['คิวอนุมัติ', '/approvals', ShieldCheck],
  ['ปฏิทินนัดหมาย', '/calendar', CalendarDays],
  ['การยืนยันนัด', '/confirmations', Bell],
  ['คำขอเลื่อนนัด', '/reschedules', Activity],
  ['ประวัติการแก้ไข', '/history', History],
  ['แผนปีถัดไป', '/next-year', FileSpreadsheet],
  ['Google Sheets', '/sheets', FileSpreadsheet],
  ['Google Drive', '/drive', HardDrive],
  ['LINE Groups', '/line-groups', Users],
  ['รายงาน', '/reports', Building2],
  ['ตั้งค่า', '/settings', Settings],
] as const

export function Shell({ children }: { children: ReactNode }) {
  const [open, setOpen] = useState(false)
  const [compact, setCompact] = useState(false)
  return (
    <div className={`app-shell ${compact ? 'compact' : ''}`}>
      <aside className={`sidebar ${open ? 'open' : ''}`}>
        <div className="brand">
          <div className="brand-mark"><Stethoscope size={22} /></div>
          <div className="brand-copy"><strong>BA CHILLER</strong><span>SERVICE & PM</span></div>
          <button className="icon-button close-mobile" onClick={() => setOpen(false)} aria-label="ปิดเมนู"><X /></button>
        </div>
        <nav>
          {navigation.map(([label, path, Icon]) => (
            <NavLink key={path} to={path} end={path === '/'} onClick={() => setOpen(false)}>
              <Icon size={18} /><span>{label}</span>
            </NavLink>
          ))}
        </nav>
        <button className="collapse-button" onClick={() => setCompact((value) => !value)}>
          {compact ? <ChevronRight size={18} /> : <ChevronLeft size={18} />}
          <span>ย่อเมนู</span>
        </button>
      </aside>
      {open && <button className="overlay" onClick={() => setOpen(false)} aria-label="ปิดเมนู" />}
      <main>
        <header className="topbar">
          <button className="icon-button menu-mobile" onClick={() => setOpen(true)} aria-label="เปิดเมนู"><Menu /></button>
          <div className="environment"><span className="live-dot" /> ระบบพัฒนา · Mock integrations</div>
          <div className="profile"><span>ผู้ดูแลระบบ</span><div className="avatar">BA</div></div>
        </header>
        <div className="content">{children}</div>
      </main>
    </div>
  )
}

