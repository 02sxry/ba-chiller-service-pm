import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.db import bool_filter
from app.domain.enums import PlanningMode
from app.domain.models import AnnualPlan, Equipment, NextYearPlanDraft, PMSlot, User
from app.domain.schemas import PlanApproveRequest, PlanPreviewRequest
from app.services.audit import record_audit

THAI_MONTHS = [
    "มกราคม", "กุมภาพันธ์", "มีนาคม", "เมษายน", "พฤษภาคม", "มิถุนายน",
    "กรกฎาคม", "สิงหาคม", "กันยายน", "ตุลาคม", "พฤศจิกายน", "ธันวาคม",
]
AUTOMATIC_FREQUENCIES = {1, 2, 3, 4, 6, 12}


class PlanningError(ValueError):
    pass


def calculate_months(data: PlanPreviewRequest) -> list[int]:
    if data.planning_mode == PlanningMode.AUTOMATIC:
        if data.annual_frequency not in AUTOMATIC_FREQUENCIES:
            raise PlanningError("โหมดอัตโนมัติรองรับความถี่ 1, 2, 3, 4, 6 หรือ 12 ครั้งต่อปี")
        if data.start_month is None:
            raise PlanningError("โหมดอัตโนมัติต้องระบุเดือนเริ่มต้น")
        interval = 12 // data.annual_frequency
        months = {
            ((data.start_month - 1 + index * interval) % 12) + 1
            for index in range(data.annual_frequency)
        }
    else:
        months = set(data.planned_months or [])
        if len(months) != len(data.planned_months or []):
            raise PlanningError("เดือนที่วางแผนต้องไม่ซ้ำ")
        if len(months) != data.annual_frequency:
            raise PlanningError("จำนวนเดือนต้องเท่ากับความถี่ต่อปี")
    if any(month < 1 or month > 12 for month in months):
        raise PlanningError("เดือนต้องอยู่ระหว่าง 1 ถึง 12")
    return sorted(months)


def approve_plan(db: Session, request: PlanApproveRequest, admin: User) -> AnnualPlan:
    equipment = db.get(Equipment, request.equipment_id)
    if not equipment or not equipment.active:
        raise PlanningError("ไม่พบอุปกรณ์ที่ใช้งานอยู่")
    months = calculate_months(request)
    plan = AnnualPlan(
        equipment_id=request.equipment_id,
        plan_year=request.plan_year,
        annual_frequency=request.annual_frequency,
        planning_mode=request.planning_mode,
        start_month=request.start_month,
        planned_months=months,
        approved_by_id=admin.id,
    )
    plan.slots = [
        PMSlot(equipment_id=request.equipment_id, plan_year=request.plan_year, planned_month=month)
        for month in months
    ]
    db.add(plan)
    try:
        db.flush()
    except IntegrityError as exc:
        raise PlanningError("มีแผนรายปีของอุปกรณ์นี้แล้ว") from exc
    record_audit(
        db,
        actor=admin,
        action="ANNUAL_PLAN_APPROVED",
        entity_type="annual_plan",
        entity_id=plan.id,
        new_values={"year": plan.plan_year, "months": months},
    )
    return plan


def generate_next_year_drafts(db: Session, source_year: int, target_year: int) -> list[NextYearPlanDraft]:
    if target_year != source_year + 1:
        raise PlanningError("ปีเป้าหมายต้องเป็นปีถัดจากปีต้นทาง")
    plans = db.scalars(
        select(AnnualPlan).join(Equipment).where(
            AnnualPlan.plan_year == source_year,
            bool_filter(AnnualPlan.active, True),
            bool_filter(Equipment.active, True),
        )
    ).all()
    drafts: list[NextYearPlanDraft] = []
    for plan in plans:
        draft = db.scalar(
            select(NextYearPlanDraft).where(
                NextYearPlanDraft.equipment_id == plan.equipment_id,
                NextYearPlanDraft.target_year == target_year,
            )
        )
        if draft:
            drafts.append(draft)
            continue
        draft = NextYearPlanDraft(
            source_plan_id=plan.id,
            equipment_id=plan.equipment_id,
            target_year=target_year,
            annual_frequency=plan.annual_frequency,
            planning_mode=plan.planning_mode,
            start_month=plan.start_month,
            planned_months=list(plan.planned_months),
        )
        db.add(draft)
        drafts.append(draft)
    db.flush()
    return drafts


@dataclass
class BulkResult:
    draft_id: uuid.UUID
    approved: bool
    plan_id: uuid.UUID | None = None
    error: str | None = None


def bulk_approve_drafts(
    db: Session, draft_ids: list[uuid.UUID], admin: User
) -> list[BulkResult]:
    results: list[BulkResult] = []
    for draft_id in draft_ids:
        try:
            with db.begin_nested():
                draft = db.get(NextYearPlanDraft, draft_id)
                if not draft:
                    raise PlanningError("ไม่พบ draft")
                if draft.excluded:
                    raise PlanningError("draft ถูกยกเว้น")
                if draft.approved_plan_id:
                    raise PlanningError("draft นี้อนุมัติแล้ว")
                request = PlanApproveRequest(
                    equipment_id=draft.equipment_id,
                    plan_year=draft.target_year,
                    annual_frequency=draft.annual_frequency,
                    planning_mode=draft.planning_mode,
                    start_month=draft.start_month,
                    planned_months=draft.planned_months,
                )
                plan = approve_plan(db, request, admin)
                draft.approved_plan_id = plan.id
                db.flush()
                results.append(BulkResult(draft_id=draft.id, approved=True, plan_id=plan.id))
        except (PlanningError, IntegrityError) as exc:
            results.append(BulkResult(draft_id=draft_id, approved=False, error=str(exc)))
    return results

