import uuid
from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import String, DateTime, ForeignKey, Enum, UniqueConstraint, Text, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database import Base
from app.models.subject import student_enrollments


class StudentStatus(str, PyEnum):
    active = "active"
    suspended = "suspended"
    alumni = "alumni"
    transferred = "transferred"


class Student(Base):
    __tablename__ = "students"
    __table_args__ = (
        UniqueConstraint("roll_number", name="uq_student_roll_number"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Link to users table
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)

    # Academic info
    roll_number: Mapped[str] = mapped_column(String(50), nullable=False)
    department_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("departments.id", ondelete="RESTRICT"), nullable=False)
    semester_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("semesters.id", ondelete="RESTRICT"), nullable=False)
    section: Mapped[str | None] = mapped_column(String(10), nullable=True)
    status: Mapped[StudentStatus] = mapped_column(Enum(StudentStatus), default=StudentStatus.active, nullable=False)

    # Personal info
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    date_of_birth: Mapped[str | None] = mapped_column(String(20), nullable=True)
    blood_group: Mapped[str | None] = mapped_column(String(5), nullable=True)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Guardian info
    guardian_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    guardian_phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    guardian_relation: Mapped[str | None] = mapped_column(String(50), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    user: Mapped["User"] = relationship("User", foreign_keys=[user_id])
    department: Mapped["Department"] = relationship("Department", back_populates="students")
    semester: Mapped["Semester"] = relationship("Semester", back_populates="students")
    enrolled_subjects: Mapped[list["Subject"]] = relationship("Subject", secondary=student_enrollments, back_populates="enrolled_students")

    def __repr__(self) -> str:
        return f"<Student roll={self.roll_number}>"
