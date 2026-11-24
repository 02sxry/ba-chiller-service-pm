import hashlib
import re
import uuid
from datetime import UTC, date, datetime
from typing import Annotated
from urllib.parse import parse_qs

from fastapi import APIRouter, Depends, File, Header, HTTPException, Query, Request, UploadFile
from sqlalchemy import func, or_, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.db import get_db
from app.core.security import AdminUser, CurrentUser, create_access_token, hash_password, verify_password
from app.domain.enums import AppointmentStatus, NotificationStatus, Role, SyncStatus
from app.domain.models import (
    AnnualPlan,
    Appointment,
    AppointmentRevision,
    AuditLog,
    Equipment,
    Hospital,
    LineGroupMapping,
    MasterDataDraft,
    NextYearPlanDraft,
    NotificationJob,
    PMSlot,
    ScheduleIntake,
    SyncEvent,
    User,
    WebhookEvent,
)
from app.domain.schemas import (
    AppointmentApproveRequest,
    AppointmentSummary,
    AppointmentView,
    ApproveEquipmentDraftRequest,
    ApproveHospitalDraftRequest,
    ApprovePlanDraftRequest,
    BulkApprovalRequest,
    BulkApprovalResult,
    ConfirmRequest,
    DashboardMetrics,
    DateChangeRequest,
    DraftView,
    EquipmentCreate,
    EquipmentUpdate,
    EquipmentView,
    HealthResponse,
    HospitalCreate,
    HospitalSheetSubmission,
    HospitalUpdate,
    HospitalView,
    IntakeView,
    LineGroupCreate,
    LineGroupView,
    LoginRequest,
    MatchHospitalDraftRequest,
    PlanApproveRequest,
    PlanPreviewRequest,
    PlanPreviewResponse,
    PlanView,
    RescheduleRequestInput,
    RevisionView,
    SlotRecommendation,
    SlotView,
    SyncEventView,
    TextIntakeRequest,
    TokenResponse,
    UserCreateRequest,
    UserUpdateRequest,
    UserView,
)
from app.integrations.gemini import build_intent_provider
from app.integrations.google import build_google_provider
from app.integrations.line import LineQuestionIntent, parse_line_question, verify_signature
from app.services.appointments import (
    AppointmentError,
    approve_appointment,
    confirm_appointment,
    request_reschedule,
    technician_date_change,
)
from app.services.audit import record_audit
from app.services.drafts import (
    DraftError,
    approve_equipment_draft,
    approve_hospital_as_new,
    approve_plan_draft,
    match_hospital_draft,
)
from app.services.google_sync import SyncError, process_hospital_submission, process_outbound_event
from app.services.intake import create_text_intake, parse_excel
from app.services.matching import recommend_slots
from app.services.planning import (
    THAI_MONTHS,
    PlanningError,
    approve_plan,
    bulk_approve_drafts,
    calculate_months,
    generate_next_year_drafts,
)

router = APIRouter()
Db = Annotated[Session, Depends(get_db)]


def _normalize_chiller_serial(data: dict[str, object]) -> None:
    equipment_name = str(data.get("equipment_name") or "")
    model = str(data.get("model") or "")
    serial_number = data.get("serial_number")
    if not isinstance(serial_number, str) or not serial_number.strip():
        return
    serial_number = re.sub(r"-CH$", "", serial_number.strip(), flags=re.IGNORECASE)
    if "chiller" in f"{equipment_name} {model}".casefold():
        serial_number = f"{serial_number}-CH"
    data["serial_number"] = serial_number


@router.get("/health", response_model=HealthResponse, tags=["system"])
def health(db: Db) -> HealthResponse:
    try:
        db.execute(text("SELECT 1"))
        database = "ok"
        status = "ok"
    except Exception:
        database = "unavailable"
        status = "degraded"
    settings = get_settings()
    return HealthResponse(
        status=status,
        database=database,
        integrations={
            "line": "configured" if settings.line_channel_secret and settings.line_channel_access_token else "mock",
            "google": "configured" if settings.google_spreadsheet_id else "mock",
            "gemini": "configured" if settings.gemini_api_key else "disabled",
            "notifications": "enabled" if settings.notifications_enabled and not settings.notification_kill_switch else "disabled",
        },
    )


@router.post("/auth/token", response_model=TokenResponse, tags=["auth"])
def login(request: LoginRequest, db: Db) -> TokenResponse:
    username = request.username.strip().lower()
    user = db.scalar(select(User).where(or_(User.username == username, User.email == username), User.active.is_(True)))
    if not user or not verify_password(request.password, user.password_hash):
        raise HTTPException(status_code=401, detail="User ID หรือรหัสผ่านไม่ถูกต้อง")
    return TokenResponse(access_token=create_access_token(user))


@router.get("/auth/me", response_model=UserView, tags=["auth"])
def me(user: CurrentUser) -> User:
    return user


@router.get("/users", response_model=list[UserView], tags=["users"])
def list_users(db: Db, _: AdminUser) -> list[User]:
    return list(db.scalars(select(User).order_by(User.username)).all())


@router.post("/users", response_model=UserView, status_code=201, tags=["users"])
def create_user(request: UserCreateRequest, db: Db, admin: AdminUser) -> User:
    username = request.username.strip().lower()
    if not username or any(char.isspace() for char in username):
        raise HTTPException(status_code=422, detail="User ID ต้องไม่ว่างและห้ามมีช่องว่าง")
    if db.scalar(select(User).where(User.username == username)):
        raise HTTPException(status_code=409, detail="มี User ID นี้แล้ว")
    user = User(
        username=username,
        # The email column is retained for compatibility, but users sign in with
        # username. Use a valid internal domain so UserView validation succeeds.
        email=f"{username}@local.dev",
        display_name=request.display_name.strip(),
        password_hash=hash_password(request.password),
        role=request.role,
    )
    db.add(user)
    try:
        db.flush()
        record_audit(db, actor=admin, action="USER_CREATED", entity_type="user", entity_id=user.id, new_values={"username": username, "role": request.role.value})
        db.commit()
        db.refresh(user)
        return user
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="มี User ID นี้แล้ว") from exc


@router.patch("/users/{user_id}", response_model=UserView, tags=["users"])
def update_user(user_id: uuid.UUID, request: UserUpdateRequest, db: Db, admin: AdminUser) -> User:
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="ไม่พบผู้ใช้งาน")
    updates = request.model_dump(exclude_unset=True)
    if not updates:
        return user
    if user.id == admin.id and updates.get("role") == Role.VIEWER:
        raise HTTPException(status_code=409, detail="ไม่สามารถลดสิทธิ์ของตัวเองขณะใช้งานอยู่")
    if updates.get("role") == Role.VIEWER and user.role == Role.ADMIN:
        active_admins = db.scalar(select(func.count()).select_from(User).where(User.role == Role.ADMIN, User.active.is_(True))) or 0
        if active_admins <= 1:
            raise HTTPException(status_code=409, detail="ต้องมี Admin ที่ใช้งานได้อย่างน้อย 1 คน")
    old_values = {"display_name": user.display_name, "role": user.role.value, "active": user.active}
    if "display_name" in updates:
        user.display_name = updates["display_name"].strip()
    if "password" in updates and updates["password"]:
        user.password_hash = hash_password(updates["password"])
    if "role" in updates and updates["role"] is not None:
        user.role = updates["role"]
    db.flush()
    new_values = {
        key: value.value if isinstance(value, Role) else value
        for key, value in updates.items()
        if key != "password"
    }
    record_audit(
        db,
        actor=admin,
        action="USER_UPDATED",
        entity_type="user",
        entity_id=user.id,
        old_values=old_values,
        new_values=new_values,
    )
    db.commit()
    db.refresh(user)
    return user


@router.delete("/users/{user_id}", response_model=UserView, tags=["users"])
def deactivate_user(user_id: uuid.UUID, db: Db, admin: AdminUser) -> User:
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="ไม่พบผู้ใช้งาน")
    if user.id == admin.id:
        raise HTTPException(status_code=409, detail="ไม่สามารถปิดใช้งานตัวเองได้")
    if user.role == Role.ADMIN:
        active_admins = db.scalar(select(func.count()).select_from(User).where(User.role == Role.ADMIN, User.active.is_(True))) or 0
        if active_admins <= 1:
            raise HTTPException(status_code=409, detail="ต้องมี Admin ที่ใช้งานได้อย่างน้อย 1 คน")
    user.active = False
    db.flush()
    record_audit(db, actor=admin, action="USER_DEACTIVATED", entity_type="user", entity_id=user.id, new_values={"active": False})
    db.commit()
    db.refresh(user)
    return user


@router.delete("/users/{user_id}/permanent", response_model=UserView, tags=["users"])
def delete_user_permanently(user_id: uuid.UUID, db: Db, admin: AdminUser) -> User:
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="ไม่พบผู้ใช้งาน")
    if user.id == admin.id:
        raise HTTPException(status_code=409, detail="ไม่สามารถลบบัญชีที่กำลังใช้งานอยู่ได้")
    if user.role == Role.ADMIN:
        active_admins = db.scalar(select(func.count()).select_from(User).where(User.role == Role.ADMIN, User.active.is_(True))) or 0
        if user.active and active_admins <= 1:
            raise HTTPException(status_code=409, detail="ต้องมี Admin ที่ใช้งานได้อย่างน้อย 1 คน")

    dependencies = {
        "ประวัติการตรวจข้อมูล": db.scalar(select(func.count()).select_from(MasterDataDraft).where(MasterDataDraft.reviewed_by_id == user.id)) or 0,
        "แผน PM ที่อนุมัติ": db.scalar(select(func.count()).select_from(AnnualPlan).where(AnnualPlan.approved_by_id == user.id)) or 0,
        "ประวัติการนัดหมาย": db.scalar(select(func.count()).select_from(AppointmentRevision).where(AppointmentRevision.approved_by_id == user.id)) or 0,
        "ประวัติการแก้ไขระบบ": db.scalar(select(func.count()).select_from(AuditLog).where(AuditLog.actor_id == user.id)) or 0,
    }
    used_by = [f"{label} {count} รายการ" for label, count in dependencies.items() if count]
    if used_by:
        raise HTTPException(status_code=409, detail=f"ลบถาวรไม่ได้เพราะบัญชีนี้มีประวัติการใช้งาน: {', '.join(used_by)} ให้ใช้ปิดใช้งานแทน")

    response = user
    record_audit(db, actor=admin, action="USER_DELETED", entity_type="user", entity_id=user.id, old_values={"username": user.username, "display_name": user.display_name, "role": user.role.value})
    db.delete(user)
    db.commit()
    return response


@router.get("/hospitals", response_model=list[HospitalView], tags=["master-data"])
def list_hospitals(db: Db, _: CurrentUser, active: bool | None = None) -> list[Hospital]:
    query = select(Hospital).order_by(Hospital.hospital_name)
    if active is not None:
        query = query.where(Hospital.active == active)
    return list(db.scalars(query).all())


@router.post("/hospitals", response_model=HospitalView, status_code=201, tags=["master-data"])
def create_hospital(request: HospitalCreate, db: Db, admin: AdminUser) -> Hospital:
    data = request.model_dump()
    data["hospital_code"] = data["hospital_code"] or f"HOSP-{uuid.uuid4().hex[:10].upper()}"
    hospital = Hospital(**data)
    db.add(hospital)
    try:
        db.flush()
    except IntegrityError as exc:
        raise HTTPException(status_code=409, detail="รหัสโรงพยาบาลซ้ำ") from exc
    record_audit(
        db, actor=admin, action="HOSPITAL_CREATED", entity_type="hospital",
        entity_id=hospital.id, new_values=data,
    )
    db.commit()
    db.refresh(hospital)
    return hospital


@router.patch("/hospitals/{hospital_id}", response_model=HospitalView, tags=["master-data"])
def update_hospital(hospital_id: uuid.UUID, request: HospitalUpdate, db: Db, admin: AdminUser) -> Hospital:
    hospital = db.get(Hospital, hospital_id)
    if not hospital:
        raise HTTPException(status_code=404, detail="ไม่พบโรงพยาบาล")
    old_values = {"hospital_name": hospital.hospital_name, "short_name": hospital.short_name, "notes": hospital.notes}
    for field, value in request.model_dump(exclude_unset=True).items():
        setattr(hospital, field, value.strip() if isinstance(value, str) and value else value)
    try:
        db.flush()
        record_audit(db, actor=admin, action="HOSPITAL_UPDATED", entity_type="hospital", entity_id=hospital.id, old_values=old_values, new_values=request.model_dump(exclude_unset=True))
        db.commit()
        db.refresh(hospital)
        return hospital
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="แก้ไขโรงพยาบาลไม่สำเร็จ") from exc


@router.delete("/hospitals/{hospital_id}", response_model=HospitalView, tags=["master-data"])
def deactivate_hospital(hospital_id: uuid.UUID, db: Db, admin: AdminUser) -> Hospital:
    hospital = db.get(Hospital, hospital_id)
    if not hospital:
        raise HTTPException(status_code=404, detail="ไม่พบโรงพยาบาล")
    hospital.active = False
    db.flush()
    record_audit(db, actor=admin, action="HOSPITAL_DEACTIVATED", entity_type="hospital", entity_id=hospital.id, new_values={"active": False})
    db.commit()
    db.refresh(hospital)
    return hospital


@router.get("/drafts", response_model=list[DraftView], tags=["drafts"])
def list_drafts(db: Db, _: AdminUser, status: str | None = None) -> list[MasterDataDraft]:
    query = select(MasterDataDraft).order_by(MasterDataDraft.created_at.desc())
    if status:
        query = query.where(MasterDataDraft.status == status)
    return list(db.scalars(query).all())


@router.post("/drafts/{draft_id}/approve-hospital", response_model=HospitalView, tags=["drafts"])
def approve_hospital_draft(
    draft_id: uuid.UUID,
    request: ApproveHospitalDraftRequest,
    db: Db,
    admin: AdminUser,
) -> Hospital:
    try:
        hospital = approve_hospital_as_new(
            db, draft_id, request.hospital_code, request.hospital_name, admin
        )
        db.commit()
        db.refresh(hospital)
        return hospital
    except (DraftError, IntegrityError) as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/drafts/{draft_id}/match-hospital", response_model=HospitalView, tags=["drafts"])
def match_hospital_draft_endpoint(
    draft_id: uuid.UUID,
    request: MatchHospitalDraftRequest,
    db: Db,
    admin: AdminUser,
) -> Hospital:
    try:
        hospital = match_hospital_draft(
            db, draft_id, request.hospital_id, admin, add_alias=request.add_alias
        )
        db.commit()
        db.refresh(hospital)
        return hospital
    except (DraftError, IntegrityError) as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/drafts/{draft_id}/approve-equipment", response_model=EquipmentView, tags=["drafts"])
def approve_equipment_draft_endpoint(
    draft_id: uuid.UUID,
    request: ApproveEquipmentDraftRequest,
    db: Db,
    admin: AdminUser,
) -> Equipment:
    try:
        equipment = approve_equipment_draft(
            db,
            draft_id,
            admin=admin,
            **request.model_dump(),
        )
        db.commit()
        db.refresh(equipment)
        return equipment
    except (DraftError, IntegrityError, ValueError) as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/drafts/{draft_id}/approve-plan", response_model=PlanView, tags=["drafts"])
def approve_plan_draft_endpoint(
    draft_id: uuid.UUID,
    request: ApprovePlanDraftRequest,
    db: Db,
    admin: AdminUser,
) -> AnnualPlan:
    try:
        plan = approve_plan_draft(
            db,
            draft_id,
            admin=admin,
            **request.model_dump(),
        )
        db.commit()
        db.refresh(plan)
        return plan
    except (DraftError, PlanningError, IntegrityError, ValueError) as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/equipment", response_model=list[EquipmentView], tags=["master-data"])
def list_equipment(db: Db, _: CurrentUser, hospital_id: uuid.UUID | None = None) -> list[Equipment]:
    query = select(Equipment).where(Equipment.active.is_(True)).order_by(Equipment.equipment_code)
    if hospital_id:
        query = query.where(Equipment.hospital_id == hospital_id)
    return list(db.scalars(query).all())


@router.get("/equipment/archive", response_model=list[EquipmentView], tags=["master-data"])
def list_equipment_archive(db: Db, _: AdminUser) -> list[Equipment]:
    query = select(Equipment).where(Equipment.active.is_(False)).order_by(Equipment.updated_at.desc())
    return list(db.scalars(query).all())


@router.post("/equipment", response_model=EquipmentView, status_code=201, tags=["master-data"])
def create_equipment(request: EquipmentCreate, db: Db, admin: AdminUser) -> Equipment:
    if not db.get(Hospital, request.hospital_id):
        raise HTTPException(status_code=404, detail="ไม่พบโรงพยาบาล")
    data = request.model_dump()
    _normalize_chiller_serial(data)
    data["equipment_code"] = data["equipment_code"] or f"EQUIP-{uuid.uuid4().hex[:10].upper()}"
    equipment = Equipment(**data)
    db.add(equipment)
    try:
        db.flush()
    except IntegrityError as exc:
        raise HTTPException(status_code=409, detail="รหัสหรือข้อมูลระบุอุปกรณ์ซ้ำ") from exc
    record_audit(
        db, actor=admin, action="EQUIPMENT_CREATED", entity_type="equipment",
        entity_id=equipment.id, new_values=data,
    )
    db.commit()
    db.refresh(equipment)
    return equipment


@router.patch("/equipment/{equipment_id}", response_model=EquipmentView, tags=["master-data"])
def update_equipment(equipment_id: uuid.UUID, request: EquipmentUpdate, db: Db, admin: AdminUser) -> Equipment:
    equipment = db.get(Equipment, equipment_id)
    if not equipment:
        raise HTTPException(status_code=404, detail="ไม่พบอุปกรณ์")
    updates = request.model_dump(exclude_unset=True)
    if updates.get("hospital_id") and not db.get(Hospital, updates["hospital_id"]):
        raise HTTPException(status_code=404, detail="ไม่พบโรงพยาบาลใหม่")
    equipment_data = {
        "equipment_name": updates.get("equipment_name", equipment.equipment_name),
        "model": updates.get("model", equipment.model),
        "serial_number": updates.get("serial_number", equipment.serial_number),
    }
    _normalize_chiller_serial(equipment_data)
    if equipment_data["serial_number"] != equipment.serial_number:
        updates["serial_number"] = equipment_data["serial_number"]
    old_values = {field: getattr(equipment, field) for field in updates}
    for field, value in updates.items():
        setattr(equipment, field, value.strip() if isinstance(value, str) and value else value)
    try:
        db.flush()
        record_audit(db, actor=admin, action="EQUIPMENT_UPDATED", entity_type="equipment", entity_id=equipment.id, old_values=old_values, new_values=updates)
        db.commit()
        db.refresh(equipment)
        return equipment
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="แก้ไขอุปกรณ์ไม่สำเร็จ อาจมี Serial number ซ้ำ") from exc


@router.delete("/equipment/{equipment_id}", response_model=EquipmentView, tags=["master-data"])
def deactivate_equipment(equipment_id: uuid.UUID, db: Db, admin: AdminUser) -> Equipment:
    equipment = db.get(Equipment, equipment_id)
    if not equipment:
        raise HTTPException(status_code=404, detail="ไม่พบอุปกรณ์")
    equipment.active = False

    active_plans = db.scalars(
        select(AnnualPlan).where(AnnualPlan.equipment_id == equipment.id, AnnualPlan.active.is_(True))
    ).all()
    for plan in active_plans:
        plan.active = False

    active_slots = db.scalars(
        select(PMSlot).where(PMSlot.equipment_id == equipment.id, PMSlot.active.is_(True))
    ).all()
    for slot in active_slots:
        slot.active = False

    open_drafts = db.scalars(
        select(NextYearPlanDraft).where(
            NextYearPlanDraft.equipment_id == equipment.id,
            NextYearPlanDraft.excluded.is_(False),
        )
    ).all()
    for draft in open_drafts:
        draft.excluded = True

    appointments = db.scalars(
        select(Appointment).where(
            Appointment.equipment_id == equipment.id,
            Appointment.status != AppointmentStatus.CANCELLED,
        )
    ).all()
    for appointment in appointments:
        appointment.status = AppointmentStatus.CANCELLED

    db.flush()
    record_audit(
        db,
        actor=admin,
        action="EQUIPMENT_DEACTIVATED",
        entity_type="equipment",
        entity_id=equipment.id,
        new_values={
            "active": False,
            "annual_plans_cancelled": len(active_plans),
            "pm_slots_cancelled": len(active_slots),
            "next_year_drafts_excluded": len(open_drafts),
            "appointments_cancelled": len(appointments),
        },
    )
    db.commit()
    db.refresh(equipment)
    return equipment


@router.delete("/equipment/{equipment_id}/permanent", response_model=EquipmentView, tags=["master-data"])
def delete_equipment_permanently(equipment_id: uuid.UUID, db: Db, admin: AdminUser) -> Equipment:
    equipment = db.get(Equipment, equipment_id)
    if not equipment:
        raise HTTPException(status_code=404, detail="ไม่พบอุปกรณ์")
    if equipment.active:
        raise HTTPException(status_code=409, detail="ต้องเก็บอุปกรณ์เข้า Archive ก่อนจึงจะลบถาวรได้")

    appointment_count = db.scalar(
        select(func.count()).select_from(Appointment).where(Appointment.equipment_id == equipment.id)
    ) or 0
    if appointment_count:
        raise HTTPException(
            status_code=409,
            detail=f"ลบถาวรไม่ได้เพราะมีนัดหมาย {appointment_count} รายการอ้างถึงอุปกรณ์นี้ ให้เก็บ Archive ไว้แทนเพื่อรักษาประวัตินัด",
        )

    plans = db.scalars(select(AnnualPlan).where(AnnualPlan.equipment_id == equipment.id)).all()
    drafts = db.scalars(select(NextYearPlanDraft).where(NextYearPlanDraft.equipment_id == equipment.id)).all()
    for draft in drafts:
        db.delete(draft)
    for plan in plans:
        db.delete(plan)
    db.flush()

    response = equipment
    record_audit(
        db,
        actor=admin,
        action="EQUIPMENT_DELETED",
        entity_type="equipment",
        entity_id=equipment.id,
        old_values={"equipment_code": equipment.equipment_code, "equipment_name": equipment.equipment_name},
        new_values={"plans_deleted": len(plans), "next_year_drafts_deleted": len(drafts)},
    )
    db.delete(equipment)
    db.commit()
    return response


@router.get("/line-groups", response_model=list[LineGroupView], tags=["line"])
def list_line_groups(db: Db, _: AdminUser) -> list[LineGroupMapping]:
    return list(db.scalars(
        select(LineGroupMapping).order_by(LineGroupMapping.group_type, LineGroupMapping.created_at)
    ).all())


@router.post("/line-groups", response_model=LineGroupView, status_code=201, tags=["line"])
def create_line_group(request: LineGroupCreate, db: Db, admin: AdminUser) -> LineGroupMapping:
    group_type = request.group_type.upper()
    if group_type not in {"ADMIN", "TECHNICIAN", "HOSPITAL"}:
        raise HTTPException(status_code=422, detail="group_type ต้องเป็น ADMIN, TECHNICIAN หรือ HOSPITAL")
    if group_type == "HOSPITAL":
        if not request.hospital_id or not db.get(Hospital, request.hospital_id):
            raise HTTPException(status_code=422, detail="Hospital group ต้องผูกกับโรงพยาบาล")
    elif request.hospital_id:
        raise HTTPException(status_code=422, detail="Internal group ต้องไม่มี hospital_id")
    mapping = LineGroupMapping(
        line_group_id=request.line_group_id,
        group_type=group_type,
        hospital_id=request.hospital_id,
    )
    db.add(mapping)
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="LINE group นี้ลงทะเบียนแล้ว") from exc
    record_audit(
        db,
        actor=admin,
        action="LINE_GROUP_AUTHORIZED",
        entity_type="line_group_mapping",
        entity_id=mapping.id,
        new_values={
            "line_group_id": mapping.line_group_id,
            "group_type": mapping.group_type,
            "hospital_id": str(mapping.hospital_id) if mapping.hospital_id else None,
        },
    )
    db.commit()
    db.refresh(mapping)
    return mapping


@router.post("/plans/preview", response_model=PlanPreviewResponse, tags=["planning"])
def preview_plan(request: PlanPreviewRequest, _: CurrentUser) -> PlanPreviewResponse:
    try:
        months = calculate_months(request)
    except PlanningError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return PlanPreviewResponse(
        plan_year=request.plan_year,
        annual_frequency=request.annual_frequency,
        planned_months=months,
        display_months_th=[THAI_MONTHS[month - 1] for month in months],
    )


@router.post("/plans/approve", response_model=PlanView, status_code=201, tags=["planning"])
def approve_plan_endpoint(request: PlanApproveRequest, db: Db, admin: AdminUser) -> AnnualPlan:
    try:
        plan = approve_plan(db, request, admin)
        db.commit()
        db.refresh(plan)
        return plan
    except PlanningError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/slots", response_model=list[SlotView], tags=["planning"])
def list_slots(db: Db, _: CurrentUser, plan_year: int | None = None) -> list[PMSlot]:
    query = select(PMSlot).where(PMSlot.active.is_(True)).order_by(PMSlot.plan_year, PMSlot.planned_month)
    if plan_year:
        query = query.where(PMSlot.plan_year == plan_year)
    return list(db.scalars(query).all())


@router.post("/next-year-drafts/generate", tags=["planning"])
def generate_drafts(
    db: Db, admin: AdminUser, source_year: int = Query(ge=2000, le=2200), target_year: int = Query(ge=2000, le=2200)
) -> dict:
    try:
        drafts = generate_next_year_drafts(db, source_year, target_year)
        db.commit()
        return {"generated_or_existing": len(drafts), "draft_ids": [str(draft.id) for draft in drafts]}
    except PlanningError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/next-year-drafts/bulk-approve", response_model=list[BulkApprovalResult], tags=["planning"])
def approve_drafts(request: BulkApprovalRequest, db: Db, admin: AdminUser) -> list[BulkApprovalResult]:
    results = bulk_approve_drafts(db, request.draft_ids, admin)
    db.commit()
    return [BulkApprovalResult(**result.__dict__) for result in results]


@router.post("/intakes/text", status_code=201, tags=["intake"])
def text_intake(request: TextIntakeRequest, db: Db, _: AdminUser) -> dict:
    intake = create_text_intake(db, request.source_event_id, request.text, request.received_at)
    if intake.state.value == "NEEDS_REVIEW" and "ai_suggestion" not in intake.parsed_data:
        suggestion = build_intent_provider(get_settings()).extract(request.text)
        if suggestion["available"]:
            intake.parsed_data = {**intake.parsed_data, "ai_suggestion": suggestion}
            intake.validation_errors = [*intake.validation_errors, "มีคำแนะนำจาก AI ต้องให้ Admin ตรวจสอบก่อนใช้งาน"]
    db.commit()
    return {"id": intake.id, "state": intake.state, "parsed_data": intake.parsed_data, "errors": intake.validation_errors}


@router.get("/intakes", response_model=list[IntakeView], tags=["intake"])
def list_intakes(
    db: Db,
    _: AdminUser,
    state: str | None = None,
    limit: int = Query(default=100, ge=1, le=500),
) -> list[ScheduleIntake]:
    query = select(ScheduleIntake).order_by(ScheduleIntake.created_at.desc()).limit(limit)
    if state:
        query = query.where(ScheduleIntake.state == state)
    return list(db.scalars(query).all())


@router.post("/intakes/excel", tags=["intake"])
async def excel_intake(db: Db, _: AdminUser, file: Annotated[UploadFile, File()]) -> dict:
    settings = get_settings()
    if not file.filename or not file.filename.lower().endswith(".xlsx"):
        raise HTTPException(status_code=415, detail="รองรับเฉพาะไฟล์ .xlsx")
    content = await file.read(settings.upload_max_bytes + 1)
    if len(content) > settings.upload_max_bytes:
        raise HTTPException(status_code=413, detail="ไฟล์มีขนาดเกินกำหนด")
    checksum = hashlib.sha256(content).hexdigest()
    existing = db.scalar(select(ScheduleIntake).where(ScheduleIntake.source_checksum == checksum))
    if existing:
        return {"duplicate": True, "intake_id": existing.id}
    try:
        rows = parse_excel(content)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"duplicate": False, "checksum": checksum, "rows": [row.model_dump(mode="json") for row in rows]}


@router.get("/slots/recommend", response_model=list[SlotRecommendation], tags=["matching"])
def slot_recommendations(
    db: Db, _: AdminUser, equipment_id: uuid.UUID, proposed_date: datetime
) -> list[dict]:
    return recommend_slots(db, equipment_id, proposed_date.date())


@router.post("/appointments/approve", response_model=AppointmentView, status_code=201, tags=["appointments"])
def appointment_approve(request: AppointmentApproveRequest, db: Db, admin: AdminUser) -> Appointment:
    try:
        appointment, _ = approve_appointment(db, request, admin)
        db.commit()
        db.refresh(appointment)
        return appointment
    except AppointmentError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/appointments/confirm", response_model=AppointmentView, tags=["appointments"])
def appointment_confirm(request: ConfirmRequest, db: Db) -> Appointment:
    try:
        appointment = confirm_appointment(db, request.token, request.line_group_id)
        db.commit()
        db.refresh(appointment)
        return appointment
    except AppointmentError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/appointments/reschedule", response_model=AppointmentView, tags=["appointments"])
def appointment_reschedule(request: RescheduleRequestInput, db: Db) -> Appointment:
    try:
        appointment = request_reschedule(
            db, request.token, request.line_group_id, request.preferred_date, request.message
        )
        db.commit()
        db.refresh(appointment)
        return appointment
    except AppointmentError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/appointments/{appointment_id}/technician-date-change", response_model=RevisionView, tags=["appointments"])
def change_technician_date(
    appointment_id: uuid.UUID, request: DateChangeRequest, db: Db, admin: AdminUser
) -> AppointmentRevision:
    try:
        revision = technician_date_change(db, appointment_id, request, admin)
        db.commit()
        db.refresh(revision)
        return revision
    except AppointmentError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/appointments/{appointment_id}/history", response_model=list[RevisionView], tags=["appointments"])
def appointment_history(appointment_id: uuid.UUID, db: Db, _: CurrentUser) -> list[AppointmentRevision]:
    return list(db.scalars(
        select(AppointmentRevision).where(AppointmentRevision.appointment_id == appointment_id)
        .order_by(AppointmentRevision.revision_number)
    ).all())


@router.get("/appointments", response_model=list[AppointmentSummary], tags=["appointments"])
def list_appointments(
    db: Db,
    _: CurrentUser,
    plan_year: int | None = None,
    status: AppointmentStatus | None = None,
) -> list[AppointmentSummary]:
    confirmed_revision = AppointmentRevision.__table__.alias("confirmed_revision")
    query = (
        select(
            Appointment,
            AppointmentRevision,
            Hospital.hospital_name,
            Equipment.equipment_name,
            PMSlot.plan_year,
            PMSlot.planned_month,
            confirmed_revision.c.scheduled_date.label("confirmed_date"),
        )
        .join(PMSlot, PMSlot.id == Appointment.pm_slot_id)
        .join(Hospital, Hospital.id == Appointment.hospital_id)
        .join(Equipment, Equipment.id == Appointment.equipment_id)
        .join(AppointmentRevision, AppointmentRevision.id == Appointment.current_revision_id)
        .outerjoin(confirmed_revision, confirmed_revision.c.id == Appointment.confirmed_revision_id)
        .order_by(AppointmentRevision.scheduled_date, Hospital.hospital_name)
    )
    if plan_year is not None:
        query = query.where(PMSlot.plan_year == plan_year)
    if status is not None:
        query = query.where(Appointment.status == status)
    rows = db.execute(query).all()
    appointment_ids = [row[0].id for row in rows]
    warning_ids = set(db.scalars(
        select(NotificationJob.appointment_id).where(
            NotificationJob.appointment_id.in_(appointment_ids),
            NotificationJob.status.in_([
                NotificationStatus.FAILED,
                NotificationStatus.REVIEW_REQUIRED,
            ]),
        )
    ).all()) if appointment_ids else set()
    return [
        AppointmentSummary(
            id=appointment.id,
            reference=f"BA-{str(appointment.id)[:8].upper()}",
            hospital_id=appointment.hospital_id,
            equipment_id=appointment.equipment_id,
            hospital_name=hospital_name,
            equipment_name=equipment_name,
            plan_year=row_plan_year,
            planned_month=planned_month,
            scheduled_date=revision.scheduled_date,
            status=appointment.status,
            revision_number=revision.revision_number,
            confirmed_date=confirmed_date,
            admin_changed_after_confirmation=bool(
                appointment.confirmed_revision_id
                and appointment.current_revision_id != appointment.confirmed_revision_id
            ),
            notification_warning=appointment.id in warning_ids,
        )
        for (
            appointment,
            revision,
            hospital_name,
            equipment_name,
            row_plan_year,
            planned_month,
            confirmed_date,
        ) in rows
    ]


@router.post("/google-sync/hospitals", response_model=SyncEventView, tags=["google-sync"])
def import_hospital_sheet_row(
    request: HospitalSheetSubmission,
    db: Db,
    admin: AdminUser,
) -> SyncEvent:
    try:
        event = process_hospital_submission(db, request.model_dump(mode="json"), admin)
        db.commit()
        db.refresh(event)
        return event
    except (SyncError, IntegrityError) as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/google-sync/events", response_model=list[SyncEventView], tags=["google-sync"])
def list_sync_events(
    db: Db,
    _: AdminUser,
    status: SyncStatus | None = None,
    limit: int = Query(default=100, ge=1, le=500),
) -> list[SyncEvent]:
    query = select(SyncEvent).order_by(SyncEvent.created_at.desc()).limit(limit)
    if status is not None:
        query = query.where(SyncEvent.status == status)
    return list(db.scalars(query).all())


@router.post("/google-sync/events/{event_id}/run", response_model=SyncEventView, tags=["google-sync"])
def run_google_sync_event(event_id: uuid.UUID, db: Db, _: AdminUser) -> SyncEvent:
    event = db.scalar(select(SyncEvent).where(SyncEvent.id == event_id).with_for_update())
    if not event:
        raise HTTPException(status_code=404, detail="ไม่พบ sync event")
    try:
        process_outbound_event(db, event, build_google_provider(get_settings()))
        db.commit()
        db.refresh(event)
        return event
    except SyncError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/google-sync/events/{event_id}/retry", response_model=SyncEventView, tags=["google-sync"])
def retry_google_sync_event(event_id: uuid.UUID, db: Db, admin: AdminUser) -> SyncEvent:
    event = db.scalar(select(SyncEvent).where(SyncEvent.id == event_id).with_for_update())
    if not event:
        raise HTTPException(status_code=404, detail="ไม่พบ sync event")
    if event.direction != "OUTBOUND" or event.status not in {SyncStatus.FAILED, SyncStatus.CONFLICT}:
        raise HTTPException(status_code=409, detail="retry ได้เฉพาะ outbound event ที่ล้มเหลวหรือ conflict")
    old_status = event.status
    event.status = SyncStatus.PENDING
    event.last_error = None
    record_audit(
        db,
        actor=admin,
        action="GOOGLE_SYNC_RETRY",
        entity_type=event.entity_type,
        entity_id=event.entity_id,
        old_values={"status": old_status.value, "attempts": event.attempts},
        new_values={"status": event.status.value, "attempts": event.attempts},
        reason="Admin สั่ง retry จาก Google operations",
        source="WEB",
    )
    db.commit()
    db.refresh(event)
    return event


@router.post("/line/webhook", tags=["line"])
async def line_webhook(
    request: Request,
    db: Db,
    x_line_signature: Annotated[str | None, Header()] = None,
) -> dict:
    settings = get_settings()
    raw_body = await request.body()
    if not settings.line_channel_secret or not x_line_signature:
        raise HTTPException(status_code=503, detail="ยังไม่ได้กำหนด LINE webhook credentials")
    if not verify_signature(raw_body, x_line_signature, settings.line_channel_secret):
        raise HTTPException(status_code=401, detail="ลายเซ็น LINE ไม่ถูกต้อง")
    payload = await request.json()
    accepted = 0
    action_results: list[dict[str, str]] = []
    for event in payload.get("events", []):
        event_id = event.get("webhookEventId")
        if not event_id:
            continue
        if db.scalar(select(WebhookEvent).where(WebhookEvent.provider_event_id == event_id)):
            continue
        db.add(WebhookEvent(
            provider_event_id=event_id,
            payload_hash=hashlib.sha256(str(event).encode()).hexdigest(),
            processed_at=datetime.now(UTC),
        ))
        if event.get("type") == "postback":
            group_id = event.get("source", {}).get("groupId")
            parameters = parse_qs(event.get("postback", {}).get("data", ""))
            action = parameters.get("action", [None])[0]
            token = parameters.get("token", [None])[0]
            if not group_id or not action or not token:
                action_results.append({"event_id": event_id, "result": "INVALID_POSTBACK"})
            else:
                try:
                    if action == "confirm":
                        confirm_appointment(db, token, group_id)
                        action_results.append({"event_id": event_id, "result": "CONFIRMED"})
                    elif action == "reschedule":
                        preferred_date_text = event.get("postback", {}).get("params", {}).get("date")
                        request_reschedule(
                            db,
                            token,
                            group_id,
                            date.fromisoformat(preferred_date_text) if preferred_date_text else None,
                            "ขอเลื่อนนัดผ่าน LINE postback",
                        )
                        action_results.append({"event_id": event_id, "result": "RESCHEDULE_REQUESTED"})
                    else:
                        action_results.append({"event_id": event_id, "result": "UNKNOWN_ACTION"})
                except (AppointmentError, ValueError) as exc:
                    action_results.append({"event_id": event_id, "result": f"REJECTED: {exc}"})
        elif event.get("type") == "message" and event.get("message", {}).get("type") == "text":
            group_id = event.get("source", {}).get("groupId")
            mapping = db.scalar(select(LineGroupMapping).where(
                LineGroupMapping.line_group_id == group_id,
                LineGroupMapping.group_type == "HOSPITAL",
                LineGroupMapping.active.is_(True),
            )) if group_id else None
            intent = parse_line_question(event["message"].get("text", ""))
            if not mapping or not mapping.hospital_id:
                action_results.append({"event_id": event_id, "result": "UNAUTHORIZED_GROUP"})
            elif intent == LineQuestionIntent.HELP:
                db.add(NotificationJob(
                    idempotency_key=f"LINE_QA:{event_id}", kind="LINE_TEXT_REPLY", destination_id=group_id,
                    payload={"text": "เมนูช่วยเหลือ: พิมพ์ ‘ขอนัดหมาย’ เพื่อดูนัดหมายของโรงพยาบาล หรือกดปุ่มในข้อความแจ้งนัดเพื่อยืนยัน/ขอเลื่อนนัด"},
                    status=NotificationStatus.PENDING,
                ))
                action_results.append({"event_id": event_id, "result": "HELP_QUEUED"})
            elif intent == LineQuestionIntent.APPOINTMENTS:
                rows = db.execute(
                    select(AppointmentRevision.scheduled_date, Appointment.status)
                    .join(Appointment, Appointment.id == AppointmentRevision.appointment_id)
                    .where(
                        Appointment.hospital_id == mapping.hospital_id,
                        Appointment.current_revision_id == AppointmentRevision.id,
                        Appointment.status != AppointmentStatus.CANCELLED,
                    )
                    .order_by(AppointmentRevision.scheduled_date)
                    .limit(3)
                ).all()
                if rows:
                    dates = ", ".join(f"{scheduled_date.isoformat()} ({status.value})" for scheduled_date, status in rows)
                    reply = f"นัดหมายที่มีในระบบ: {dates} ระบบแสดงแผนนัดหมายล่วงหน้า ไม่ได้หมายความว่างานบริการเสร็จแล้ว"
                else:
                    reply = "ยังไม่พบนัดหมายของโรงพยาบาลในระบบ กรุณาติดต่อผู้ประสานงานเพื่อให้ Admin ตรวจสอบ"
                db.add(NotificationJob(
                    idempotency_key=f"LINE_QA:{event_id}", kind="LINE_TEXT_REPLY", destination_id=group_id,
                    payload={"text": reply}, status=NotificationStatus.PENDING,
                ))
                action_results.append({"event_id": event_id, "result": "APPOINTMENTS_QUEUED"})
            else:
                action_results.append({"event_id": event_id, "result": "UNKNOWN_QUESTION"})
        accepted += 1
    db.commit()
    return {"accepted_events": accepted, "actions": action_results}


@router.get("/dashboard", response_model=DashboardMetrics, tags=["reports"])
def dashboard(db: Db, _: CurrentUser, year: int = Query(default_factory=lambda: datetime.now().year)) -> DashboardMetrics:
    today = datetime.now(UTC).date()
    total_pm_slots = db.scalar(select(func.count()).select_from(PMSlot).where(PMSlot.plan_year == year, PMSlot.active.is_(True))) or 0
    appointments = list(db.scalars(
        select(Appointment).join(PMSlot).where(PMSlot.plan_year == year)
    ).all())
    appointment_ids = [item.id for item in appointments]
    revisions = list(db.scalars(
        select(AppointmentRevision).where(AppointmentRevision.appointment_id.in_(appointment_ids))
    ).all()) if appointment_ids else []
    revisions_by_id = {revision.id: revision for revision in revisions}
    current_revisions = [revisions_by_id.get(item.current_revision_id) for item in appointments]
    confirmed = [item for item in appointments if item.confirmed_revision_id is not None and item.status != AppointmentStatus.CANCELLED]
    return DashboardMetrics(
        total_pm_slots=total_pm_slots,
        confirmed_appointments=len(confirmed),
        pending_confirmation=sum(item.status == AppointmentStatus.PENDING_CONFIRMATION for item in appointments),
        pending_approval=db.scalar(select(func.count()).select_from(ScheduleIntake).where(ScheduleIntake.state == "READY_FOR_APPROVAL")) or 0,
        reschedule_requests=sum(item.status == AppointmentStatus.RESCHEDULE_REQUESTED for item in appointments),
        unscheduled_slots=max(total_pm_slots - len([item for item in appointments if item.status != AppointmentStatus.CANCELLED]), 0),
        upcoming_appointments=sum(bool(revision and revision.scheduled_date >= today) for revision in current_revisions),
        past_due_unconfirmed=sum(bool(revision and revision.scheduled_date < today and not item.confirmed_revision_id) for item, revision in zip(appointments, current_revisions, strict=True)),
        unscheduled_backlog=db.scalar(
            select(func.count())
            .select_from(PMSlot)
            .outerjoin(Appointment)
            .where(
                PMSlot.plan_year == year,
                PMSlot.active.is_(True),
                PMSlot.planned_month < today.month,
                Appointment.id.is_(None),
            )
        ) or 0,
        cancelled_appointments=sum(item.status == AppointmentStatus.CANCELLED for item in appointments),
        admin_changed_appointments=sum(bool(item.confirmed_revision_id and item.current_revision_id != item.confirmed_revision_id) for item in appointments),
        failed_notifications=db.scalar(select(func.count()).select_from(NotificationJob).where(NotificationJob.status.in_([NotificationStatus.FAILED, NotificationStatus.REVIEW_REQUIRED]))) or 0,
        sync_errors=db.scalar(select(func.count()).select_from(SyncEvent).where(SyncEvent.status.in_([SyncStatus.FAILED, SyncStatus.CONFLICT]))) or 0,
    )

