import re
import uuid
from dataclasses import dataclass
from datetime import date

from rapidfuzz import fuzz
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.domain.models import Equipment, Hospital, PMSlot


def normalize_name(value: str) -> str:
    value = value.casefold().strip()
    value = re.sub(r"โรงพยาบาล|รพ\.?", "", value)
    value = re.sub(r"[\s._\-/]+", "", value)
    return value


@dataclass
class Match:
    record_id: uuid.UUID
    label: str
    score: int


def match_hospitals(db: Session, text: str, limit: int = 5) -> list[Match]:
    query = normalize_name(text)
    hospitals = db.scalars(select(Hospital).options(selectinload(Hospital.aliases)).where(Hospital.active.is_(True))).all()
    matches = []
    for hospital in hospitals:
        names = [hospital.hospital_name] + [a.alias for a in hospital.aliases]
        score = max(fuzz.ratio(query, normalize_name(name)) for name in names if name)
        matches.append(Match(hospital.id, hospital.hospital_name, int(score)))
    return sorted(matches, key=lambda item: item.score, reverse=True)[:limit]


def match_equipment(db: Session, hospital_id: uuid.UUID, text: str, limit: int = 5) -> list[Match]:
    query = normalize_name(text)
    equipment = db.scalars(
        select(Equipment).where(Equipment.hospital_id == hospital_id, Equipment.active.is_(True))
    ).all()
    matches = [
        Match(item.id, item.equipment_name, int(fuzz.ratio(query, normalize_name(item.equipment_name))))
        for item in equipment
    ]
    return sorted(matches, key=lambda item: item.score, reverse=True)[:limit]


def circular_month_distance(month_a: int, month_b: int) -> int:
    delta = abs(month_a - month_b)
    return min(delta, 12 - delta)


def recommend_slots(db: Session, equipment_id: uuid.UUID, proposed_date: date) -> list[dict]:
    slots = db.scalars(
        select(PMSlot)
        .options(selectinload(PMSlot.appointment))
        .where(PMSlot.equipment_id == equipment_id, PMSlot.active.is_(True))
    ).all()
    recommendations = []
    for slot in slots:
        distance = circular_month_distance(slot.planned_month, proposed_date.month)
        year_penalty = abs(slot.plan_year - proposed_date.year) * 8
        occupied_penalty = 80 if slot.appointment else 0
        score = 100 - distance * 15 - year_penalty - occupied_penalty
        warning = None
        if slot.appointment:
            warning = "Slot นี้มีนัดอยู่แล้ว ต้องใช้ขั้นตอนแก้ไขนัด"
        elif distance > 2:
            warning = "วันนัดห่างจากเดือนแผนมากกว่า 2 เดือน"
        recommendations.append({
            "slot_id": slot.id,
            "plan_year": slot.plan_year,
            "planned_month": slot.planned_month,
            "month_distance": distance,
            "score": score,
            "warning": warning,
            "has_appointment": slot.appointment is not None,
        })
    return sorted(recommendations, key=lambda item: item["score"], reverse=True)

