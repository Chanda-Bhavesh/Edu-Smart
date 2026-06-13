"""
Analytics & Dashboard service.

Pure read-only aggregations — no writes.
Each function returns a typed schema ready to be serialised by the router.
"""
import uuid
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import Integer, case, distinct, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.assignment import Assignment, AssignmentStatus, Submission, SubmissionStatus
from app.models.attendance import Attendance, AttendanceStatus
from app.models.certificate import CertificateRequest, CertificateStatus
from app.models.course_assignment import CourseAssignment
from app.models.department import Department
from app.models.faculty import Faculty
from app.models.faculty_attendance import FacultyAttendance, LeaveRequest, LeaveStatus
from app.models.fee import FeePayment, FeeStatus, FeeStructure, StudentFee
from app.models.notification import Announcement, AnnouncementRead, Notification
from app.models.semester import Semester
from app.models.student import Student
from app.models.subject import Subject, student_enrollments
from app.models.timetable import DayOfWeek, TimetableSlot
from app.models.user import User
from app.schemas.dashboard import (
    AdminDashboard, AttendanceTrend, CertificateStatusItem,
    ChartDataPoint, DeptStats, FacultyDashboard, FeeCollectionTrend,
    FeeStatus_, PendingGradingItem, StudentDashboard,
    SubjectAttendanceSummary, SubjectPerformance, TodayClass, UpcomingAssignment,
)


def _today() -> date:
    return datetime.now(timezone.utc).date()


def _today_dow() -> str:
    """Return lowercase weekday name matching DayOfWeek enum."""
    return _today().strftime("%A").lower()


# ── Student Dashboard ──────────────────────────────────────────────────────────

async def get_student_dashboard(db: AsyncSession, user_id: uuid.UUID) -> StudentDashboard:
    # Resolve student
    s_result = await db.execute(
        select(Student).where(Student.user_id == user_id)
    )
    student = s_result.scalar_one_or_none()
    if not student:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Student profile not found")

    today = _today()

    # ── 1. Subject-wise attendance ──────────────────────────────────────────
    att_q = (
        select(
            Subject.id,
            Subject.name,
            Subject.code,
            func.count(Attendance.id).label("total"),
            func.sum(
                case((Attendance.status == AttendanceStatus.present, 1), else_=0)
            ).label("present"),
        )
        .join(TimetableSlot, Attendance.timetable_slot_id == TimetableSlot.id)
        .join(CourseAssignment, TimetableSlot.course_assignment_id == CourseAssignment.id)
        .join(Subject, CourseAssignment.subject_id == Subject.id)
        .where(Attendance.student_id == student.id)
        .group_by(Subject.id, Subject.name, Subject.code)
    )
    att_rows = (await db.execute(att_q)).all()

    subject_att: list[SubjectAttendanceSummary] = []
    total_classes = 0
    total_present = 0
    at_risk_count = 0

    for row in att_rows:
        t = row.total or 0
        p = int(row.present or 0)
        pct = round((p / t * 100) if t > 0 else 0, 1)
        at_risk = pct < 75.0 and t > 0
        if at_risk:
            at_risk_count += 1
        total_classes += t
        total_present += p
        subject_att.append(SubjectAttendanceSummary(
            subject_id=row.id,
            subject_name=row.name,
            subject_code=row.code,
            total_classes=t,
            present=p,
            absent=t - p,
            percentage=pct,
            is_at_risk=at_risk,
        ))

    overall_pct = round((total_present / total_classes * 100) if total_classes > 0 else 0, 1)

    # ── 2. Upcoming assignments (next 7 days) ───────────────────────────────
    cutoff = datetime.now(timezone.utc) + timedelta(days=7)
    enrolled_sub_q = (
        select(student_enrollments.c.subject_id)
        .where(student_enrollments.c.student_id == student.id)
    )
    asgn_q = (
        select(
            Assignment.id,
            Assignment.title,
            Assignment.deadline,
            Assignment.max_marks,
            Subject.name.label("subject_name"),
            Submission.id.label("submission_id"),
        )
        .join(Subject, Assignment.subject_id == Subject.id)
        .outerjoin(
            Submission,
            (Submission.assignment_id == Assignment.id) & (Submission.student_id == student.id),
        )
        .where(
            Assignment.subject_id.in_(enrolled_sub_q),
            Assignment.status == AssignmentStatus.published,
            Assignment.deadline <= cutoff,
            Assignment.deadline >= datetime.now(timezone.utc),
        )
        .order_by(Assignment.deadline.asc())
    )
    asgn_rows = (await db.execute(asgn_q)).all()

    upcoming: list[UpcomingAssignment] = []
    pending_count = 0
    for row in asgn_rows:
        dl = row.deadline
        if dl.tzinfo is None:
            dl = dl.replace(tzinfo=timezone.utc)
        days_left = max((dl.date() - today).days, 0)
        submitted = row.submission_id is not None
        if not submitted:
            pending_count += 1
        upcoming.append(UpcomingAssignment(
            assignment_id=row.id,
            title=row.title,
            subject_name=row.subject_name,
            deadline=row.deadline,
            max_marks=row.max_marks,
            days_remaining=days_left,
            already_submitted=submitted,
        ))

    # ── 3. Fee summary ──────────────────────────────────────────────────────
    fee_q = await db.execute(
        select(StudentFee)
        .join(FeeStructure)
        .where(
            StudentFee.student_id == student.id,
            StudentFee.status.notin_([FeeStatus.paid, FeeStatus.waived]),
        )
        .order_by(StudentFee.due_date.asc())
        .limit(1)
    )
    active_fee_record = fee_q.scalar_one_or_none()
    active_fee = None
    total_outstanding = 0.0
    if active_fee_record:
        fs = await db.get(FeeStructure, active_fee_record.fee_structure_id)
        active_fee = FeeStatus_(
            student_fee_id=active_fee_record.id,
            academic_year=fs.academic_year if fs else "",
            net_amount=float(active_fee_record.net_amount),
            amount_paid=float(active_fee_record.amount_paid),
            balance=float(active_fee_record.balance),
            status=active_fee_record.status,
            due_date=active_fee_record.due_date,
            is_overdue=active_fee_record.due_date < today,
        )
        total_outstanding = float(active_fee_record.balance)

    # ── 4. Certificate requests ─────────────────────────────────────────────
    cert_q = await db.execute(
        select(CertificateRequest)
        .where(CertificateRequest.student_id == student.id)
        .order_by(CertificateRequest.created_at.desc())
        .limit(5)
    )
    cert_items = [
        CertificateStatusItem(
            request_id=c.id,
            certificate_type=c.certificate_type,
            status=c.status,
            requested_at=c.created_at,
            certificate_number=c.certificate_number,
        )
        for c in cert_q.scalars().all()
    ]

    # ── 5. Notification counts ──────────────────────────────────────────────
    notif_count = (await db.execute(
        select(func.count(Notification.id)).where(
            Notification.user_id == user_id, Notification.is_read == False
        )
    )).scalar() or 0

    read_count = (await db.execute(
        select(func.count(AnnouncementRead.id)).where(
            AnnouncementRead.user_id == user_id
        )
    )).scalar() or 0
    total_ann = (await db.execute(
        select(func.count(Announcement.id)).where(Announcement.is_active == True)
    )).scalar() or 0
    unread_ann = max(total_ann - read_count, 0)

    return StudentDashboard(
        overall_attendance_pct=overall_pct,
        subject_attendance=subject_att,
        at_risk_count=at_risk_count,
        upcoming_deadlines=upcoming,
        total_pending_submissions=pending_count,
        active_fee=active_fee,
        total_outstanding=total_outstanding,
        certificate_requests=cert_items,
        unread_notifications=notif_count,
        unread_announcements=unread_ann,
    )


# ── Faculty Dashboard ──────────────────────────────────────────────────────────

async def get_faculty_dashboard(db: AsyncSession, user_id: uuid.UUID) -> FacultyDashboard:
    f_result = await db.execute(select(Faculty).where(Faculty.user_id == user_id))
    faculty = f_result.scalar_one_or_none()
    if not faculty:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Faculty profile not found")

    today = _today()
    today_dow = _today_dow()

    # ── 1. Today's classes ──────────────────────────────────────────────────
    schedule_q = (
        select(
            TimetableSlot.id,
            TimetableSlot.start_time,
            TimetableSlot.end_time,
            TimetableSlot.room_number,
            Subject.name.label("subject_name"),
            Subject.code.label("subject_code"),
            CourseAssignment.section,
            Semester.number.label("semester_number"),
            func.count(distinct(Attendance.id)).label("att_marked"),
            func.sum(
                case((Attendance.status == AttendanceStatus.present, 1), else_=0)
            ).label("present_count"),
        )
        .join(CourseAssignment, TimetableSlot.course_assignment_id == CourseAssignment.id)
        .join(Subject, CourseAssignment.subject_id == Subject.id)
        .join(Semester, CourseAssignment.semester_id == Semester.id)
        .outerjoin(
            Attendance,
            (Attendance.timetable_slot_id == TimetableSlot.id) & (Attendance.date == today),
        )
        .where(
            CourseAssignment.faculty_id == faculty.id,
            TimetableSlot.day_of_week == today_dow,
            TimetableSlot.is_active == True,
            CourseAssignment.is_active == True,
        )
        .group_by(
            TimetableSlot.id, Subject.name, Subject.code,
            CourseAssignment.section, Semester.number,
        )
        .order_by(TimetableSlot.start_time.asc())
    )
    schedule_rows = (await db.execute(schedule_q)).all()

    today_classes: list[TodayClass] = []
    for row in schedule_rows:
        att_marked = int(row.att_marked or 0)
        today_classes.append(TodayClass(
            slot_id=row.id,
            subject_name=row.subject_name,
            subject_code=row.subject_code,
            start_time=str(row.start_time),
            end_time=str(row.end_time),
            room_number=row.room_number,
            section=row.section,
            semester_number=row.semester_number,
            attendance_marked=att_marked > 0,
            present_count=int(row.present_count or 0),
            total_students=att_marked,
        ))

    # ── 2. Pending grading ──────────────────────────────────────────────────
    grading_q = (
        select(
            Assignment.id,
            Assignment.title,
            Assignment.updated_at,
            Subject.name.label("subject_name"),
            func.count(Submission.id).label("ungraded"),
            func.count(Submission.id).label("total"),
        )
        .join(Subject, Assignment.subject_id == Subject.id)
        .join(Submission, Submission.assignment_id == Assignment.id)
        .where(
            Assignment.faculty_id == faculty.id,
            Assignment.status == AssignmentStatus.closed,
            Submission.status != SubmissionStatus.graded,
        )
        .group_by(Assignment.id, Assignment.title, Assignment.updated_at, Subject.name)
        .having(func.count(Submission.id) > 0)
        .order_by(Assignment.updated_at.asc())
    )
    grading_rows = (await db.execute(grading_q)).all()
    pending_grading = [
        PendingGradingItem(
            assignment_id=row.id,
            title=row.title,
            subject_name=row.subject_name,
            closed_at=row.updated_at,
            ungraded_count=row.ungraded,
            total_submissions=row.total,
        )
        for row in grading_rows
    ]
    total_ungraded = sum(p.ungraded_count for p in pending_grading)

    # ── 3. Subject performance ──────────────────────────────────────────────
    perf_q = (
        select(
            Subject.id,
            Subject.name,
            func.count(distinct(Assignment.id)).label("total_asgn"),
            func.avg(Submission.marks).label("avg_marks"),
            func.max(Assignment.max_marks).label("max_marks"),
            func.max(Submission.marks).label("top_score"),
            func.count(Submission.id).label("sub_count"),
        )
        .join(Assignment, Assignment.subject_id == Subject.id)
        .join(Submission, Submission.assignment_id == Assignment.id)
        .where(
            Assignment.faculty_id == faculty.id,
            Submission.marks.isnot(None),
        )
        .group_by(Subject.id, Subject.name)
    )
    perf_rows = (await db.execute(perf_q)).all()
    subject_perf = [
        SubjectPerformance(
            subject_id=row.id,
            subject_name=row.name,
            total_assignments=row.total_asgn,
            avg_marks=round(float(row.avg_marks), 1) if row.avg_marks else None,
            max_marks=row.max_marks or 100,
            top_score=float(row.top_score) if row.top_score else None,
            submissions_count=row.sub_count,
        )
        for row in perf_rows
    ]

    # ── 4. Pending leave requests ───────────────────────────────────────────
    pending_leaves = (await db.execute(
        select(func.count(LeaveRequest.id)).where(
            LeaveRequest.faculty_id == faculty.id,
            LeaveRequest.status == LeaveStatus.pending,
        )
    )).scalar() or 0

    # ── 5. Unread notifications ─────────────────────────────────────────────
    unread_notifs = (await db.execute(
        select(func.count(Notification.id)).where(
            Notification.user_id == user_id, Notification.is_read == False
        )
    )).scalar() or 0

    return FacultyDashboard(
        today_classes=today_classes,
        total_classes_today=len(today_classes),
        pending_grading=pending_grading,
        total_ungraded=total_ungraded,
        subject_performance=subject_perf,
        pending_leave_requests=pending_leaves,
        unread_notifications=unread_notifs,
    )


# ── Admin Dashboard ────────────────────────────────────────────────────────────

async def get_admin_dashboard(
    db: AsyncSession,
    user_id: uuid.UUID,
    department_id: uuid.UUID | None = None,
) -> AdminDashboard:
    today = _today()

    # ── Counts ──────────────────────────────────────────────────────────────
    student_q = select(func.count(Student.id))
    faculty_q = select(func.count(Faculty.id))
    if department_id:
        student_q = student_q.where(Student.department_id == department_id)
        faculty_q = faculty_q.where(Faculty.department_id == department_id)

    total_students = (await db.execute(student_q)).scalar() or 0
    total_faculty = (await db.execute(faculty_q)).scalar() or 0
    total_depts = (await db.execute(select(func.count(Department.id)))).scalar() or 0

    # ── Today's org-wide attendance rate ─────────────────────────────────────
    att_today_q = select(
        func.count(Attendance.id).label("total"),
        func.sum(
            case((Attendance.status == AttendanceStatus.present, 1), else_=0)
        ).label("present"),
    ).where(Attendance.date == today)
    att_row = (await db.execute(att_today_q)).one()
    t = att_row.total or 0
    p = int(att_row.present or 0)
    today_att_rate = round((p / t * 100) if t > 0 else 0, 1)

    # ── Fee stats ────────────────────────────────────────────────────────────
    fee_q = select(
        func.sum(StudentFee.net_amount).label("expected"),
        func.sum(StudentFee.amount_paid).label("collected"),
    )
    fee_row = (await db.execute(fee_q)).one()
    expected = float(fee_row.expected or 0)
    collected = float(fee_row.collected or 0)
    fee_pct = round((collected / expected * 100) if expected > 0 else 0, 1)

    overdue_count = (await db.execute(
        select(func.count(StudentFee.id)).where(StudentFee.status == FeeStatus.overdue)
    )).scalar() or 0

    # ── Pending certificates ─────────────────────────────────────────────────
    pending_certs = (await db.execute(
        select(func.count(CertificateRequest.id)).where(
            CertificateRequest.status.in_([
                CertificateStatus.pending, CertificateStatus.under_review
            ])
        )
    )).scalar() or 0

    # ── Open assignments ─────────────────────────────────────────────────────
    open_asgn = (await db.execute(
        select(func.count(Assignment.id)).where(
            Assignment.status == AssignmentStatus.published
        )
    )).scalar() or 0

    # ── Dept breakdown ───────────────────────────────────────────────────────
    dept_rows = (await db.execute(
        select(
            Department.id,
            Department.name,
            Department.code,
            func.count(distinct(Student.id)).label("students"),
            func.count(distinct(Faculty.id)).label("faculty_count"),
        )
        .outerjoin(Student, Student.department_id == Department.id)
        .outerjoin(Faculty, Faculty.department_id == Department.id)
        .group_by(Department.id, Department.name, Department.code)
        .order_by(Department.name)
    )).all()

    dept_stats: list[DeptStats] = []
    for row in dept_rows:
        # Per-dept today attendance
        dept_att_q = (
            select(
                func.count(Attendance.id).label("total"),
                func.sum(
                    case((Attendance.status == AttendanceStatus.present, 1), else_=0)
                ).label("present"),
            )
            .join(TimetableSlot, Attendance.timetable_slot_id == TimetableSlot.id)
            .join(CourseAssignment, TimetableSlot.course_assignment_id == CourseAssignment.id)
            .join(Semester, CourseAssignment.semester_id == Semester.id)
            .where(
                Semester.department_id == row.id,
                Attendance.date == today,
            )
        )
        da = (await db.execute(dept_att_q)).one()
        dept_att = round((int(da.present or 0) / da.total * 100) if da.total else 0, 1)

        pending_fee_dept = (await db.execute(
            select(func.count(StudentFee.id))
            .join(Student, StudentFee.student_id == Student.id)
            .where(
                Student.department_id == row.id,
                StudentFee.status.in_([FeeStatus.pending, FeeStatus.overdue]),
            )
        )).scalar() or 0

        dept_stats.append(DeptStats(
            department_id=row.id,
            department_name=row.name,
            department_code=row.code,
            total_students=row.students,
            total_faculty=row.faculty_count,
            today_attendance_rate=dept_att,
            pending_fee_count=pending_fee_dept,
        ))

    # ── System unread (for admin) ─────────────────────────────────────────────
    sys_unread = (await db.execute(
        select(func.count(Notification.id)).where(
            Notification.user_id == user_id, Notification.is_read == False
        )
    )).scalar() or 0

    return AdminDashboard(
        total_students=total_students,
        total_faculty=total_faculty,
        total_departments=total_depts,
        today_attendance_rate=today_att_rate,
        total_fee_expected=expected,
        total_fee_collected=collected,
        fee_collection_pct=fee_pct,
        overdue_fee_count=overdue_count,
        pending_certificate_requests=pending_certs,
        open_assignments=open_asgn,
        dept_stats=dept_stats,
        total_unread_system_notifications=sys_unread,
    )


# ── Trend / Chart data ─────────────────────────────────────────────────────────

async def get_attendance_trend(
    db: AsyncSession,
    weeks: int = 8,
    department_id: uuid.UUID | None = None,
) -> AttendanceTrend:
    """Return weekly attendance rate for the past N weeks."""
    since = _today() - timedelta(weeks=weeks)

    week_col = func.date_trunc("week", Attendance.date).label("week")
    q = (
        select(
            week_col,
            func.count(Attendance.id).label("total"),
            func.sum(
                case((Attendance.status == AttendanceStatus.present, 1), else_=0)
            ).label("present"),
        )
        .where(Attendance.date >= since)
        .group_by(week_col)
        .order_by(week_col)
    )
    if department_id:
        q = (
            q.join(TimetableSlot, Attendance.timetable_slot_id == TimetableSlot.id)
            .join(CourseAssignment, TimetableSlot.course_assignment_id == CourseAssignment.id)
            .join(Semester, CourseAssignment.semester_id == Semester.id)
            .where(Semester.department_id == department_id)
        )

    rows = (await db.execute(q)).all()
    points: list[ChartDataPoint] = []
    total_p = total_t = 0
    for row in rows:
        t = row.total or 0
        p = int(row.present or 0)
        rate = round((p / t * 100) if t > 0 else 0, 1)
        total_p += p
        total_t += t
        label = row.week.strftime("%d %b") if hasattr(row.week, "strftime") else str(row.week)
        points.append(ChartDataPoint(label=label, value=rate))

    overall = round((total_p / total_t * 100) if total_t > 0 else 0, 1)
    return AttendanceTrend(data=points, overall_avg=overall)


async def get_fee_collection_trend(
    db: AsyncSession,
    academic_year: str | None = None,
) -> FeeCollectionTrend:
    """Return monthly fee collection totals for chart display."""
    month_col = func.date_trunc("month", FeePayment.payment_date).label("month")
    q = (
        select(
            month_col,
            func.sum(FeePayment.amount).label("collected"),
        )
        .group_by(month_col)
        .order_by(month_col)
    )
    if academic_year:
        q = (
            q.join(StudentFee, FeePayment.student_fee_id == StudentFee.id)
            .join(FeeStructure, StudentFee.fee_structure_id == FeeStructure.id)
            .where(FeeStructure.academic_year == academic_year)
        )

    rows = (await db.execute(q)).all()
    points: list[ChartDataPoint] = []
    total_collected = 0.0
    for row in rows:
        amt = float(row.collected or 0)
        total_collected += amt
        label = row.month.strftime("%b %Y") if hasattr(row.month, "strftime") else str(row.month)
        points.append(ChartDataPoint(label=label, value=amt))

    # Total expected (all time or filtered by year)
    exp_q = select(func.sum(StudentFee.net_amount))
    if academic_year:
        exp_q = (
            exp_q.join(FeeStructure, StudentFee.fee_structure_id == FeeStructure.id)
            .where(FeeStructure.academic_year == academic_year)
        )
    total_expected = float((await db.execute(exp_q)).scalar() or 0)

    return FeeCollectionTrend(
        data=points,
        total_collected=total_collected,
        total_expected=total_expected,
    )
