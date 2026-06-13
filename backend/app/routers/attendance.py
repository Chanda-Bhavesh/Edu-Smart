import uuid
from datetime import date

from fastapi import APIRouter, Depends, File, UploadFile, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies.auth import (
    get_current_faculty, get_current_student,
    get_current_admin, get_current_user,
)
from app.models.user import User
from app.schemas.attendance import (
    ManualAttendanceRequest, EditAttendanceRequest, BulkAttendanceResult,
    QRGenerateRequest, QRGenerateResponse, QRScanRequest,
    AttendanceResponse, SessionAttendanceSummary,
    StudentAttendanceReport, FaceAttendanceResponse,
    AtRiskStudent,
)
from app.services import attendance as att_service

router = APIRouter(prefix="/attendance", tags=["Attendance"])


# ── Manual Attendance ──────────────────────────────────────────────────────────

@router.post("/manual", response_model=BulkAttendanceResult)
async def mark_manual(
    payload: ManualAttendanceRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_faculty),
):
    """
    Faculty: bulk-mark attendance for one class session.
    Provide the timetable_slot_id (which period) + date + list of student statuses.
    """
    return await att_service.mark_manual_attendance(db, payload, current_user.id)


@router.put("/{attendance_id}", response_model=AttendanceResponse)
async def edit_attendance(
    attendance_id: uuid.UUID,
    payload: EditAttendanceRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_faculty),
):
    """Faculty: edit a single attendance record within 24 hours of marking."""
    return await att_service.edit_attendance(db, attendance_id, payload, current_user.id)


# ── QR Attendance ──────────────────────────────────────────────────────────────

@router.post("/qr/generate", response_model=QRGenerateResponse)
async def generate_qr(
    payload: QRGenerateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_faculty),
):
    """
    Faculty: generate a QR code for a specific period (timetable_slot_id + date).
    The QR code is valid for 10 minutes only.
    """
    return await att_service.generate_qr_session(db, payload, current_user.id)


@router.post("/qr/scan", response_model=AttendanceResponse, status_code=status.HTTP_201_CREATED)
async def scan_qr(
    payload: QRScanRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_student),
):
    """Student: scan QR code to mark yourself present for a session."""
    return await att_service.scan_qr_attendance(db, payload, current_user.id)


# ── Face Recognition ───────────────────────────────────────────────────────────

@router.post("/face/register", status_code=status.HTTP_204_NO_CONTENT)
async def register_face(
    image: UploadFile = File(..., description="Student face photo (JPEG/PNG)"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_student),
):
    """Student: upload face photo once to enable face-recognition attendance."""
    await att_service.register_face(db, current_user.id, await image.read())


@router.post("/face/mark", response_model=FaceAttendanceResponse)
async def mark_face(
    slot_id:      uuid.UUID,
    session_date: date,
    image: UploadFile = File(..., description="Classroom photo"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_faculty),
):
    """Faculty: upload classroom photo to auto-mark attendance via face recognition."""
    return await att_service.mark_face_attendance(
        db, slot_id, session_date, await image.read(), current_user.id
    )


# ── Reports ────────────────────────────────────────────────────────────────────

@router.get("/session-summary", response_model=SessionAttendanceSummary)
async def session_summary(
    slot_id:      uuid.UUID,
    session_date: date = Query(default_factory=date.today),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """
    Get attendance summary for one class session.
    Shows present/absent counts and percentage for a specific period on a specific date.
    """
    return await att_service.get_session_summary(db, slot_id, session_date)


@router.get("/my-report", response_model=StudentAttendanceReport)
async def my_report(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_student),
):
    """Student: view my attendance percentage per subject across all sessions."""
    from app.models.student import Student
    from sqlalchemy import select
    result = await db.execute(select(Student).where(Student.user_id == current_user.id))
    student = result.scalar_one_or_none()
    if not student:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Student profile not found")
    return await att_service.get_student_attendance_report(db, student.id)


@router.get("/report/{student_id}", response_model=StudentAttendanceReport)
async def student_report(
    student_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    """Admin/Faculty: view any student's full attendance report."""
    return await att_service.get_student_attendance_report(db, student_id)


@router.get("/at-risk", response_model=list[AtRiskStudent])
async def at_risk(
    slot_id:   uuid.UUID,
    threshold: float = Query(75.0, ge=0, le=100),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Get students below the attendance threshold for a course."""
    return await att_service.get_at_risk_students(db, slot_id, threshold)
