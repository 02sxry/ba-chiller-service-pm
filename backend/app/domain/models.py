import uuid
from datetime import date, datetime
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.domain.enums import (
    AppointmentStatus,
    ChangeSource,
    DraftStatus,
    DraftType,
    IntakeState,
    NotificationStatus,
    PlanningMode,
    Role,
    SyncStatus,
)


class IdMixin:
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class VersionMixin:
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    __mapper_args__ = {"version_id_col": version}


class User(IdMixin, TimestampMixin, Base):
    __tablename__ = "users"
    username: Mapped[str | None] = mapped_column(String(100), unique=True, index=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    display_name: Mapped[str] = mapped_column(String(255))
    role: Mapped[Role] = mapped_column(Enum(Role, name="user_role"), default=Role.VIEWER)
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class Hospital(IdMixin, TimestampMixin, VersionMixin, Base):
    __tablename__ = "hospitals"
    hospital_code: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    hospital_name: Mapped[str] = mapped_column(String(255), index=True)
    short_name: Mapped[str | None] = mapped_column(String(120))
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    notes: Mapped[str | None] = mapped_column(Text)
    aliases: Mapped[list["HospitalAlias"]] = relationship(back_populates="hospital", cascade="all, delete-orphan")
    equipment: Mapped[list["Equipment"]] = relationship(back_populates="hospital")


class HospitalAlias(IdMixin, TimestampMixin, Base):
    __tablename__ = "hospital_aliases"
    hospital_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("hospitals.id", ondelete="CASCADE"), index=True)
    alias: Mapped[str] = mapped_column(String(255))
    normalized_alias: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    hospital: Mapped[Hospital] = relationship(back_populates="aliases")


class Manufacturer(IdMixin, TimestampMixin, VersionMixin, Base):
    __tablename__ = "manufacturers"
    name: Mapped[str] = mapped_column(String(255), unique=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class EquipmentType(IdMixin, TimestampMixin, VersionMixin, Base):
    __tablename__ = "equipment_types"
    name: Mapped[str] = mapped_column(String(255), unique=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class Equipment(IdMixin, TimestampMixin, VersionMixin, Base):
    __tablename__ = "equipment"
    equipment_code: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    hospital_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("hospitals.id"), index=True)
    manufacturer_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("manufacturers.id"))
    equipment_type_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("equipment_types.id"))
    equipment_name: Mapped[str] = mapped_column(String(255))
    model: Mapped[str | None] = mapped_column(String(255))
    serial_number: Mapped[str | None] = mapped_column(String(255))
    room_location: Mapped[str | None] = mapped_column(String(255))
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    notes: Mapped[str | None] = mapped_column(Text)
    hospital: Mapped[Hospital] = relationship(back_populates="equipment")
    __table_args__ = (
        UniqueConstraint("hospital_id", "serial_number", name="uq_equipment_hospital_serial"),
        Index("ix_equipment_hospital_name", "hospital_id", "equipment_name"),
    )


class Technician(IdMixin, TimestampMixin, VersionMixin, Base):
    __tablename__ = "technicians"
    technician_code: Mapped[str] = mapped_column(String(50), unique=True)
    display_name: Mapped[str] = mapped_column(String(255))
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class MasterDataDraft(IdMixin, TimestampMixin, VersionMixin, Base):
    __tablename__ = "master_data_drafts"
    draft_type: Mapped[DraftType] = mapped_column(Enum(DraftType, name="draft_type"))
    status: Mapped[DraftStatus] = mapped_column(Enum(DraftStatus, name="draft_status"), default=DraftStatus.PENDING)
    original_text: Mapped[str] = mapped_column(Text)
    proposed_data: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    suggestions: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    parent_draft_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("master_data_drafts.id"))
    resolved_record_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    reviewed_by_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    review_notes: Mapped[str | None] = mapped_column(Text)


class AnnualPlan(IdMixin, TimestampMixin, VersionMixin, Base):
    __tablename__ = "annual_plans"
    equipment_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("equipment.id"), index=True)
    plan_year: Mapped[int] = mapped_column(Integer)
    annual_frequency: Mapped[int] = mapped_column(Integer)
    planning_mode: Mapped[PlanningMode] = mapped_column(Enum(PlanningMode, name="planning_mode"))
    start_month: Mapped[int | None] = mapped_column(Integer)
    planned_months: Mapped[list[int]] = mapped_column(JSON)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    approved_by_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    approved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    slots: Mapped[list["PMSlot"]] = relationship(back_populates="plan", cascade="all, delete-orphan")
    __table_args__ = (
        UniqueConstraint("equipment_id", "plan_year", name="uq_plan_equipment_year"),
        CheckConstraint("annual_frequency BETWEEN 1 AND 12", name="ck_plan_frequency"),
        CheckConstraint("plan_year BETWEEN 2000 AND 2200", name="ck_plan_year"),
    )


class NextYearPlanDraft(IdMixin, TimestampMixin, VersionMixin, Base):
    __tablename__ = "next_year_plan_drafts"
    source_plan_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("annual_plans.id"))
    equipment_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("equipment.id"), index=True)
    target_year: Mapped[int] = mapped_column(Integer)
    annual_frequency: Mapped[int] = mapped_column(Integer)
    planning_mode: Mapped[PlanningMode] = mapped_column(Enum(PlanningMode, name="next_year_planning_mode"))
    start_month: Mapped[int | None] = mapped_column(Integer)
    planned_months: Mapped[list[int]] = mapped_column(JSON)
    excluded: Mapped[bool] = mapped_column(Boolean, default=False)
    manually_edited: Mapped[bool] = mapped_column(Boolean, default=False)
    approved_plan_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("annual_plans.id"))
    __table_args__ = (
        UniqueConstraint("equipment_id", "target_year", name="uq_next_year_draft_equipment_year"),
    )


class PMSlot(IdMixin, TimestampMixin, VersionMixin, Base):
    __tablename__ = "pm_slots"
    yearly_plan_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("annual_plans.id", ondelete="CASCADE"), index=True)
    equipment_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("equipment.id"), index=True)
    plan_year: Mapped[int] = mapped_column(Integer, index=True)
    planned_month: Mapped[int] = mapped_column(Integer)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    plan: Mapped[AnnualPlan] = relationship(back_populates="slots")
    appointment: Mapped["Appointment | None"] = relationship(back_populates="slot", uselist=False)
    __table_args__ = (
        UniqueConstraint("yearly_plan_id", "planned_month", name="uq_slot_plan_month"),
        CheckConstraint("planned_month BETWEEN 1 AND 12", name="ck_slot_month"),
    )


class ScheduleIntake(IdMixin, TimestampMixin, VersionMixin, Base):
    __tablename__ = "schedule_intakes"
    source_type: Mapped[str] = mapped_column(String(30))
    source_event_id: Mapped[str] = mapped_column(String(255), unique=True)
    source_file_id: Mapped[str | None] = mapped_column(String(255))
    source_checksum: Mapped[str | None] = mapped_column(String(64), index=True)
    raw_text: Mapped[str | None] = mapped_column(Text)
    parsed_data: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    state: Mapped[IntakeState] = mapped_column(Enum(IntakeState, name="intake_state"), default=IntakeState.RECEIVED)
    validation_errors: Mapped[list[str]] = mapped_column(JSON, default=list)
    duplicate_of_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("schedule_intakes.id"))


class Appointment(IdMixin, TimestampMixin, VersionMixin, Base):
    __tablename__ = "appointments"
    pm_slot_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("pm_slots.id"), unique=True, index=True)
    hospital_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("hospitals.id"), index=True)
    equipment_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("equipment.id"), index=True)
    technician_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("technicians.id"))
    status: Mapped[AppointmentStatus] = mapped_column(Enum(AppointmentStatus, name="appointment_status"))
    current_revision_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    confirmed_revision_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    confirmation_source: Mapped[str | None] = mapped_column(String(50))
    slot: Mapped[PMSlot] = relationship(back_populates="appointment")
    revisions: Mapped[list["AppointmentRevision"]] = relationship(
        back_populates="appointment", cascade="all, delete-orphan", foreign_keys="AppointmentRevision.appointment_id"
    )


class AppointmentRevision(IdMixin, TimestampMixin, Base):
    __tablename__ = "appointment_revisions"
    appointment_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("appointments.id", ondelete="CASCADE"), index=True)
    revision_number: Mapped[int] = mapped_column(Integer)
    scheduled_date: Mapped[date] = mapped_column(Date, index=True)
    service_type: Mapped[str] = mapped_column(String(100), default="PM")
    notes: Mapped[str | None] = mapped_column(Text)
    change_source: Mapped[ChangeSource] = mapped_column(Enum(ChangeSource, name="change_source"))
    requested_by: Mapped[str | None] = mapped_column(String(255))
    approved_by_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    reason: Mapped[str | None] = mapped_column(Text)
    appointment: Mapped[Appointment] = relationship(back_populates="revisions", foreign_keys=[appointment_id])
    __table_args__ = (UniqueConstraint("appointment_id", "revision_number", name="uq_revision_number"),)


class RescheduleRequest(IdMixin, TimestampMixin, Base):
    __tablename__ = "reschedule_requests"
    appointment_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("appointments.id"), index=True)
    revision_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("appointment_revisions.id"))
    preferred_date: Mapped[date | None] = mapped_column(Date)
    message: Mapped[str | None] = mapped_column(Text)
    source_group_id: Mapped[str] = mapped_column(String(255))
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class LineGroupMapping(IdMixin, TimestampMixin, VersionMixin, Base):
    __tablename__ = "line_group_mappings"
    line_group_id: Mapped[str] = mapped_column(String(255), unique=True)
    group_type: Mapped[str] = mapped_column(String(30))
    hospital_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("hospitals.id"))
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class WebhookEvent(IdMixin, TimestampMixin, Base):
    __tablename__ = "webhook_events"
    provider_event_id: Mapped[str] = mapped_column(String(255), unique=True)
    payload_hash: Mapped[str] = mapped_column(String(64))
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class NotificationJob(IdMixin, TimestampMixin, VersionMixin, Base):
    __tablename__ = "notification_jobs"
    idempotency_key: Mapped[str] = mapped_column(String(255), unique=True)
    kind: Mapped[str] = mapped_column(String(80))
    destination_id: Mapped[str] = mapped_column(String(255))
    appointment_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("appointments.id"))
    revision_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("appointment_revisions.id"))
    payload: Mapped[dict[str, Any]] = mapped_column(JSON)
    status: Mapped[NotificationStatus] = mapped_column(
        Enum(NotificationStatus, name="notification_status"), default=NotificationStatus.PENDING
    )
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    available_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_error: Mapped[str | None] = mapped_column(Text)
    provider_message_id: Mapped[str | None] = mapped_column(String(255))


class SyncEvent(IdMixin, TimestampMixin, VersionMixin, Base):
    __tablename__ = "sync_events"
    idempotency_key: Mapped[str] = mapped_column(String(255), unique=True)
    direction: Mapped[str] = mapped_column(String(20))
    entity_type: Mapped[str] = mapped_column(String(80))
    entity_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    payload: Mapped[dict[str, Any]] = mapped_column(JSON)
    expected_version: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[SyncStatus] = mapped_column(Enum(SyncStatus, name="sync_status"), default=SyncStatus.PENDING)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    last_error: Mapped[str | None] = mapped_column(Text)


class DriveFile(IdMixin, TimestampMixin, Base):
    __tablename__ = "drive_files"
    drive_file_id: Mapped[str] = mapped_column(String(255), unique=True)
    folder_kind: Mapped[str] = mapped_column(String(80))
    original_name: Mapped[str] = mapped_column(String(500))
    mime_type: Mapped[str] = mapped_column(String(255))
    checksum: Mapped[str | None] = mapped_column(String(64), index=True)
    size_bytes: Mapped[int | None] = mapped_column(Integer)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)


class ActionToken(IdMixin, TimestampMixin, Base):
    __tablename__ = "action_tokens"
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    appointment_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("appointments.id"))
    revision_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("appointment_revisions.id"))
    action: Mapped[str] = mapped_column(String(30))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class AuditLog(IdMixin, Base):
    __tablename__ = "audit_logs"
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    actor_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    actor_label: Mapped[str | None] = mapped_column(String(255))
    action: Mapped[str] = mapped_column(String(100), index=True)
    entity_type: Mapped[str] = mapped_column(String(100))
    entity_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), index=True)
    old_values: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    new_values: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    reason: Mapped[str | None] = mapped_column(Text)
    source: Mapped[str] = mapped_column(String(50))
    revision_number: Mapped[int | None] = mapped_column(Integer)

