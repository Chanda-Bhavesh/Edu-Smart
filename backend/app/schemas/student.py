import uuid
from datetime import datetime
from pydantic import BaseModel, Field, field_validator
from app.models.student import StudentStatus


class StudentCreate(BaseModel):
    # User account fields
    full_name: str = Field(..., min_length=2, max_length=255)
    email: str = Field(..., pattern=r"^[\w\.\+\-]+@[\w]+\.[a-z]{2,}$")
    password: str = Field(..., min_length=8, max_length=128)

    # Academic fields
    roll_number: str = Field(..., min_length=2, max_length=50)
    department_id: uuid.UUID
    semester_id: uuid.UUID
    section: str | None = Field(None, max_length=10)

    # Personal fields
    phone: str | None = Field(None, max_length=20)
    date_of_birth: str | None = None
    blood_group: str | None = Field(None, max_length=5)
    address: str | None = None

    # Guardian fields
    guardian_name: str | None = Field(None, max_length=255)
    guardian_phone: str | None = Field(None, max_length=20)
    guardian_relation: str | None = Field(None, max_length=50)


class StudentUpdate(BaseModel):
    full_name: str | None = Field(None, min_length=2, max_length=255)
    section: str | None = Field(None, max_length=10)
    semester_id: uuid.UUID | None = None
    phone: str | None = Field(None, max_length=20)
    date_of_birth: str | None = None
    blood_group: str | None = Field(None, max_length=5)
    address: str | None = None
    guardian_name: str | None = Field(None, max_length=255)
    guardian_phone: str | None = Field(None, max_length=20)
    guardian_relation: str | None = Field(None, max_length=50)


class StudentStatusUpdate(BaseModel):
    status: StudentStatus


class StudentUserInfo(BaseModel):
    id: uuid.UUID
    email: str
    full_name: str
    role: str = "student"
    is_verified: bool

    model_config = {"from_attributes": True}


class StudentDeptInfo(BaseModel):
    id: uuid.UUID
    name: str
    code: str

    model_config = {"from_attributes": True}


class StudentSemInfo(BaseModel):
    id: uuid.UUID
    number: int

    model_config = {"from_attributes": True}


class StudentResponse(BaseModel):
    id: uuid.UUID
    roll_number: str
    department_id: uuid.UUID
    semester_id: uuid.UUID
    section: str | None
    status: StudentStatus
    phone: str | None
    date_of_birth: str | None
    blood_group: str | None
    address: str | None
    guardian_name: str | None
    guardian_phone: str | None
    guardian_relation: str | None
    created_at: datetime
    user: StudentUserInfo
    department: StudentDeptInfo
    semester: StudentSemInfo

    model_config = {"from_attributes": True}


class StudentListResponse(BaseModel):
    id: uuid.UUID
    roll_number: str
    status: StudentStatus
    department_id: uuid.UUID
    semester_id: uuid.UUID
    section: str | None
    user: StudentUserInfo
    department: StudentDeptInfo
    semester: StudentSemInfo

    model_config = {"from_attributes": True}


class PaginatedStudents(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[StudentListResponse]
