import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies.auth import get_current_faculty, get_current_admin
from app.models.user import User
from app.schemas.faculty_attendance import (
    CheckInResponse, CheckOutResponse,
    LeaveRequestCreate, LeaveReviewRequest, LeaveRequestResponse,
    FacultyAttendanceResponse, FacultyMonthlyReport,
)
from app.services import faculty_attendance as fa_service

router = APIRouter(prefix="/faculty-attendance", tags=["Faculty Attendance"])


# ── Check-In / Check-Out ──────────────────────────────────────────────────────

@router.post("/check-in", response_model=CheckInResponse, status_code=status.HTTP_201_CREATED)
async def check_in(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_faculty),
):
    """Faculty: mark arrival time for today."""
    return await fa_service.check_in(db, current_user.id)


@router.post("/check-out", response_model=CheckOutResponse)
async def check_out(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_faculty),
):
    """Faculty: mark departure time and auto-calculate working hours."""
    return await fa_service.check_out(db, current_user.id)


# ── Leave Requests ────────────────────────────────────────────────────────────

@router.post("/leave", response_model=LeaveRequestResponse, status_code=status.HTTP_201_CREATED)
async def apply_leave(
    payload: LeaveRequestCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_faculty),
):
    """Faculty: submit a leave request."""
    return await fa_service.apply_leave(db, current_user.id, payload)


@router.get("/leave/my-requests", response_model=list[LeaveRequestResponse])
async def my_leave_requests(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_faculty),
):
    """Faculty: view all my leave requests and their status."""
    return await fa_service.get_my_leave_requests(db, current_user.id)


@router.get("/leave/pending", response_model=list[LeaveRequestResponse])
async def pending_leave_requests(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    """Admin: view all pending leave requests awaiting review."""
    return await fa_service.get_pending_leaves(db)


@router.patch("/leave/{leave_id}/review", response_model=LeaveRequestResponse)
async def review_leave(
    leave_id: uuid.UUID,
    payload: LeaveReviewRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    """Admin: approve or reject a faculty leave request."""
    return await fa_service.review_leave(db, leave_id, current_user.id, payload)


# ── Monthly Report ────────────────────────────────────────────────────────────

@router.get("/report/monthly", response_model=FacultyMonthlyReport)
async def monthly_report(
    month: int = Query(..., ge=1, le=12),
    year: int  = Query(..., ge=2020),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_faculty),
):
    """Faculty: get my attendance report for a specific month."""
    return await fa_service.get_monthly_report(db, current_user.id, month, year)
