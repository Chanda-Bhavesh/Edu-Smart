import enum
import uuid
from datetime import date, datetime

from sqlalchemy import (
    Boolean, Date, DateTime, Enum, ForeignKey,
    Numeric, String, Text, UniqueConstraint, UUID,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database import Base


class FeeStatus(str, enum.Enum):
    pending = "pending"       # fee assigned, not yet due or not yet paid
    partial = "partial"       # some amount paid, balance remaining
    paid = "paid"             # fully paid
    overdue = "overdue"       # past due date with unpaid balance
    waived = "waived"         # fee fully waived by admin


class PaymentMode(str, enum.Enum):
    cash = "cash"
    online = "online"
    cheque = "cheque"
    demand_draft = "demand_draft"


class FeeStructure(Base):
    """
    Defines the fee breakdown for a department + semester + academic year.
    Admin creates one fee structure per dept/semester/year, then assigns it to students.
    """
    __tablename__ = "fee_structures"
    __table_args__ = (
        UniqueConstraint(
            "department_id", "semester_id", "academic_year",
            name="uq_fee_structure_dept_sem_year",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    department_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("departments.id", ondelete="CASCADE"), nullable=False
    )
    semester_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("semesters.id", ondelete="CASCADE"), nullable=False
    )
    academic_year: Mapped[str] = mapped_column(String(10), nullable=False)  # e.g. "2024-25"

    tuition_fee: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    exam_fee: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    library_fee: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    lab_fee: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    other_fee: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    total_fee: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)

    due_date: Mapped[date] = mapped_column(Date, nullable=False)
    late_fine_per_day: Mapped[float] = mapped_column(Numeric(8, 2), default=0)

    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_by_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    department = relationship("Department", backref="fee_structures")
    semester = relationship("Semester", backref="fee_structures")
    created_by = relationship("User", foreign_keys=[created_by_id])
    student_fees = relationship("StudentFee", back_populates="fee_structure", cascade="all, delete-orphan")


class StudentFee(Base):
    """
    One record per student per fee structure.
    Tracks how much is owed, paid, and the current status.
    """
    __tablename__ = "student_fees"
    __table_args__ = (
        UniqueConstraint("student_id", "fee_structure_id", name="uq_student_fee"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    student_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("students.id", ondelete="CASCADE"), nullable=False
    )
    fee_structure_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("fee_structures.id", ondelete="CASCADE"), nullable=False
    )

    total_amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    discount_amount: Mapped[float] = mapped_column(Numeric(10, 2), default=0)  # scholarship / waiver
    fine_amount: Mapped[float] = mapped_column(Numeric(10, 2), default=0)      # late payment fine
    net_amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)  # total - discount + fine
    amount_paid: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    balance: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)     # net - paid

    status: Mapped[FeeStatus] = mapped_column(
        Enum(FeeStatus), default=FeeStatus.pending, nullable=False
    )
    due_date: Mapped[date] = mapped_column(Date, nullable=False)

    waiver_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    waiver_approved_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    student = relationship("Student", backref="fees")
    fee_structure = relationship("FeeStructure", back_populates="student_fees")
    waiver_approved_by = relationship("User", foreign_keys=[waiver_approved_by_id])
    payments = relationship("FeePayment", back_populates="student_fee", cascade="all, delete-orphan")


class FeePayment(Base):
    """
    Individual payment transaction record.
    Multiple payments are possible for one StudentFee (partial payments).
    """
    __tablename__ = "fee_payments"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    student_fee_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("student_fees.id", ondelete="CASCADE"), nullable=False
    )
    student_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("students.id", ondelete="CASCADE"), nullable=False
    )

    amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    payment_mode: Mapped[PaymentMode] = mapped_column(Enum(PaymentMode), nullable=False)
    transaction_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    payment_date: Mapped[date] = mapped_column(Date, nullable=False)
    receipt_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    remarks: Mapped[str | None] = mapped_column(Text, nullable=True)

    recorded_by_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    student_fee = relationship("StudentFee", back_populates="payments")
    student = relationship("Student", backref="fee_payments")
    recorded_by = relationship("User", foreign_keys=[recorded_by_id])
