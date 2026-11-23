import hashlib
import uuid
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, File, Header, HTTPException, Query, Request, UploadFile
from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.db import get_db
from app.core.security import AdminUser, CurrentUser, create_access_token, verify_password
from app.domain.enums import AppointmentStatus, NotificationStatus, SyncStatus
from app.domain.models import (
    AnnualPlan,
    Appointment,
    AppointmentRevision,
    Equipment,
    Hospital,
    MasterDataDraft,
    NotificationJob,
    PMSlot,
    ScheduleIntake,
    SyncEvent,
    User,
    WebhookEvent,
)
from app.domain.schemas import (
    AppointmentApproveRequest,
    AppointmentView,
    ApproveHospitalDraftRequest,
    BulkApprovalRequest,
    BulkApprovalResult,
    ConfirmRequest,
    DashboardMetrics,
    DateChangeRequest,
    DraftView,
    EquipmentCreate,
    EquipmentView,
    HealthResponse,
    HospitalCreate,
    HospitalView,
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
    TextIntakeRequest,
    TokenResponse,
    UserView,
)
from app.integrations.line import verify_signature
from app.services.appointments import (
    AppointmentError,
    approve_appointment,
    confirm_appointment,
    request_reschedule,
    technician_date_change,
)
from app.services.audit import record_audit
from app.services.drafts import DraftError, approve_hospital_as_new, match_hospital_draft
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
    user = db.scalar(select(User).where(User.email == request.email, User.active.is_(True)))
    if not user or not verify_password(request.password, user.password_hash):
        raise HTTPException(status_code=401, detail="อีเมลหรือรหัสผ่านไม่ถูกต้อง")
    return TokenResponse(access_token=create_access_token(user))


@router.get("/auth/me", response_model=UserView, tags=["auth"])
def me(user: CurrentUser) -> User:
    return user


@router.get("/hospitals", response_model=list[HospitalView], tags=["master-data"])
def list_hospitals(db: Db, _: CurrentUser, active: bool | None = None) -> list[Hospital]:
    query = select(Hospital).order_by(Hospital.hospital_name)
    if active is not None:
        query = query.where(Hospital.active == active)
    return list(db.scalars(query).all())


@router.post("/hospitals", response_model=HospitalView, status_code=201, tags=["master-data"])
def create_hospital(request: HospitalCreate, db: Db, admin: AdminUser) -> Hospital:
    hospital = Hospital(**request.model_dump())
    db.add(hospital)
    try:
        db.flush()
    except IntegrityError as exc:
        raise HTTPException(status_code=409, detail="รหัสโรงพยาบาลซ้ำ") from exc
    record_audit(
        db, actor=admin, action="HOSPITAL_CREATED", entity_type="hospital",
        entity_id=hospital.id, new_values=request.model_dump(mode="json"),
    )
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


@router.get("/equipment", response_model=list[EquipmentView], tags=["master-data"])
def list_equipment(db: Db, _: CurrentUser, hospital_id: uuid.UUID | None = None) -> list[Equipment]:
    query = select(Equipment).order_by(Equipment.equipment_code)
    if hospital_id:
        query = query.where(Equipment.hospital_id == hospital_id)
    return list(db.scalars(query).all())


@router.post("/equipment", response_model=EquipmentView, status_code=201, tags=["master-data"])
def create_equipment(request: EquipmentCreate, db: Db, admin: AdminUser) -> Equipment:
    if not db.get(Hospital, request.hospital_id):
        raise HTTPException(status_code=404, detail="ไม่พบโรงพยาบาล")
    equipment = Equipment(**request.model_dump())
    db.add(equipment)
    try:
        db.flush()
    except IntegrityError as exc:
        raise HTTPException(status_code=409, detail="รหัสหรือข้อมูลระบุอุปกรณ์ซ้ำ") from exc
    record_audit(
        db, actor=admin, action="EQUIPMENT_CREATED", entity_type="equipment",
        entity_id=equipment.id, new_values=request.model_dump(mode="json"),
    )
    db.commit()
    db.refresh(equipment)
    return equipment


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
    query = select(PMSlot).order_by(PMSlot.plan_year, PMSlot.planned_month)
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
    db.commit()
    return {"id": intake.id, "state": intake.state, "parsed_data": intake.parsed_data, "errors": intake.validation_errors}


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
        accepted += 1
    db.commit()
    return {"accepted_events": accepted}


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
        unscheduled_backlog=db.scalar(select(func.count()).select_from(PMSlot).outerjoin(Appointment).where(PMSlot.plan_year == year, PMSlot.planned_month < today.month, Appointment.id.is_(None))) or 0,
        cancelled_appointments=sum(item.status == AppointmentStatus.CANCELLED for item in appointments),
        admin_changed_appointments=sum(bool(item.confirmed_revision_id and item.current_revision_id != item.confirmed_revision_id) for item in appointments),
        failed_notifications=db.scalar(select(func.count()).select_from(NotificationJob).where(NotificationJob.status.in_([NotificationStatus.FAILED, NotificationStatus.REVIEW_REQUIRED]))) or 0,
        sync_errors=db.scalar(select(func.count()).select_from(SyncEvent).where(SyncEvent.status.in_([SyncStatus.FAILED, SyncStatus.CONFLICT]))) or 0,
    )

