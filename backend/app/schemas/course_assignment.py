import uuid
from datetime import datetime
from pydantic import BaseModel, Field


class CourseAssignmentCreate(BaseModel):
    faculty_id: uuid.UUID
    subject_id: uuid.UUID
    semester_id: uuid.UUID
    section: str = Field(..., min_length=1, max_length=10)
    academic_year: str = Field(..., pattern=r"^\d{4}-\d{4}$")  # e.g. 2024-2025


class CourseAssignmentUpdate(BaseModel):
    is_active: bool


# Nested detail objects for rich responses
class FacultyBrief(BaseModel):
    id: uuid.UUID
    employee_id: str
    full_name: str

    model_config = {"from_attributes": True}


class SubjectBrief(BaseModel):
    id: uuid.UUID
    name: str
    code: str
    credits: int

    model_config = {"from_attributes": True}


class SemesterBrief(BaseModel):
    id: uuid.UUID
    number: int
    academic_year: str

    model_config = {"from_attributes": True}


class CourseAssignmentResponse(BaseModel):
    id: uuid.UUID
    section: str
    academic_year: str
    is_active: bool
    created_at: datetime
    faculty: "FacultyBriefNested"
    subject: SubjectBrief
    semester: SemesterBrief

    model_config = {"from_attributes": True}


class FacultyBriefNested(BaseModel):
    id: uuid.UUID
    employee_id: str
    user: "UserNameOnly"

    model_config = {"from_attributes": True}


class UserNameOnly(BaseModel):
    full_name: str
    email: str

    model_config = {"from_attributes": True}


# Rebuild forward refs
CourseAssignmentResponse.model_rebuild()
FacultyBriefNested.model_rebuild()


class StudentInClass(BaseModel):
    """A student who belongs to this course assignment's section + subject."""
    id: uuid.UUID
    roll_number: str
    section: str
    full_name: str
    email: str

    model_config = {"from_attributes": True}


class CourseAssignmentWithStudents(BaseModel):
    assignment: CourseAssignmentResponse
    students: list[StudentInClass]
    total_students: int
