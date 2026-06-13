import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, model_validator

from app.models.assignment import AssignmentStatus, SubmissionStatus


# ── Assignment schemas ─────────────────────────────────────────────────────────

class AssignmentCreate(BaseModel):
    title: str = Field(..., min_length=3, max_length=255)
    description: Optional[str] = None
    subject_id: uuid.UUID
    course_assignment_id: Optional[uuid.UUID] = None
    semester_id: uuid.UUID
    deadline: datetime
    max_marks: int = Field(default=100, ge=1, le=1000)
    allow_late_submission: bool = False


class AssignmentUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=3, max_length=255)
    description: Optional[str] = None
    deadline: Optional[datetime] = None
    max_marks: Optional[int] = Field(default=None, ge=1, le=1000)
    allow_late_submission: Optional[bool] = None


class AssignmentResponse(BaseModel):
    id: uuid.UUID
    title: str
    description: Optional[str]
    subject_id: uuid.UUID
    faculty_id: uuid.UUID
    course_assignment_id: Optional[uuid.UUID]
    semester_id: uuid.UUID
    deadline: datetime
    max_marks: int
    file_url: Optional[str]
    file_name: Optional[str]
    status: AssignmentStatus
    allow_late_submission: bool
    created_at: datetime
    updated_at: datetime
    published_at: Optional[datetime]

    model_config = {"from_attributes": True}


class AssignmentListItem(BaseModel):
    """Lightweight listing item, includes student-specific submission status when applicable."""
    id: uuid.UUID
    title: str
    subject_id: uuid.UUID
    deadline: datetime
    max_marks: int
    status: AssignmentStatus
    file_url: Optional[str]
    # Filled for student-facing list views
    submission_status: Optional[SubmissionStatus] = None
    marks: Optional[float] = None
    is_late: Optional[bool] = None

    model_config = {"from_attributes": True}


# ── Submission schemas ─────────────────────────────────────────────────────────

class SubmissionCreate(BaseModel):
    content: Optional[str] = Field(default=None, description="Optional text answer")


class GradeSubmission(BaseModel):
    marks: float = Field(..., ge=0)
    feedback: Optional[str] = None

    @model_validator(mode="after")
    def marks_non_negative(self) -> "GradeSubmission":
        if self.marks < 0:
            raise ValueError("marks must be >= 0")
        return self


class SubmissionResponse(BaseModel):
    id: uuid.UUID
    assignment_id: uuid.UUID
    student_id: uuid.UUID
    file_url: Optional[str]
    file_name: Optional[str]
    content: Optional[str]
    submitted_at: datetime
    is_late: bool
    status: SubmissionStatus
    marks: Optional[float]
    feedback: Optional[str]
    graded_at: Optional[datetime]
    graded_by_id: Optional[uuid.UUID]

    model_config = {"from_attributes": True}


class SubmissionWithStudent(SubmissionResponse):
    """Used by faculty when listing all submissions for an assignment."""
    student_name: Optional[str] = None
    roll_number: Optional[str] = None


# ── Bulk / summary schemas ─────────────────────────────────────────────────────

class AssignmentStats(BaseModel):
    assignment_id: uuid.UUID
    title: str
    total_students: int
    submitted: int
    not_submitted: int
    late_submissions: int
    graded: int
    average_marks: Optional[float]
    max_marks: int
