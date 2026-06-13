import uuid
from datetime import date, datetime, timezone, timedelta

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.attendance import Attendance, AttendanceStatus, AttendanceMethod, QRSession
from app.models.timetable import TimetableSlot
from app.models.course_assignment import CourseAssignment
from app.models.student import Student, StudentStatus
from app.models.student_face import StudentFaceEncoding
from app.models.subject import student_enrollments
from app.models.faculty import Faculty
from app.models.user import User
from app.schemas.attendance import (
    ManualAttendanceRequest, EditAttendanceRequest,
    QRGenerateRequest, QRScanRequest,
)
from app.utils import qr as qr_utils
from app.utils import face as face_utils


# ── Internal helpers ───────────────────────────────────────────────────────────

async def _load_slot(db: AsyncSession, slot_id: uuid.UUID) -> TimetableSlot:
    result = await db.execute(
        select(TimetableSlot)
        .where(TimetableSlot.id == slot_id)
        .options(
            selectinload(TimetableSlot.course_assignment)
            .selectinload(CourseAssignment.subject),
            selectinload(TimetableSlot.course_assignment)
            .selectinload(CourseAssignment.faculty),
            selectinload(TimetableSlot.course_assignment)
            .selectinload(CourseAssignment.semester),
        )
    )
    slot = result.scalar_one_or_none()
    if not slot:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Timetable slot not found")
    return slot


async def _get_faculty(db: AsyncSession, user_id: uuid.UUID) -> Faculty:
    result = await db.execute(select(Faculty).where(Faculty.user_id == user_id))
    faculty = result.scalar_one_or_none()
    if not faculty:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Faculty profile not found")
    return faculty


async def _get_enrolled_students(db: AsyncSession, ca: CourseAssignment) -> list[Student]:
    result = await db.execute(
        select(Student)
        .join(student_enrollments, student_enrollments.c.student_id == Student.id)
        .where(
            student_enrollments.c.subject_id == ca.subject_id,
            Student.semester_id == ca.semester_id,
            Student.section     == ca.section,
            Student.status      == StudentStatus.active,
        )
    )
    return list(result.scalars().all())


# ── Manual Attendance ──────────────────────────────────────────────────────────

async def mark_manual_attendance(
    db: AsyncSession,
    payload: ManualAttendanceRequest,
    faculty_user_id: uuid.UUID,
) -> dict:
    slot    = await _load_slot(db, payload.timetable_slot_id)
    ca      = slot.course_assignment
    faculty = await _get_faculty(db, faculty_user_id)

    if ca.faculty_id != faculty.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You are not assigned to this class")

    created = updated = 0

    for entry in payload.entries:
        existing = await db.execute(
            select(Attendance).where(
                Attendance.student_id        == entry.student_id,
                Attendance.timetable_slot_id == slot.id,
                Attendance.date              == payload.date,
            )
        )
        record = existing.scalar_one_or_none()

        if record:
            cutoff = record.marked_at
            if cutoff.tzinfo is None:
                cutoff = cutoff.replace(tzinfo=timezone.utc)
            if (datetime.now(timezone.utc) - cutoff).total_seconds() > 86400:
                continue   # locked after 24 h
            record.status = entry.status
            record.notes  = entry.notes
            updated += 1
        else:
            db.add(Attendance(
                student_id=entry.student_id,
                timetable_slot_id=slot.id,
                subject_id=ca.subject_id,
                faculty_id=faculty.id,
                course_assignment_id=ca.id,
                date=payload.date,
                status=entry.status,
                method=AttendanceMethod.manual,
                notes=entry.notes,
            ))
            created += 1

    await db.flush()
    return {
        "timetable_slot_id": slot.id,
        "date":              payload.date,
        "subject_name":      ca.subject.name,
        "section":           ca.section,
        "start_time":        slot.start_time,
        "end_time":          slot.end_time,
        "total":             len(payload.entries),
        "created":           created,
        "updated":           updated,
    }


async def edit_attendance(
    db: AsyncSession,
    attendance_id: uuid.UUID,
    payload: EditAttendanceRequest,
    faculty_user_id: uuid.UUID,
) -> Attendance:
    result = await db.execute(select(Attendance).where(Attendance.id == attendance_id))
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attendance record not found")

    cutoff = record.marked_at
    if cutoff.tzinfo is None:
        cutoff = cutoff.replace(tzinfo=timezone.utc)
    if (datetime.now(timezone.utc) - cutoff).total_seconds() > 86400:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Attendance is locked after 24 hours")

    record.status = payload.status
    record.notes  = payload.notes
    await db.flush()
    return record


# ── QR Attendance ──────────────────────────────────────────────────────────────

async def generate_qr_session(
    db: AsyncSession,
    payload: QRGenerateRequest,
    faculty_user_id: uuid.UUID,
) -> dict:
    slot    = await _load_slot(db, payload.timetable_slot_id)
    ca      = slot.course_assignment
    faculty = await _get_faculty(db, faculty_user_id)

    if ca.faculty_id != faculty.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not assigned to this class")

    # Deactivate any existing active session for this slot+date
    old_sessions = await db.execute(
        select(QRSession).where(
            QRSession.timetable_slot_id == slot.id,
            QRSession.date              == payload.date,
            QRSession.is_active         == True,
        )
    )
    for old in old_sessions.scalars().all():
        old.is_active = False

    expires_at = datetime.now(timezone.utc) + timedelta(minutes=10)
    token      = qr_utils.create_qr_token(str(slot.id), str(faculty.id), str(payload.date))

    session = QRSession(
        timetable_slot_id=slot.id,
        course_assignment_id=ca.id,
        faculty_id=faculty.id,
        date=payload.date,
        token=token,
        expires_at=expires_at,
        is_active=True,
    )
    db.add(session)
    await db.flush()

    return {
        "session_id":        session.id,
        "qr_image_base64":   qr_utils.generate_qr_image_base64(token),
        "token":             token,
        "expires_at":        expires_at,
        "timetable_slot_id": slot.id,
        "date":              payload.date,
        "subject_name":      ca.subject.name,
        "section":           ca.section,
        "start_time":        slot.start_time,
        "end_time":          slot.end_time,
    }


async def scan_qr_attendance(
    db: AsyncSession,
    payload: QRScanRequest,
    student_user_id: uuid.UUID,
) -> Attendance:
    from jose import JWTError
    try:
        token_data = qr_utils.decode_qr_token(payload.token)
    except JWTError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired QR code")

    slot_id      = uuid.UUID(token_data["course_assignment_id"])  # stored as slot id in token
    session_date = date.fromisoformat(token_data["date"])

    # Verify session is active in DB
    session_result = await db.execute(
        select(QRSession).where(QRSession.token == payload.token, QRSession.is_active == True)
    )
    session = session_result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="QR session is no longer active")

    slot    = await _load_slot(db, session.timetable_slot_id)
    ca      = slot.course_assignment

    stu_result = await db.execute(select(Student).where(Student.user_id == student_user_id))
    student    = stu_result.scalar_one_or_none()
    if not student:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Student profile not found")

    enrolled = await _get_enrolled_students(db, ca)
    if student.id not in {s.id for s in enrolled}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You are not enrolled in this class")

    existing = await db.execute(
        select(Attendance).where(
            Attendance.student_id        == student.id,
            Attendance.timetable_slot_id == slot.id,
            Attendance.date              == session_date,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Attendance already marked for this session")

    record = Attendance(
        student_id=student.id,
        timetable_slot_id=slot.id,
        subject_id=ca.subject_id,
        faculty_id=ca.faculty_id,
        course_assignment_id=ca.id,
        date=session_date,
        status=AttendanceStatus.present,
        method=AttendanceMethod.qr,
    )
    db.add(record)
    await db.flush()
    return record


# ── Face Recognition ───────────────────────────────────────────────────────────

async def register_face(db: AsyncSession, student_user_id: uuid.UUID, image_bytes: bytes) -> None:
    stu_result = await db.execute(select(Student).where(Student.user_id == student_user_id))
    student    = stu_result.scalar_one_or_none()
    if not student:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student profile not found")

    try:
        encoding_bytes = face_utils.encode_face_from_bytes(image_bytes)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))

    existing = await db.execute(select(StudentFaceEncoding).where(StudentFaceEncoding.student_id == student.id))
    rec      = existing.scalar_one_or_none()
    if rec:
        rec.encoding = encoding_bytes
    else:
        db.add(StudentFaceEncoding(student_id=student.id, encoding=encoding_bytes))
    await db.flush()


async def mark_face_attendance(
    db: AsyncSession,
    slot_id: uuid.UUID,
    session_date: date,
    image_bytes: bytes,
    faculty_user_id: uuid.UUID,
) -> dict:
    slot    = await _load_slot(db, slot_id)
    ca      = slot.course_assignment
    faculty = await _get_faculty(db, faculty_user_id)

    if ca.faculty_id != faculty.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not assigned to this class")

    enrolled = await _get_enrolled_students(db, ca)
    if not enrolled:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No students enrolled in this class")

    enc_records = await db.execute(
        select(StudentFaceEncoding).where(
            StudentFaceEncoding.student_id.in_([s.id for s in enrolled])
        )
    )
    encodings = [{"student_id": str(r.student_id), "encoding": r.encoding}
                 for r in enc_records.scalars().all()]

    try:
        matched_ids = face_utils.recognise_faces_in_image(image_bytes, encodings)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))

    matched_set    = set(matched_ids)
    marked_present = []
    not_recognised = []

    for s in enrolled:
        att_status = AttendanceStatus.present if str(s.id) in matched_set else AttendanceStatus.absent
        existing   = await db.execute(
            select(Attendance).where(
                Attendance.student_id        == s.id,
                Attendance.timetable_slot_id == slot.id,
                Attendance.date              == session_date,
            )
        )
        if not existing.scalar_one_or_none():
            db.add(Attendance(
                student_id=s.id,
                timetable_slot_id=slot.id,
                subject_id=ca.subject_id,
                faculty_id=faculty.id,
                course_assignment_id=ca.id,
                date=session_date,
                status=att_status,
                method=AttendanceMethod.face,
            ))
        (marked_present if str(s.id) in matched_set else not_recognised).append(s.roll_number)

    await db.flush()
    return {
        "timetable_slot_id": slot_id,
        "date":              session_date,
        "recognised_count":  len(marked_present),
        "marked_present":    marked_present,
        "not_recognised":    not_recognised,
    }


# ── Reports ────────────────────────────────────────────────────────────────────

async def get_session_summary(
    db: AsyncSession,
    slot_id: uuid.UUID,
    session_date: date,
) -> dict:
    slot = await _load_slot(db, slot_id)
    ca   = slot.course_assignment

    result  = await db.execute(
        select(Attendance).where(
            Attendance.timetable_slot_id == slot_id,
            Attendance.date              == session_date,
        )
    )
    records = list(result.scalars().all())
    counts  = {s: 0 for s in AttendanceStatus}
    for r in records:
        counts[r.status] += 1

    total   = len(records)
    present = counts[AttendanceStatus.present] + counts[AttendanceStatus.late]
    pct     = round(present / total * 100, 2) if total else 0.0

    return {
        "timetable_slot_id": slot_id,
        "subject_name":      ca.subject.name,
        "subject_code":      ca.subject.code,
        "section":           ca.section,
        "date":              session_date,
        "day_of_week":       slot.day_of_week,
        "start_time":        slot.start_time,
        "end_time":          slot.end_time,
        "total_students":    total,
        "present":           counts[AttendanceStatus.present],
        "absent":            counts[AttendanceStatus.absent],
        "late":              counts[AttendanceStatus.late],
        "medical":           counts[AttendanceStatus.medical],
        "percentage":        pct,
        "records":           records,
    }


async def get_student_attendance_report(db: AsyncSession, student_id: uuid.UUID) -> dict:
    stu_result = await db.execute(
        select(Student)
        .where(Student.id == student_id)
        .options(selectinload(Student.user), selectinload(Student.enrolled_subjects))
    )
    student = stu_result.scalar_one_or_none()
    if not student:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found")

    subjects_data     = []
    total_sessions_all = present_all = 0

    for subject in student.enrolled_subjects:
        records_result = await db.execute(
            select(Attendance).where(
                Attendance.student_id == student_id,
                Attendance.subject_id == subject.id,
            )
        )
        records  = list(records_result.scalars().all())
        total    = len(records)
        present  = sum(1 for r in records if r.status in (AttendanceStatus.present, AttendanceStatus.late))
        absent   = sum(1 for r in records if r.status == AttendanceStatus.absent)
        late     = sum(1 for r in records if r.status == AttendanceStatus.late)
        medical  = sum(1 for r in records if r.status == AttendanceStatus.medical)
        pct      = round(present / total * 100, 2) if total else 0.0

        total_sessions_all += total
        present_all        += present

        subjects_data.append({
            "subject_id":     subject.id,
            "subject_name":   subject.name,
            "subject_code":   subject.code,
            "total_sessions": total,
            "present":        present,
            "absent":         absent,
            "late":           late,
            "medical":        medical,
            "percentage":     pct,
            "is_at_risk":     pct < 75.0,
        })

    overall = round(present_all / total_sessions_all * 100, 2) if total_sessions_all else 0.0

    return {
        "student_id":         student_id,
        "roll_number":        student.roll_number,
        "full_name":          student.user.full_name,
        "overall_percentage": overall,
        "subjects":           subjects_data,
    }


async def get_at_risk_students(
    db: AsyncSession,
    slot_id: uuid.UUID,
    threshold: float = 75.0,
) -> list[dict]:
    slot     = await _load_slot(db, slot_id)
    ca       = slot.course_assignment
    enrolled = await _get_enrolled_students(db, ca)

    at_risk = []
    for student in enrolled:
        records_result = await db.execute(
            select(Attendance).where(
                Attendance.student_id == student.id,
                Attendance.subject_id == ca.subject_id,
            )
        )
        records = list(records_result.scalars().all())
        total   = len(records)
        if total == 0:
            continue
        present = sum(1 for r in records if r.status in (AttendanceStatus.present, AttendanceStatus.late))
        pct     = round(present / total * 100, 2)
        if pct < threshold:
            user_result = await db.execute(select(User).where(User.id == student.user_id))
            user        = user_result.scalar_one_or_none()
            at_risk.append({
                "student_id":            student.id,
                "roll_number":           student.roll_number,
                "full_name":             user.full_name if user else "Unknown",
                "subject_id":            ca.subject_id,
                "subject_name":          ca.subject.name,
                "attendance_percentage": pct,
            })

    return at_risk
