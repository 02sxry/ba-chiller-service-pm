import uuid
from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.domain.enums import AppointmentStatus, ChangeSource, DraftStatus, DraftType, PlanningMode, Role, SyncStatus


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=100)
    password: str


class UserCreateRequest(BaseModel):
    username: str = Field(min_length=1, max_length=100)
    display_name: str = Field(min_length=1, max_length=255)
    password: str = Field(min_length=4, max_length=255)
    role: Role = Role.VIEWER


class UserUpdateRequest(BaseModel):
    display_name: str | None = Field(default=None, min_length=1, max_length=255)
    password: str | None = Field(default=None, min_length=4, max_length=255)
    role: Role | None = None


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserView(ORMModel):
    id: uuid.UUID
    username: str | None
    # Email remains in the response for backwards compatibility. It is not the
    # login identifier, and older local records may contain an internal address
    # such as @local.invalid that EmailStr rejects on response serialization.
    email: str
    display_name: str
    role: Role
    active: bool


class HospitalCreate(BaseModel):
    hospital_code: str | None = Field(default=None, min_length=1, max_length=50)
    hospital_name: str = Field(min_length=1, max_length=255)
    notes: str | None = None

    @field_validator("hospital_code", mode="before")
    @classmethod
    def empty_hospital_code_is_none(cls, value: object) -> object:
        return None if isinstance(value, str) and not value.strip() else value


class HospitalUpdate(BaseModel):
    hospital_name: str | None = Field(default=None, min_length=1, max_length=255)
    notes: str | None = None


class HospitalView(HospitalCreate, ORMModel):
    id: uuid.UUID
    active: bool
    version: int
    created_at: datetime
    updated_at: datetime


class EquipmentCreate(BaseModel):
    equipment_code: str | None = Field(default=None, min_length=1, max_length=50)
    hospital_id: uuid.UUID
    manufacturer_id: uuid.UUID | None = None
    equipment_type_id: uuid.UUID | None = None
    equipment_name: str = Field(min_length=1, max_length=255)
    model: str | None = None
    serial_number: str | None = None
    room_location: str | None = None
    notes: str | None = None


class EquipmentUpdate(BaseModel):
    hospital_id: uuid.UUID | None = None
    equipment_name: str | None = Field(default=None, min_length=1, max_length=255)
    model: str | None = None
    serial_number: str | None = None
    room_location: str | None = None
    notes: str | None = None


class EquipmentView(EquipmentCreate, ORMModel):
    id: uuid.UUID
    active: bool
    version: int
    created_at: datetime
    updated_at: datetime


class PlanPreviewRequest(BaseModel):
    plan_year: int = Field(ge=2000, le=2200)
    annual_frequency: int = Field(ge=1, le=12)
    planning_mode: PlanningMode
    start_month: int | None = Field(default=None, ge=1, le=12)
    planned_months: list[int] | None = None


class PlanPreviewResponse(BaseModel):
    plan_year: int
    annual_frequency: int
    planned_months: list[int]
    display_months_th: list[str]


class PlanApproveRequest(PlanPreviewRequest):
    equipment_id: uuid.UUID


class PlanView(ORMModel):
    id: uuid.UUID
    equipment_id: uuid.UUID
    plan_year: int
    annual_frequency: int
    planning_mode: PlanningMode
    start_month: int | None
    planned_months: list[int]
    version: int


class SlotView(ORMModel):
    id: uuid.UUID
    yearly_plan_id: uuid.UUID
    equipment_id: uuid.UUID
    plan_year: int
    planned_month: int
    active: bool
    version: int


class ParsedSchedule(BaseModel):
    proposed_date: date | None = None
    hospital_text: str | None = None
    equipment_text: str | None = None
    technician_text: str | None = None
    notes: str | None = None
    ambiguous: bool = False
    errors: list[str] = Field(default_factory=list)


class TextIntakeRequest(BaseModel):
    source_event_id: str = Field(min_length=1, max_length=255)
    text: str = Field(min_length=1, max_length=5000)
    received_at: datetime


class SlotRecommendation(BaseModel):
    slot_id: uuid.UUID
    plan_year: int
    planned_month: int
    month_distance: int
    score: int
    warning: str | None = None
    has_appointment: bool


class AppointmentApproveRequest(BaseModel):
    pm_slot_id: uuid.UUID
    scheduled_date: date
    hospital_id: uuid.UUID
    equipment_id: uuid.UUID
    technician_id: uuid.UUID | None = None
    service_type: str = "PM"
    notes: str | None = None
    expected_slot_version: int


class AppointmentView(ORMModel):
    id: uuid.UUID
    pm_slot_id: uuid.UUID
    hospital_id: uuid.UUID
    equipment_id: uuid.UUID
    technician_id: uuid.UUID | None
    status: AppointmentStatus
    current_revision_id: uuid.UUID | None
    confirmed_revision_id: uuid.UUID | None
    confirmed_at: datetime | None
    confirmation_source: str | None
    version: int


class AppointmentSummary(BaseModel):
    id: uuid.UUID
    reference: str
    pm_slot_id: uuid.UUID
    hospital_id: uuid.UUID
    equipment_id: uuid.UUID
    hospital_name: str
    equipment_name: str
    plan_year: int
    planned_month: int
    scheduled_date: date
    status: AppointmentStatus
    revision_number: int
    confirmed_date: date | None
    admin_changed_after_confirmation: bool
    notification_warning: bool


class IntakeView(ORMModel):
    id: uuid.UUID
    source_type: str
    source_event_id: str
    raw_text: str | None
    parsed_data: dict[str, Any]
    state: str
    validation_errors: list[str]
    version: int
    created_at: datetime


class ConfirmRequest(BaseModel):
    token: str
    line_group_id: str


class RescheduleRequestInput(ConfirmRequest):
    preferred_date: date | None = None
    message: str | None = Field(default=None, max_length=2000)


class DateChangeRequest(BaseModel):
    scheduled_date: date
    expected_appointment_version: int
    reason: str = Field(min_length=1, max_length=2000)
    requested_by: str = Field(min_length=1, max_length=255)


class RevisionView(ORMModel):
    id: uuid.UUID
    appointment_id: uuid.UUID
    revision_number: int
    scheduled_date: date
    service_type: str
    notes: str | None
    change_source: ChangeSource
    reason: str | None
    created_at: datetime


class DashboardMetrics(BaseModel):
    total_pm_slots: int
    confirmed_appointments: int
    pending_confirmation: int
    pending_approval: int
    reschedule_requests: int
    unscheduled_slots: int
    upcoming_appointments: int
    past_due_unconfirmed: int
    unscheduled_backlog: int
    cancelled_appointments: int
    admin_changed_appointments: int
    failed_notifications: int
    sync_errors: int


class BulkApprovalResult(BaseModel):
    draft_id: uuid.UUID
    approved: bool
    plan_id: uuid.UUID | None = None
    error: str | None = None


class BulkApprovalRequest(BaseModel):
    draft_ids: list[uuid.UUID]

    @field_validator("draft_ids")
    @classmethod
    def unique_ids(cls, values: list[uuid.UUID]) -> list[uuid.UUID]:
        if len(values) != len(set(values)):
            raise ValueError("draft_ids ต้องไม่ซ้ำ")
        return values


class DraftView(ORMModel):
    id: uuid.UUID
    draft_type: DraftType
    status: DraftStatus
    original_text: str
    proposed_data: dict[str, Any]
    suggestions: list[dict[str, Any]]
    parent_draft_id: uuid.UUID | None
    resolved_record_id: uuid.UUID | None
    version: int
    created_at: datetime


class ApproveHospitalDraftRequest(BaseModel):
    hospital_code: str = Field(min_length=1, max_length=50)
    hospital_name: str = Field(min_length=1, max_length=255)


class MatchHospitalDraftRequest(BaseModel):
    hospital_id: uuid.UUID
    add_alias: bool = True


class ApproveEquipmentDraftRequest(BaseModel):
    equipment_code: str = Field(min_length=1, max_length=50)
    equipment_name: str = Field(min_length=1, max_length=255)
    manufacturer_id: uuid.UUID | None = None
    equipment_type_id: uuid.UUID | None = None
    model: str | None = None
    serial_number: str | None = None
    room_location: str | None = None
    notes: str | None = None


class ApprovePlanDraftRequest(BaseModel):
    annual_frequency: int = Field(ge=1, le=12)
    planning_mode: PlanningMode
    start_month: int | None = Field(default=None, ge=1, le=12)
    planned_months: list[int] | None = None


class HealthResponse(BaseModel):
    status: str
    database: str
    integrations: dict[str, Any]


class HospitalSheetSubmission(BaseModel):
    row_key: str = Field(min_length=1, max_length=255)
    record_id: uuid.UUID | None = None
    expected_version: int | None = Field(default=None, ge=1)
    operation: str
    hospital_code: str | None = None
    hospital_name: str | None = None
    notes: str | None = None


class SyncEventView(ORMModel):
    id: uuid.UUID
    idempotency_key: str
    direction: str
    entity_type: str
    entity_id: uuid.UUID | None
    payload: dict[str, Any]
    expected_version: int | None
    status: SyncStatus
    attempts: int
    last_error: str | None
    version: int
    created_at: datetime
    updated_at: datetime


class LineGroupCreate(BaseModel):
    line_group_id: str = Field(min_length=1, max_length=255)
    group_type: str
    hospital_id: uuid.UUID | None = None


class LineGroupView(LineGroupCreate, ORMModel):
    id: uuid.UUID
    active: bool
    version: int
    created_at: datetime
    updated_at: datetime

