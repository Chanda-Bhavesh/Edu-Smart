"""
Report generation service.

Produces downloadable CSV and PDF files for:
  - Student attendance (date-range filtered)
  - Assignment marks (per assignment, for faculty)
  - Fee collection (admin, per fee structure)
  - Fee statement (student, all-time)
"""
import csv
import io
import uuid
from datetime import date, datetime, timezone
from typing import Optional

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.assignment import Assignment, Submission
from app.models.attendance import Attendance, AttendanceStatus
from app.models.course_assignment import CourseAssignment
from app.models.faculty import Faculty
from app.models.fee import FeePayment, FeeStatus, FeeStructure, StudentFee
from app.models.semester import Semester
from app.models.student import Student
from app.models.subject import Subject
from app.models.timetable import TimetableSlot


def _now() -> datetime:
    return datetime.now(timezone.utc)


# ── CSV helpers ────────────────────────────────────────────────────────────────

def _csv_bytes(headers: list[str], rows: list[list]) -> bytes:
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(headers)
    w.writerows(rows)
    return buf.getvalue().encode("utf-8-sig")  # BOM so Excel opens correctly


# ── Student Attendance CSV ─────────────────────────────────────────────────────

async def student_attendance_csv(
    db: AsyncSession,
    student_id: uuid.UUID,
    start_date: date,
    end_date: date,
    subject_id: Optional[uuid.UUID] = None,
) -> bytes:
    q = (
        select(
            Attendance.date,
            Subject.name.label("subject"),
            Subject.code,
            TimetableSlot.start_time,
            TimetableSlot.end_time,
            Attendance.status,
            Attendance.marked_at,
        )
        .join(TimetableSlot, Attendance.timetable_slot_id == TimetableSlot.id)
        .join(CourseAssignment, TimetableSlot.course_assignment_id == CourseAssignment.id)
        .join(Subject, CourseAssignment.subject_id == Subject.id)
        .where(
            Attendance.student_id == student_id,
            Attendance.date >= start_date,
            Attendance.date <= end_date,
        )
        .order_by(Attendance.date.asc(), TimetableSlot.start_time.asc())
    )
    if subject_id:
        q = q.where(Subject.id == subject_id)

    rows_db = (await db.execute(q)).all()

    headers = ["Date", "Subject", "Code", "Start Time", "End Time", "Status", "Marked At"]
    rows = [
        [
            str(r.date),
            r.subject,
            r.code,
            str(r.start_time),
            str(r.end_time),
            r.status.value,
            str(r.marked_at) if r.marked_at else "",
        ]
        for r in rows_db
    ]
    return _csv_bytes(headers, rows)


# ── Student Attendance PDF ─────────────────────────────────────────────────────

async def student_attendance_pdf(
    db: AsyncSession,
    student_id: uuid.UUID,
    start_date: date,
    end_date: date,
) -> bytes:
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import cm
        from reportlab.lib.enums import TA_CENTER
        from reportlab.platypus import (
            HRFlowable, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle,
        )
    except ImportError:
        raise HTTPException(status_code=500, detail="reportlab not installed")

    # Load student
    s_result = await db.execute(
        select(Student).where(Student.id == student_id)
        .options(selectinload(Student.user), selectinload(Student.department))
    )
    student = s_result.scalar_one_or_none()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    # Load attendance records
    q = (
        select(
            Attendance.date,
            Subject.name.label("subject"),
            TimetableSlot.start_time,
            Attendance.status,
        )
        .join(TimetableSlot, Attendance.timetable_slot_id == TimetableSlot.id)
        .join(CourseAssignment, TimetableSlot.course_assignment_id == CourseAssignment.id)
        .join(Subject, CourseAssignment.subject_id == Subject.id)
        .where(
            Attendance.student_id == student_id,
            Attendance.date >= start_date,
            Attendance.date <= end_date,
        )
        .order_by(Attendance.date.asc(), TimetableSlot.start_time.asc())
    )
    att_rows = (await db.execute(q)).all()

    # Stats per subject
    subject_stats: dict[str, dict] = {}
    for r in att_rows:
        if r.subject not in subject_stats:
            subject_stats[r.subject] = {"total": 0, "present": 0}
        subject_stats[r.subject]["total"] += 1
        if r.status == AttendanceStatus.present:
            subject_stats[r.subject]["present"] += 1

    buf = io.BytesIO()
    styles = getSampleStyleSheet()
    doc = SimpleDocTemplate(buf, pagesize=A4,
                             rightMargin=2*cm, leftMargin=2*cm,
                             topMargin=2*cm, bottomMargin=2*cm)
    story = []

    title_style = ParagraphStyle("t", parent=styles["Heading1"],
                                  fontSize=16, textColor=colors.HexColor("#1a237e"),
                                  alignment=TA_CENTER)
    story.append(Paragraph("Attendance Report", title_style))
    story.append(Spacer(1, 0.3 * cm))

    student_name = f"{student.user.first_name} {student.user.last_name}" if student.user else "N/A"
    info_data = [
        ["Student", student_name, "Roll No", student.roll_number],
        ["Department", student.department.name if student.department else "N/A",
         "Period", f"{start_date} to {end_date}"],
    ]
    info_table = Table(info_data, colWidths=[3*cm, 6*cm, 3*cm, 5*cm])
    info_table.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("TEXTCOLOR", (0, 0), (0, -1), colors.grey),
        ("TEXTCOLOR", (2, 0), (2, -1), colors.grey),
        ("FONTNAME", (1, 0), (1, -1), "Helvetica-Bold"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(info_table)
    story.append(Spacer(1, 0.4 * cm))

    # Summary table
    story.append(Paragraph("Subject-wise Summary", styles["Heading3"]))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.lightgrey, spaceAfter=6))
    sum_headers = [["Subject", "Total Classes", "Present", "Absent", "Percentage"]]
    sum_rows = []
    for subj, stats in subject_stats.items():
        t = stats["total"]
        p = stats["present"]
        pct = f"{round(p/t*100, 1)}%" if t > 0 else "0%"
        sum_rows.append([subj, t, p, t - p, pct])
    sum_table = Table(sum_headers + sum_rows,
                       colWidths=[6*cm, 3*cm, 3*cm, 3*cm, 3*cm])
    sum_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a237e")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ALIGN", (1, 0), (-1, -1), "CENTER"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.whitesmoke, colors.white]),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.lightgrey),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(sum_table)
    story.append(Spacer(1, 0.5 * cm))

    # Detailed log
    story.append(Paragraph("Detailed Log", styles["Heading3"]))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.lightgrey, spaceAfter=6))
    det_headers = [["Date", "Subject", "Time", "Status"]]
    det_rows = [
        [str(r.date), r.subject, str(r.start_time), r.status.value.capitalize()]
        for r in att_rows
    ]
    det_table = Table(det_headers + det_rows,
                       colWidths=[3*cm, 6*cm, 3*cm, 5*cm])
    det_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a237e")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.whitesmoke, colors.white]),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.lightgrey),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(det_table)

    doc.build(story)
    return buf.getvalue()


# ── Assignment Marks CSV ───────────────────────────────────────────────────────

async def assignment_marks_csv(
    db: AsyncSession,
    assignment_id: uuid.UUID,
    faculty_user_id: uuid.UUID,
) -> bytes:
    # Verify ownership
    f_result = await db.execute(select(Faculty).where(Faculty.user_id == faculty_user_id))
    faculty = f_result.scalar_one_or_none()
    if not faculty:
        raise HTTPException(status_code=403, detail="Faculty profile not found")

    asgn = await db.get(Assignment, assignment_id)
    if not asgn:
        raise HTTPException(status_code=404, detail="Assignment not found")
    if asgn.faculty_id != faculty.id:
        raise HTTPException(status_code=403, detail="Not your assignment")

    q = (
        select(
            Student.roll_number,
            Student.section,
            Submission.submitted_at,
            Submission.is_late,
            Submission.marks,
            Submission.feedback,
            Submission.status,
        )
        .join(Student, Submission.student_id == Student.id)
        .outerjoin(Student.user)
        .where(Submission.assignment_id == assignment_id)
        .order_by(Student.roll_number)
    )
    rows_db = (await db.execute(q)).all()

    headers = ["Roll Number", "Section", "Submitted At", "Is Late",
               "Marks", f"Marks / {asgn.max_marks}", "Feedback", "Status"]
    rows = [
        [
            r.roll_number,
            r.section,
            str(r.submitted_at) if r.submitted_at else "Not Submitted",
            "Yes" if r.is_late else "No",
            r.marks if r.marks is not None else "",
            f"{r.marks}/{asgn.max_marks}" if r.marks is not None else "",
            r.feedback or "",
            r.status.value if r.status else "",
        ]
        for r in rows_db
    ]
    return _csv_bytes(headers, rows)


# ── Fee Collection CSV (Admin) ─────────────────────────────────────────────────

async def fee_collection_csv(
    db: AsyncSession,
    fee_structure_id: uuid.UUID,
) -> bytes:
    q = (
        select(
            Student.roll_number,
            Student.section,
            StudentFee.total_amount,
            StudentFee.discount_amount,
            StudentFee.fine_amount,
            StudentFee.net_amount,
            StudentFee.amount_paid,
            StudentFee.balance,
            StudentFee.status,
            StudentFee.due_date,
        )
        .join(Student, StudentFee.student_id == Student.id)
        .where(StudentFee.fee_structure_id == fee_structure_id)
        .order_by(Student.roll_number)
    )
    rows_db = (await db.execute(q)).all()

    headers = [
        "Roll Number", "Section", "Total Fee", "Discount",
        "Fine", "Net Payable", "Amount Paid", "Balance", "Status", "Due Date",
    ]
    rows = [
        [
            r.roll_number, r.section,
            float(r.total_amount), float(r.discount_amount),
            float(r.fine_amount), float(r.net_amount),
            float(r.amount_paid), float(r.balance),
            r.status.value, str(r.due_date),
        ]
        for r in rows_db
    ]
    return _csv_bytes(headers, rows)


# ── Fee Statement PDF (Student) ────────────────────────────────────────────────

async def fee_statement_pdf(
    db: AsyncSession,
    student_id: uuid.UUID,
) -> bytes:
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import cm
        from reportlab.lib.enums import TA_CENTER
        from reportlab.platypus import (
            HRFlowable, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle,
        )
    except ImportError:
        raise HTTPException(status_code=500, detail="reportlab not installed")

    s_result = await db.execute(
        select(Student).where(Student.id == student_id)
        .options(
            selectinload(Student.user),
            selectinload(Student.department),
        )
    )
    student = s_result.scalar_one_or_none()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    fees_result = await db.execute(
        select(StudentFee)
        .where(StudentFee.student_id == student_id)
        .options(
            selectinload(StudentFee.fee_structure),
            selectinload(StudentFee.payments),
        )
        .order_by(StudentFee.due_date.desc())
    )
    fees = fees_result.scalars().all()

    buf = io.BytesIO()
    styles = getSampleStyleSheet()
    doc = SimpleDocTemplate(buf, pagesize=A4,
                             rightMargin=2*cm, leftMargin=2*cm,
                             topMargin=2*cm, bottomMargin=2*cm)
    story = []
    title_style = ParagraphStyle("t", parent=styles["Heading1"],
                                  fontSize=16, textColor=colors.HexColor("#1a237e"),
                                  alignment=TA_CENTER)
    story.append(Paragraph("Fee Statement", title_style))
    story.append(Spacer(1, 0.3 * cm))

    student_name = f"{student.user.first_name} {student.user.last_name}" if student.user else "N/A"
    info = [
        ["Student", student_name, "Roll No", student.roll_number],
        ["Department", student.department.name if student.department else "N/A",
         "Generated On", str(_now().date())],
    ]
    info_table = Table(info, colWidths=[3*cm, 6*cm, 3*cm, 5*cm])
    info_table.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("TEXTCOLOR", (0, 0), (0, -1), colors.grey),
        ("TEXTCOLOR", (2, 0), (2, -1), colors.grey),
        ("FONTNAME", (1, 0), (1, -1), "Helvetica-Bold"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(info_table)
    story.append(Spacer(1, 0.5 * cm))

    for fee in fees:
        fs = fee.fee_structure
        year = fs.academic_year if fs else "N/A"
        story.append(Paragraph(f"Academic Year: {year}", styles["Heading3"]))
        story.append(HRFlowable(width="100%", thickness=0.5, color=colors.lightgrey, spaceAfter=6))

        fee_summary = [
            ["Net Payable", f"₹ {float(fee.net_amount):,.2f}"],
            ["Amount Paid", f"₹ {float(fee.amount_paid):,.2f}"],
            ["Balance", f"₹ {float(fee.balance):,.2f}"],
            ["Status", fee.status.value.upper()],
            ["Due Date", str(fee.due_date)],
        ]
        fs_table = Table(fee_summary, colWidths=[6*cm, 11*cm])
        fs_table.setStyle(TableStyle([
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("TEXTCOLOR", (0, 0), (0, -1), colors.grey),
            ("FONTNAME", (1, 2), (1, 2),
             "Helvetica-Bold" if float(fee.balance) > 0 else "Helvetica"),
            ("TEXTCOLOR", (1, 2), (1, 2),
             colors.red if float(fee.balance) > 0 else colors.green),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(fs_table)
        story.append(Spacer(1, 0.3 * cm))

        if fee.payments:
            pay_headers = [["Receipt No", "Date", "Mode", "Amount"]]
            pay_rows = [
                [p.receipt_number, str(p.payment_date),
                 p.payment_mode.value, f"₹ {float(p.amount):,.2f}"]
                for p in fee.payments
            ]
            pay_table = Table(pay_headers + pay_rows,
                               colWidths=[5*cm, 3*cm, 4*cm, 5*cm])
            pay_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e8eaf6")),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("GRID", (0, 0), (-1, -1), 0.3, colors.lightgrey),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]))
            story.append(pay_table)

        story.append(Spacer(1, 0.6 * cm))

    doc.build(story)
    return buf.getvalue()
