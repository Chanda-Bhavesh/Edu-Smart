import uuid
from datetime import datetime, date
from pydantic import BaseModel, Field


# ── Department ────────────────────────────────────────────────────────────────

class DepartmentCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    code: str = Field(..., min_length=2, max_length=20)
    description: str | None = None


class DepartmentUpdate(BaseModel):
    name: str | None = Field(None, min_length=2, max_length=255)
    code: str | None = Field(None, min_length=2, max_length=20)
    description: str | None = None
    head_faculty_id: uuid.UUID | None = None


class DepartmentResponse(BaseModel):
    id: uuid.UUID
    name: str
    code: str
    description: str | None
    head_faculty_id: uuid.UUID | None
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Semester ──────────────────────────────────────────────────────────────────

class SemesterCreate(BaseModel):
    number: int = Field(..., ge=1, le=12)
    academic_year: str = Field(..., pattern=r"^\d{4}-\d{4}$")  # e.g. 2024-2025
    department_id: uuid.UUID
    start_date: date | None = None
    end_date: date | None = None


class SemesterUpdate(BaseModel):
    start_date: date | None = None
    end_date: date | None = None


class SemesterResponse(BaseModel):
    id: uuid.UUID
    number: int
    academic_year: str
    department_id: uuid.UUID
    start_date: date | None
    end_date: date | None

    model_config = {"from_attributes": True}


# ── Subject ───────────────────────────────────────────────────────────────────

class SubjectCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    code: str = Field(..., min_length=2, max_length=20)
    department_id: uuid.UUID
    semester_number: int = Field(..., ge=1, le=12)
    credits: int = Field(3, ge=1, le=6)


class SubjectUpdate(BaseModel):
    name: str | None = Field(None, min_length=2, max_length=255)
    credits: int | None = Field(None, ge=1, le=6)


class SubjectResponse(BaseModel):
    id: uuid.UUID
    name: str
    code: str
    department_id: uuid.UUID
    semester_number: int
    credits: int

    model_config = {"from_attributes": True}
