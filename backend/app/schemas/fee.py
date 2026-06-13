import uuid
from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field, model_validator

from app.models.fee import FeeStatus, PaymentMode


# ── Fee Structure ──────────────────────────────────────────────────────────────

class FeeStructureCreate(BaseModel):
    department_id: uuid.UUID
    semester_id: uuid.UUID
    academic_year: str = Field(..., pattern=r"^\d{4}-\d{2}$", examples=["2024-25"])

    tuition_fee: float = Field(default=0, ge=0)
    exam_fee: float = Field(default=0, ge=0)
    library_fee: float = Field(default=0, ge=0)
    lab_fee: float = Field(default=0, ge=0)
    other_fee: float = Field(default=0, ge=0)

    due_date: date
    late_fine_per_day: float = Field(default=0, ge=0)
    description: Optional[str] = None

    @model_validator(mode="after")
    def compute_total(self) -> "FeeStructureCreate":
        # total is validated here; service also recalculates
        return self


class FeeStructureUpdate(BaseModel):
    tuition_fee: Optional[float] = Field(default=None, ge=0)
    exam_fee: Optional[float] = Field(default=None, ge=0)
    library_fee: Optional[float] = Field(default=None, ge=0)
    lab_fee: Optional[float] = Field(default=None, ge=0)
    other_fee: Optional[float] = Field(default=None, ge=0)
    due_date: Optional[date] = None
    late_fine_per_day: Optional[float] = Field(default=None, ge=0)
    description: Optional[str] = None


class FeeStructureResponse(BaseModel):
    id: uuid.UUID
    department_id: uuid.UUID
    semester_id: uuid.UUID
    academic_year: str
    tuition_fee: float
    exam_fee: float
    library_fee: float
    lab_fee: float
    other_fee: float
    total_fee: float
    due_date: date
    late_fine_per_day: float
    description: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Student Fee ────────────────────────────────────────────────────────────────

class StudentFeeResponse(BaseModel):
    id: uuid.UUID
    student_id: uuid.UUID
    fee_structure_id: uuid.UUID
    total_amount: float
    discount_amount: float
    fine_amount: float
    net_amount: float
    amount_paid: float
    balance: float
    status: FeeStatus
    due_date: date
    waiver_reason: Optional[str]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class StudentFeeDetail(StudentFeeResponse):
    """Extended view for student — includes fee breakdown from structure."""
    academic_year: Optional[str] = None
    tuition_fee: Optional[float] = None
    exam_fee: Optional[float] = None
    library_fee: Optional[float] = None
    lab_fee: Optional[float] = None
    other_fee: Optional[float] = None
    department_name: Optional[str] = None
    semester_number: Optional[int] = None


class ApplyWaiver(BaseModel):
    discount_amount: float = Field(..., ge=0)
    reason: str = Field(..., min_length=5)


# ── Payment ────────────────────────────────────────────────────────────────────

class RecordPayment(BaseModel):
    amount: float = Field(..., gt=0)
    payment_mode: PaymentMode
    transaction_id: Optional[str] = Field(default=None, max_length=100)
    payment_date: date
    remarks: Optional[str] = None


class FeePaymentResponse(BaseModel):
    id: uuid.UUID
    student_fee_id: uuid.UUID
    student_id: uuid.UUID
    amount: float
    payment_mode: PaymentMode
    transaction_id: Optional[str]
    payment_date: date
    receipt_number: str
    remarks: Optional[str]
    recorded_by_id: Optional[uuid.UUID]
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Reports ────────────────────────────────────────────────────────────────────

class FeeCollectionSummary(BaseModel):
    """Admin dashboard: total collection stats for a fee structure."""
    fee_structure_id: uuid.UUID
    academic_year: str
    department_name: str
    semester_number: int
    total_students: int
    paid_count: int
    partial_count: int
    pending_count: int
    overdue_count: int
    waived_count: int
    total_expected: float
    total_collected: float
    total_balance: float
    collection_percentage: float


class StudentFeeSummary(BaseModel):
    """Admin/Student: full fee history for one student across all semesters."""
    student_id: uuid.UUID
    student_name: str
    roll_number: str
    fees: list[StudentFeeDetail]
    total_paid_ever: float
    total_outstanding: float
