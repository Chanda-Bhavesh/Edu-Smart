import uuid
from datetime import time, datetime
from pydantic import BaseModel, Field, model_validator
from app.models.timetable import DayOfWeek


class TimetableSlotCreate(BaseModel):
    course_assignment_id: uuid.UUID
    day_of_week:  DayOfWeek
    start_time:   time
    end_time:     time
    room_number:  str | None = Field(None, max_length=50)

    @model_validator(mode="after")
    def end_after_start(self) -> "TimetableSlotCreate":
        if self.end_time <= self.start_time:
            raise ValueError("end_time must be after start_time")
        return self


class TimetableSlotUpdate(BaseModel):
    start_time:  time        | None = None
    end_time:    time        | None = None
    room_number: str         | None = Field(None, max_length=50)
    is_active:   bool        | None = None


# ── Nested helpers ─────────────────────────────────────────────────────────────

class SubjectBrief(BaseModel):
    id:   uuid.UUID
    name: str
    code: str
    model_config = {"from_attributes": True}


class FacultyBrief(BaseModel):
    id:          uuid.UUID
    employee_id: str
    full_name:   str          # flattened from faculty.user.full_name
    model_config = {"from_attributes": True}


class TimetableSlotResponse(BaseModel):
    id:                   uuid.UUID
    course_assignment_id: uuid.UUID
    day_of_week:          DayOfWeek
    start_time:           time
    end_time:             time
    room_number:          str | None
    is_active:            bool
    subject:              SubjectBrief
    faculty_name:         str          # resolved in service layer
    section:              str
    semester_number:      int
    model_config = {"from_attributes": True}


# ── Schedule views ─────────────────────────────────────────────────────────────

class DaySchedule(BaseModel):
    """All slots for one day, sorted by start_time."""
    day_of_week: DayOfWeek
    slots:       list[TimetableSlotResponse]


class WeeklyTimetable(BaseModel):
    """Full week schedule for a section or faculty member."""
    department_name: str
    semester_number: int
    section:         str
    academic_year:   str
    schedule:        list[DaySchedule]   # 6 days, each with its slots


class FacultyDaySchedule(BaseModel):
    """Today's slots for a faculty member — used on the faculty dashboard."""
    date:        str                     # "2025-06-05"
    day_of_week: DayOfWeek
    slots:       list[TimetableSlotResponse]
