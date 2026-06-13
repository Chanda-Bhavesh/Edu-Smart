"""
Report download endpoints.

Student:
  GET /reports/attendance/csv           → my attendance CSV (date range)
  GET /reports/attendance/pdf           → my attendance PDF
  GET /reports/fees/statement           → my fee statement PDF

Faculty:
  GET /reports/assignments/{id}/csv     → submission marks CSV

Admin:
  GET /reports/fees/collection/{id}/csv → fee collection CSV for a structure
"""
import uuid
from datetime import date

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies.auth import get_current_admin, get_current_faculty, get_current_student
from app.models.user import User
from app.services import reports as report_service

router = APIRouter(prefix="/reports", tags=["Reports"])


# ── Student reports ────────────────────────────────────────────────────────────

@router.get("/attendance/csv")
async def my_attendance_csv(
    start_date: date = Query(...),
    end_date: date = Query(...),
    subject_id: uuid.UUID | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_student),
):
    """Student: download my attendance records as a CSV file."""
    from sqlalchemy import select
    from app.models.student import Student
    result = await db.execute(select(Student).where(Student.user_id == current_user.id))
    student = result.scalar_one_or_none()
    if not student:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Student profile not found")

    csv_bytes = await report_service.student_attendance_csv(
        db, student.id, start_date, end_date, subject_id
    )
    return Response(
        content=csv_bytes,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=attendance.csv"},
    )


@router.get("/attendance/pdf")
async def my_attendance_pdf(
    start_date: date = Query(...),
    end_date: date = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_student),
):
    """Student: download my attendance report as a PDF."""
    from sqlalchemy import select
    from app.models.student import Student
    result = await db.execute(select(Student).where(Student.user_id == current_user.id))
    student = result.scalar_one_or_none()
    if not student:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Student profile not found")

    pdf_bytes = await report_service.student_attendance_pdf(
        db, student.id, start_date, end_date
    )
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=attendance_report.pdf"},
    )


@router.get("/fees/statement")
async def my_fee_statement(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_student),
):
    """Student: download full fee statement PDF showing all semesters, payments, and balances."""
    from sqlalchemy import select
    from app.models.student import Student
    result = await db.execute(select(Student).where(Student.user_id == current_user.id))
    student = result.scalar_one_or_none()
    if not student:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Student profile not found")

    pdf_bytes = await report_service.fee_statement_pdf(db, student.id)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=fee_statement.pdf"},
    )


# ── Faculty reports ────────────────────────────────────────────────────────────

@router.get("/assignments/{assignment_id}/csv")
async def assignment_marks_csv(
    assignment_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_faculty),
):
    """Faculty: download submission marks for an assignment as CSV."""
    csv_bytes = await report_service.assignment_marks_csv(
        db, assignment_id, current_user.id
    )
    return Response(
        content=csv_bytes,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=marks_{assignment_id}.csv"},
    )


# ── Admin reports ──────────────────────────────────────────────────────────────

@router.get("/fees/collection/{fee_structure_id}/csv")
async def fee_collection_csv(
    fee_structure_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    """Admin: download full fee collection status for a fee structure as CSV."""
    csv_bytes = await report_service.fee_collection_csv(db, fee_structure_id)
    return Response(
        content=csv_bytes,
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=fee_collection_{fee_structure_id}.csv"
        },
    )
