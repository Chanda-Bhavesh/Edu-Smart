import uuid
from datetime import date, datetime
from pydantic import BaseModel, Field, model_validator
from app.models.faculty_attendance import FacultyAttendanceStatus, LeaveType, LeaveStatus


# ── Check-In / Check-Out ──────────────────────────────────────────────────────

class CheckInResponse(BaseModel):
    id: uuid.UUID
    date: date
    check_in_time: datetime
    status: FacultyAttendanceStatus

    model_config = {"from_attributes": True}


class CheckOutResponse(BaseModel):
    id: uuid.UUID
    date: date
    check_in_time: datetime
    check_out_time: datetime
    working_hours: float
    status: FacultyAttendanceStatus

    model_config = {"from_attributes": True}


# ── Leave Requests ────────────────────────────────────────────────────────────

class LeaveRequestCreate(BaseModel):
    leave_type: LeaveType
    start_date: date
    end_date: date
    reason: str = Field(..., min_length=10, max_length=1000)

    @model_validator(mode="after")
    def end_after_start(self) -> "LeaveRequestCreate":
        if self.end_date < self.start_date:
            raise ValueError("end_date must be on or after start_date")
        return self


class LeaveReviewRequest(BaseModel):
    status: LeaveStatus     # approved or rejected
    review_comment: str | None = None


class LeaveRequestResponse(BaseModel):
    id: uuid.UUID
    faculty_id: uuid.UUID
    leave_type: LeaveType
    start_date: date
    end_date: date
    reason: str
    status: LeaveStatus
    review_comment: str | None
    applied_at: datetime
    reviewed_at: datetime | None

    model_config = {"from_attributes": True}


# ── Faculty Attendance Record ─────────────────────────────────────────────────

class FacultyAttendanceResponse(BaseModel):
    id: uuid.UUID
    faculty_id: uuid.UUID
    date: date
    status: FacultyAttendanceStatus
    check_in_time: datetime | None
    check_out_time: datetime | None
    working_hours: float | None
    notes: str | None

    model_config = {"from_attributes": True}


# ── Monthly Report ────────────────────────────────────────────────────────────

class FacultyMonthlyReport(BaseModel):
    faculty_id: uuid.UUID
    month: int
    year: int
    total_working_days: int
    present_days: int
    absent_days: int
    leave_days: int
    half_days: int
    total_working_hours: float
    records: list[FacultyAttendanceResponse]
