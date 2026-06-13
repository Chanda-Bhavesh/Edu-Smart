import uuid
from datetime import date, datetime, time
from pydantic import BaseModel, Field
from app.models.attendance import AttendanceStatus, AttendanceMethod
from app.models.timetable import DayOfWeek


# ── Manual Attendance ──────────────────────────────────────────────────────────

class AttendanceEntry(BaseModel):
    """One student's status inside a bulk-mark request."""
    student_id: uuid.UUID
    status:     AttendanceStatus
    notes:      str | None = None


class ManualAttendanceRequest(BaseModel):
    timetable_slot_id: uuid.UUID   # which period
    date:              date        # which date
    entries:           list[AttendanceEntry] = Field(..., min_length=1)


class EditAttendanceRequest(BaseModel):
    status: AttendanceStatus
    notes:  str | None = None


# ── QR Attendance ──────────────────────────────────────────────────────────────

class QRGenerateRequest(BaseModel):
    timetable_slot_id: uuid.UUID
    date:              date


class QRGenerateResponse(BaseModel):
    session_id:          uuid.UUID
    qr_image_base64:     str
    token:               str
    expires_at:          datetime
    timetable_slot_id:   uuid.UUID
    date:                date
    subject_name:        str
    section:             str
    start_time:          time
    end_time:            time


class QRScanRequest(BaseModel):
    token: str


# ── Face Recognition ───────────────────────────────────────────────────────────

class FaceAttendanceResponse(BaseModel):
    timetable_slot_id:  uuid.UUID
    date:               date
    recognised_count:   int
    marked_present:     list[str]   # roll numbers
    not_recognised:     list[str]   # roll numbers


# ── Responses ──────────────────────────────────────────────────────────────────

class AttendanceResponse(BaseModel):
    id:                   uuid.UUID
    student_id:           uuid.UUID
    timetable_slot_id:    uuid.UUID
    subject_id:           uuid.UUID
    course_assignment_id: uuid.UUID | None
    date:                 date
    status:               AttendanceStatus
    method:               AttendanceMethod
    notes:                str | None
    marked_at:            datetime
    model_config = {"from_attributes": True}


class BulkAttendanceResult(BaseModel):
    timetable_slot_id: uuid.UUID
    date:              date
    subject_name:      str
    section:           str
    start_time:        time
    end_time:          time
    total:             int
    created:           int
    updated:           int


# ── Reports ────────────────────────────────────────────────────────────────────

class SessionAttendanceSummary(BaseModel):
    """Summary for one class session (one timetable slot on one date)."""
    timetable_slot_id: uuid.UUID
    subject_name:      str
    subject_code:      str
    section:           str
    date:              date
    day_of_week:       DayOfWeek
    start_time:        time
    end_time:          time
    total_students:    int
    present:           int
    absent:            int
    late:              int
    medical:           int
    percentage:        float
    records:           list[AttendanceResponse]


class StudentSubjectAttendance(BaseModel):
    """Student's attendance stats for one subject (all sessions combined)."""
    subject_id:     uuid.UUID
    subject_name:   str
    subject_code:   str
    total_sessions: int
    present:        int
    absent:         int
    late:           int
    medical:        int
    percentage:     float
    is_at_risk:     bool      # True if percentage < 75


class StudentAttendanceReport(BaseModel):
    student_id:          uuid.UUID
    roll_number:         str
    full_name:           str
    overall_percentage:  float
    subjects:            list[StudentSubjectAttendance]


class AtRiskStudent(BaseModel):
    student_id:            uuid.UUID
    roll_number:           str
    full_name:             str
    subject_id:            uuid.UUID
    subject_name:          str
    attendance_percentage: float
