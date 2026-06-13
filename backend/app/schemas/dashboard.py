import uuid
from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel

from app.models.assignment import AssignmentStatus
from app.models.certificate import CertificateStatus, CertificateType
from app.models.fee import FeeStatus


# ── Shared small types ─────────────────────────────────────────────────────────

class ChartDataPoint(BaseModel):
    label: str        # x-axis label (week, month, date)
    value: float      # y-axis value


class SubjectAttendanceSummary(BaseModel):
    subject_id: uuid.UUID
    subject_name: str
    subject_code: str
    total_classes: int
    present: int
    absent: int
    percentage: float
    is_at_risk: bool  # True if below 75%


class UpcomingAssignment(BaseModel):
    assignment_id: uuid.UUID
    title: str
    subject_name: str
    deadline: datetime
    max_marks: int
    days_remaining: int
    already_submitted: bool


class CertificateStatusItem(BaseModel):
    request_id: uuid.UUID
    certificate_type: CertificateType
    status: CertificateStatus
    requested_at: datetime
    certificate_number: Optional[str]


class FeeStatus_(BaseModel):
    student_fee_id: uuid.UUID
    academic_year: str
    net_amount: float
    amount_paid: float
    balance: float
    status: FeeStatus
    due_date: date
    is_overdue: bool


# ── Student Dashboard ──────────────────────────────────────────────────────────

class StudentDashboard(BaseModel):
    # Attendance
    overall_attendance_pct: float
    subject_attendance: list[SubjectAttendanceSummary]
    at_risk_count: int                    # subjects below 75%

    # Assignments
    upcoming_deadlines: list[UpcomingAssignment]   # next 7 days
    total_pending_submissions: int

    # Fees
    active_fee: Optional[FeeStatus_]      # current semester's fee record
    total_outstanding: float

    # Certificates
    certificate_requests: list[CertificateStatusItem]

    # Notifications
    unread_notifications: int
    unread_announcements: int


# ── Faculty Dashboard ──────────────────────────────────────────────────────────

class TodayClass(BaseModel):
    slot_id: uuid.UUID
    subject_name: str
    subject_code: str
    start_time: str
    end_time: str
    room_number: Optional[str]
    section: str
    semester_number: int
    attendance_marked: bool
    present_count: int
    total_students: int


class PendingGradingItem(BaseModel):
    assignment_id: uuid.UUID
    title: str
    subject_name: str
    closed_at: Optional[datetime]
    ungraded_count: int
    total_submissions: int


class SubjectPerformance(BaseModel):
    subject_id: uuid.UUID
    subject_name: str
    total_assignments: int
    avg_marks: Optional[float]
    max_marks: int
    top_score: Optional[float]
    submissions_count: int


class FacultyDashboard(BaseModel):
    # Schedule
    today_classes: list[TodayClass]
    total_classes_today: int

    # Grading
    pending_grading: list[PendingGradingItem]
    total_ungraded: int

    # Performance
    subject_performance: list[SubjectPerformance]

    # Leave
    pending_leave_requests: int

    # Notifications
    unread_notifications: int


# ── Admin Dashboard ────────────────────────────────────────────────────────────

class DeptStats(BaseModel):
    department_id: uuid.UUID
    department_name: str
    department_code: str
    total_students: int
    total_faculty: int
    today_attendance_rate: Optional[float]
    pending_fee_count: int


class AdminDashboard(BaseModel):
    # Headcounts
    total_students: int
    total_faculty: int
    total_departments: int

    # Attendance
    today_attendance_rate: float          # org-wide %

    # Fees
    total_fee_expected: float
    total_fee_collected: float
    fee_collection_pct: float
    overdue_fee_count: int                # students with overdue fees

    # Certificates
    pending_certificate_requests: int

    # Assignments
    open_assignments: int                 # published + not yet closed

    # Department breakdown
    dept_stats: list[DeptStats]

    # Notifications
    total_unread_system_notifications: int


# ── Trend / Chart schemas ──────────────────────────────────────────────────────

class AttendanceTrend(BaseModel):
    """Weekly attendance rate for the past N weeks — feeds a line chart."""
    data: list[ChartDataPoint]
    overall_avg: float


class FeeCollectionTrend(BaseModel):
    """Monthly fee collection amounts — feeds a bar chart."""
    data: list[ChartDataPoint]
    total_collected: float
    total_expected: float


class SubjectAttendanceTrend(BaseModel):
    """Per-subject attendance % for a class — feeds a bar chart for faculty."""
    subject_name: str
    data: list[ChartDataPoint]   # each point = one week
