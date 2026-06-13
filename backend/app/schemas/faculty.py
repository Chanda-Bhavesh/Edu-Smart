import uuid
from datetime import datetime
from pydantic import BaseModel, Field
from app.models.faculty import Designation
from app.schemas.department import SubjectResponse


class FacultyCreate(BaseModel):
    # User account fields
    full_name: str = Field(..., min_length=2, max_length=255)
    email: str = Field(..., pattern=r"^[\w\.\+\-]+@[\w]+\.[a-z]{2,}$")
    password: str = Field(..., min_length=8, max_length=128)

    # Professional fields
    employee_id: str = Field(..., min_length=2, max_length=50)
    department_id: uuid.UUID
    designation: Designation
    specialization: str | None = Field(None, max_length=255)
    phone: str | None = Field(None, max_length=20)
    office_location: str | None = Field(None, max_length=100)


class FacultyUpdate(BaseModel):
    full_name: str | None = Field(None, min_length=2, max_length=255)
    designation: Designation | None = None
    specialization: str | None = Field(None, max_length=255)
    phone: str | None = Field(None, max_length=20)
    office_location: str | None = Field(None, max_length=100)
    department_id: uuid.UUID | None = None


class FacultySubjectAssign(BaseModel):
    subject_id: uuid.UUID


class FacultyUserInfo(BaseModel):
    id: uuid.UUID
    email: str
    full_name: str
    is_verified: bool

    model_config = {"from_attributes": True}


class FacultyDeptInfo(BaseModel):
    id: uuid.UUID
    name: str
    code: str

    model_config = {"from_attributes": True}


class FacultyResponse(BaseModel):
    id: uuid.UUID
    employee_id: str
    department_id: uuid.UUID
    designation: Designation
    specialization: str | None
    phone: str | None
    office_location: str | None
    is_active: bool
    created_at: datetime
    user: FacultyUserInfo
    department: FacultyDeptInfo
    subjects: list[SubjectResponse]

    model_config = {"from_attributes": True}


class FacultyListResponse(BaseModel):
    id: uuid.UUID
    employee_id: str
    department_id: uuid.UUID
    designation: Designation
    is_active: bool
    user: FacultyUserInfo
    department: FacultyDeptInfo

    model_config = {"from_attributes": True}


class PaginatedFaculty(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[FacultyListResponse]
