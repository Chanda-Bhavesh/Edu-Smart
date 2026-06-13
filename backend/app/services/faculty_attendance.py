import uuid
from datetime import date, datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import select, func, extract
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.faculty import Faculty
from app.models.faculty_attendance import (
    FacultyAttendance, FacultyAttendanceStatus,
    LeaveRequest, LeaveStatus,
)
from app.schemas.faculty_attendance import LeaveRequestCreate, LeaveReviewRequest


async def _get_faculty(db: AsyncSession, user_id: uuid.UUID) -> Faculty:
    result = await db.execute(select(Faculty).where(Faculty.user_id == user_id))
    faculty = result.scalar_one_or_none()
    if not faculty:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Faculty profile not found")
    return faculty


# ── Check-In ──────────────────────────────────────────────────────────────────

async def check_in(db: AsyncSession, faculty_user_id: uuid.UUID) -> FacultyAttendance:
    faculty    = await _get_faculty(db, faculty_user_id)
    today      = date.today()
    now        = datetime.now(timezone.utc)

    existing = await db.execute(
        select(FacultyAttendance).where(
            FacultyAttendance.faculty_id == faculty.id,
            FacultyAttendance.date == today,
        )
    )
    record = existing.scalar_one_or_none()

    if record:
        if record.check_in_time:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Already checked in today")
        record.check_in_time = now
        record.status = FacultyAttendanceStatus.present
    else:
        record = FacultyAttendance(
            faculty_id=faculty.id,
            date=today,
            check_in_time=now,
            status=FacultyAttendanceStatus.present,
        )
        db.add(record)

    await db.flush()
    return record


# ── Check-Out ─────────────────────────────────────────────────────────────────

async def check_out(db: AsyncSession, faculty_user_id: uuid.UUID) -> FacultyAttendance:
    faculty = await _get_faculty(db, faculty_user_id)
    today   = date.today()
    now     = datetime.now(timezone.utc)

    result = await db.execute(
        select(FacultyAttendance).where(
            FacultyAttendance.faculty_id == faculty.id,
            FacultyAttendance.date == today,
        )
    )
    record = result.scalar_one_or_none()

    if not record or not record.check_in_time:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No check-in found for today")
    if record.check_out_time:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Already checked out today")

    record.check_out_time = now

    check_in_aware = record.check_in_time
    if check_in_aware.tzinfo is None:
        check_in_aware = check_in_aware.replace(tzinfo=timezone.utc)

    hours = (now - check_in_aware).total_seconds() / 3600
    record.working_hours = round(hours, 2)

    if hours < 4:
        record.status = FacultyAttendanceStatus.half_day

    await db.flush()
    return record


# ── Leave Requests ────────────────────────────────────────────────────────────

async def apply_leave(
    db: AsyncSession,
    faculty_user_id: uuid.UUID,
    payload: LeaveRequestCreate,
) -> LeaveRequest:
    faculty = await _get_faculty(db, faculty_user_id)

    leave = LeaveRequest(
        faculty_id=faculty.id,
        leave_type=payload.leave_type,
        start_date=payload.start_date,
        end_date=payload.end_date,
        reason=payload.reason,
        status=LeaveStatus.pending,
    )
    db.add(leave)
    await db.flush()
    return leave


async def get_my_leave_requests(
    db: AsyncSession,
    faculty_user_id: uuid.UUID,
) -> list[LeaveRequest]:
    faculty = await _get_faculty(db, faculty_user_id)
    result  = await db.execute(
        select(LeaveRequest)
        .where(LeaveRequest.faculty_id == faculty.id)
        .order_by(LeaveRequest.applied_at.desc())
    )
    return list(result.scalars().all())


async def get_pending_leaves(db: AsyncSession) -> list[LeaveRequest]:
    result = await db.execute(
        select(LeaveRequest)
        .where(LeaveRequest.status == LeaveStatus.pending)
        .order_by(LeaveRequest.applied_at)
    )
    return list(result.scalars().all())


async def review_leave(
    db: AsyncSession,
    leave_id: uuid.UUID,
    reviewer_user_id: uuid.UUID,
    payload: LeaveReviewRequest,
) -> LeaveRequest:
    result = await db.execute(select(LeaveRequest).where(LeaveRequest.id == leave_id))
    leave  = result.scalar_one_or_none()
    if not leave:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Leave request not found")
    if leave.status != LeaveStatus.pending:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Leave request already reviewed")

    leave.status         = payload.status
    leave.review_comment = payload.review_comment
    leave.reviewed_by    = reviewer_user_id
    leave.reviewed_at    = datetime.now(timezone.utc)

    # If approved, mark attendance as on_leave for each day in the range
    if payload.status == LeaveStatus.approved:
        current = leave.start_date
        from datetime import timedelta
        while current <= leave.end_date:
            existing = await db.execute(
                select(FacultyAttendance).where(
                    FacultyAttendance.faculty_id == leave.faculty_id,
                    FacultyAttendance.date == current,
                )
            )
            att = existing.scalar_one_or_none()
            if att:
                att.status = FacultyAttendanceStatus.on_leave
            else:
                db.add(FacultyAttendance(
                    faculty_id=leave.faculty_id,
                    date=current,
                    status=FacultyAttendanceStatus.on_leave,
                ))
            current += timedelta(days=1)

    await db.flush()
    return leave


# ── Monthly Report ────────────────────────────────────────────────────────────

async def get_monthly_report(
    db: AsyncSession,
    faculty_user_id: uuid.UUID,
    month: int,
    year: int,
) -> dict:
    faculty = await _get_faculty(db, faculty_user_id)

    result = await db.execute(
        select(FacultyAttendance).where(
            FacultyAttendance.faculty_id == faculty.id,
            extract("month", FacultyAttendance.date) == month,
            extract("year",  FacultyAttendance.date) == year,
        ).order_by(FacultyAttendance.date)
    )
    records = list(result.scalars().all())

    present   = sum(1 for r in records if r.status == FacultyAttendanceStatus.present)
    absent    = sum(1 for r in records if r.status == FacultyAttendanceStatus.absent)
    on_leave  = sum(1 for r in records if r.status == FacultyAttendanceStatus.on_leave)
    half_days = sum(1 for r in records if r.status == FacultyAttendanceStatus.half_day)
    total_hrs = sum(r.working_hours or 0.0 for r in records)

    return {
        "faculty_id":          faculty.id,
        "month":               month,
        "year":                year,
        "total_working_days":  len(records),
        "present_days":        present,
        "absent_days":         absent,
        "leave_days":          on_leave,
        "half_days":           half_days,
        "total_working_hours": round(total_hrs, 2),
        "records":             records,
    }
