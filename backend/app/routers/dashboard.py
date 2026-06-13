"""
Analytics & Dashboard endpoints.

Student:   GET /dashboard/student
Faculty:   GET /dashboard/faculty
Admin:     GET /dashboard/admin
Trends:    GET /dashboard/trends/attendance
           GET /dashboard/trends/fees
"""
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies.auth import get_current_admin, get_current_faculty, get_current_student
from app.models.user import User
from app.schemas.dashboard import (
    AdminDashboard, AttendanceTrend, FacultyDashboard,
    FeeCollectionTrend, StudentDashboard,
)
from app.services import dashboard as dash_service

router = APIRouter(prefix="/dashboard", tags=["Analytics & Dashboards"])


@router.get("/student", response_model=StudentDashboard)
async def student_dashboard(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_student),
):
    """
    Student: personalised dashboard.
    Returns attendance %, upcoming assignment deadlines (7 days),
    active fee balance, certificate statuses, and unread notification count.
    """
    return await dash_service.get_student_dashboard(db, current_user.id)


@router.get("/faculty", response_model=FacultyDashboard)
async def faculty_dashboard(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_faculty),
):
    """
    Faculty: personalised dashboard.
    Returns today's class schedule, pending grading queue,
    subject performance averages, and leave status.
    """
    return await dash_service.get_faculty_dashboard(db, current_user.id)


@router.get("/admin", response_model=AdminDashboard)
async def admin_dashboard(
    department_id: Optional[uuid.UUID] = Query(
        default=None,
        description="Filter to a specific department (dept_admin use case)",
    ),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    """
    Admin: org-wide dashboard.
    Returns headcounts, today's attendance rate, fee collection stats,
    pending certificate requests, and department-wise breakdown.
    Dept admins can pass their department_id to scope the view.
    """
    return await dash_service.get_admin_dashboard(db, current_user.id, department_id)


@router.get("/trends/attendance", response_model=AttendanceTrend)
async def attendance_trend(
    weeks: int = Query(default=8, ge=1, le=26),
    department_id: Optional[uuid.UUID] = Query(default=None),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    """
    Admin: weekly attendance rate for the past N weeks.
    Returns data points for a line chart.
    Optionally scope to a single department.
    """
    return await dash_service.get_attendance_trend(db, weeks, department_id)


@router.get("/trends/fees", response_model=FeeCollectionTrend)
async def fee_trend(
    academic_year: Optional[str] = Query(
        default=None,
        description="e.g. '2024-25' — omit to get all-time data",
    ),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    """
    Admin: monthly fee collection amounts for a bar chart.
    Pass academic_year to filter (e.g. '2024-25').
    """
    return await dash_service.get_fee_collection_trend(db, academic_year)
