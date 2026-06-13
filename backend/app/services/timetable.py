import uuid
from datetime import date, datetime, timezone
from collections import defaultdict

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.timetable import TimetableSlot, DayOfWeek
from app.models.course_assignment import CourseAssignment
from app.models.faculty import Faculty
from app.models.semester import Semester
from app.models.department import Department
from app.schemas.timetable import TimetableSlotCreate, TimetableSlotUpdate

# Python weekday() → DayOfWeek mapping (Monday=0 ... Saturday=5)
_WEEKDAY_MAP = {
    0: DayOfWeek.monday,
    1: DayOfWeek.tuesday,
    2: DayOfWeek.wednesday,
    3: DayOfWeek.thursday,
    4: DayOfWeek.friday,
    5: DayOfWeek.saturday,
}


# ── Internal loader ────────────────────────────────────────────────────────────

async def _load(db: AsyncSession, slot_id: uuid.UUID) -> TimetableSlot:
    result = await db.execute(
        select(TimetableSlot)
        .where(TimetableSlot.id == slot_id)
        .options(
            selectinload(TimetableSlot.course_assignment)
            .selectinload(CourseAssignment.subject),
            selectinload(TimetableSlot.course_assignment)
            .selectinload(CourseAssignment.faculty)
            .selectinload(Faculty.user),
            selectinload(TimetableSlot.course_assignment)
            .selectinload(CourseAssignment.semester),
        )
    )
    slot = result.scalar_one_or_none()
    if not slot:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Timetable slot not found")
    return slot


def _to_response(slot: TimetableSlot) -> dict:
    ca = slot.course_assignment
    return {
        "id":                   slot.id,
        "course_assignment_id": slot.course_assignment_id,
        "day_of_week":          slot.day_of_week,
        "start_time":           slot.start_time,
        "end_time":             slot.end_time,
        "room_number":          slot.room_number,
        "is_active":            slot.is_active,
        "subject":              {"id": ca.subject.id, "name": ca.subject.name, "code": ca.subject.code},
        "faculty_name":         ca.faculty.user.full_name,
        "section":              ca.section,
        "semester_number":      ca.semester.number,
    }


# ── CRUD ───────────────────────────────────────────────────────────────────────

async def create_slot(db: AsyncSession, payload: TimetableSlotCreate) -> dict:
    # Verify course assignment exists
    ca_result = await db.execute(
        select(CourseAssignment).where(CourseAssignment.id == payload.course_assignment_id)
    )
    if not ca_result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course assignment not found")

    # Conflict check: same assignment, same day, same start time
    conflict = await db.execute(
        select(TimetableSlot).where(
            TimetableSlot.course_assignment_id == payload.course_assignment_id,
            TimetableSlot.day_of_week == payload.day_of_week,
            TimetableSlot.start_time == payload.start_time,
        )
    )
    if conflict.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A slot already exists for this class on {payload.day_of_week.value} at {payload.start_time}",
        )

    slot = TimetableSlot(**payload.model_dump())
    db.add(slot)
    await db.flush()
    return _to_response(await _load(db, slot.id))


async def get_slot(db: AsyncSession, slot_id: uuid.UUID) -> dict:
    return _to_response(await _load(db, slot_id))


async def get_slots_by_assignment(db: AsyncSession, assignment_id: uuid.UUID) -> list[dict]:
    result = await db.execute(
        select(TimetableSlot)
        .where(TimetableSlot.course_assignment_id == assignment_id)
        .options(
            selectinload(TimetableSlot.course_assignment).selectinload(CourseAssignment.subject),
            selectinload(TimetableSlot.course_assignment).selectinload(CourseAssignment.faculty).selectinload(Faculty.user),
            selectinload(TimetableSlot.course_assignment).selectinload(CourseAssignment.semester),
        )
        .order_by(TimetableSlot.day_of_week, TimetableSlot.start_time)
    )
    return [_to_response(s) for s in result.scalars().all()]


async def update_slot(db: AsyncSession, slot_id: uuid.UUID, payload: TimetableSlotUpdate) -> dict:
    slot = await _load(db, slot_id)
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(slot, field, value)
    await db.flush()
    return _to_response(await _load(db, slot_id))


async def delete_slot(db: AsyncSession, slot_id: uuid.UUID) -> None:
    slot = await _load(db, slot_id)
    await db.delete(slot)


# ── Schedule views ─────────────────────────────────────────────────────────────

async def get_weekly_timetable(
    db: AsyncSession,
    semester_id: uuid.UUID,
    section: str,
) -> dict:
    """
    Returns the full weekly schedule for a section —
    used on the student timetable page.
    """
    result = await db.execute(
        select(TimetableSlot)
        .join(TimetableSlot.course_assignment)
        .options(
            selectinload(TimetableSlot.course_assignment).selectinload(CourseAssignment.subject),
            selectinload(TimetableSlot.course_assignment).selectinload(CourseAssignment.faculty).selectinload(Faculty.user),
            selectinload(TimetableSlot.course_assignment).selectinload(CourseAssignment.semester).selectinload(Semester.department),
        )
        .where(
            CourseAssignment.semester_id == semester_id,
            CourseAssignment.section     == section,
            TimetableSlot.is_active      == True,
        )
        .order_by(TimetableSlot.day_of_week, TimetableSlot.start_time)
    )
    slots = result.scalars().all()

    if not slots:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No timetable found for this section")

    # Group by day
    by_day: dict[str, list] = defaultdict(list)
    for slot in slots:
        by_day[slot.day_of_week.value].append(_to_response(slot))

    ca      = slots[0].course_assignment
    sem     = ca.semester
    dept    = sem.department

    day_order = [d.value for d in DayOfWeek]
    schedule  = [
        {"day_of_week": day, "slots": by_day.get(day, [])}
        for day in day_order
    ]

    return {
        "department_name": dept.name,
        "semester_number": sem.number,
        "section":         section,
        "academic_year":   ca.academic_year,
        "schedule":        schedule,
    }


async def get_faculty_today_schedule(
    db: AsyncSession,
    faculty_user_id: uuid.UUID,
) -> dict:
    """
    Returns today's slots for a faculty member —
    used on the faculty dashboard.
    """
    fac_result = await db.execute(select(Faculty).where(Faculty.user_id == faculty_user_id))
    faculty    = fac_result.scalar_one_or_none()
    if not faculty:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Faculty profile not found")

    today       = date.today()
    today_dow   = _WEEKDAY_MAP.get(today.weekday())

    if today_dow is None:
        # Sunday — no classes
        return {"date": str(today), "day_of_week": "sunday", "slots": []}

    result = await db.execute(
        select(TimetableSlot)
        .join(TimetableSlot.course_assignment)
        .options(
            selectinload(TimetableSlot.course_assignment).selectinload(CourseAssignment.subject),
            selectinload(TimetableSlot.course_assignment).selectinload(CourseAssignment.faculty).selectinload(Faculty.user),
            selectinload(TimetableSlot.course_assignment).selectinload(CourseAssignment.semester),
        )
        .where(
            CourseAssignment.faculty_id == faculty.id,
            TimetableSlot.day_of_week   == today_dow,
            TimetableSlot.is_active     == True,
        )
        .order_by(TimetableSlot.start_time)
    )
    slots = result.scalars().all()

    return {
        "date":        str(today),
        "day_of_week": today_dow.value,
        "slots":       [_to_response(s) for s in slots],
    }


async def get_faculty_week_schedule(
    db: AsyncSession,
    faculty_user_id: uuid.UUID,
) -> list[dict]:
    """Full week schedule for a faculty member."""
    fac_result = await db.execute(select(Faculty).where(Faculty.user_id == faculty_user_id))
    faculty    = fac_result.scalar_one_or_none()
    if not faculty:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Faculty profile not found")

    result = await db.execute(
        select(TimetableSlot)
        .join(TimetableSlot.course_assignment)
        .options(
            selectinload(TimetableSlot.course_assignment).selectinload(CourseAssignment.subject),
            selectinload(TimetableSlot.course_assignment).selectinload(CourseAssignment.faculty).selectinload(Faculty.user),
            selectinload(TimetableSlot.course_assignment).selectinload(CourseAssignment.semester),
        )
        .where(
            CourseAssignment.faculty_id == faculty.id,
            TimetableSlot.is_active     == True,
        )
        .order_by(TimetableSlot.day_of_week, TimetableSlot.start_time)
    )
    slots = result.scalars().all()

    by_day: dict[str, list] = defaultdict(list)
    for slot in slots:
        by_day[slot.day_of_week.value].append(_to_response(slot))

    day_order = [d.value for d in DayOfWeek]
    return [{"day_of_week": day, "slots": by_day.get(day, [])} for day in day_order]
