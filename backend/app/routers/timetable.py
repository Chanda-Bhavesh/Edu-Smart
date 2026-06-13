import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies.auth import get_current_admin, get_current_faculty, get_current_user
from app.models.user import User
from app.schemas.timetable import (
    TimetableSlotCreate, TimetableSlotUpdate,
    TimetableSlotResponse, WeeklyTimetable,
    FacultyDaySchedule, DaySchedule,
)
from app.services import timetable as tt_service

router = APIRouter(prefix="/timetable", tags=["Timetable"])


@router.post("", response_model=TimetableSlotResponse, status_code=status.HTTP_201_CREATED)
async def create_slot(
    payload: TimetableSlotCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    """Admin: add one period slot to a course assignment."""
    return await tt_service.create_slot(db, payload)


@router.get("/assignment/{assignment_id}", response_model=list[TimetableSlotResponse])
async def slots_by_assignment(
    assignment_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Get all timetable slots for a course assignment."""
    return await tt_service.get_slots_by_assignment(db, assignment_id)


@router.get("/weekly", response_model=WeeklyTimetable)
async def weekly_timetable(
    semester_id: uuid.UUID,
    section: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """
    Get the full week timetable for a section.
    Students use this to view their weekly class schedule.
    """
    return await tt_service.get_weekly_timetable(db, semester_id, section)


@router.get("/my-today", response_model=FacultyDaySchedule)
async def my_today_schedule(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_faculty),
):
    """
    Faculty: get today's class schedule.
    Shows all periods the faculty has to teach today.
    """
    return await tt_service.get_faculty_today_schedule(db, current_user.id)


@router.get("/my-week", response_model=list[DaySchedule])
async def my_week_schedule(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_faculty),
):
    """Faculty: get the full weekly teaching schedule."""
    return await tt_service.get_faculty_week_schedule(db, current_user.id)


@router.get("/{slot_id}", response_model=TimetableSlotResponse)
async def get_slot(
    slot_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Get a single timetable slot by ID."""
    return await tt_service.get_slot(db, slot_id)


@router.patch("/{slot_id}", response_model=TimetableSlotResponse)
async def update_slot(
    slot_id: uuid.UUID,
    payload: TimetableSlotUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    """Admin: update time, room, or active status of a slot."""
    return await tt_service.update_slot(db, slot_id, payload)


@router.delete("/{slot_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_slot(
    slot_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    """Admin: permanently remove a timetable slot."""
    await tt_service.delete_slot(db, slot_id)
