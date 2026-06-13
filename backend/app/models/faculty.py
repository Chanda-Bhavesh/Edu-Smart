import uuid
from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import String, DateTime, ForeignKey, Enum, UniqueConstraint, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database import Base
from app.models.subject import faculty_subjects


class Designation(str, PyEnum):
    professor = "professor"
    associate_professor = "associate_professor"
    assistant_professor = "assistant_professor"
    lecturer = "lecturer"
    visiting_faculty = "visiting_faculty"


class Faculty(Base):
    __tablename__ = "faculty"
    __table_args__ = (
        UniqueConstraint("employee_id", name="uq_faculty_employee_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Link to users table
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)

    # Professional info
    employee_id: Mapped[str] = mapped_column(String(50), nullable=False)
    department_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("departments.id", ondelete="RESTRICT"), nullable=False)
    designation: Mapped[Designation] = mapped_column(Enum(Designation), nullable=False)
    specialization: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Contact
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    office_location: Mapped[str | None] = mapped_column(String(100), nullable=True)

    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    user: Mapped["User"] = relationship("User", foreign_keys=[user_id])
    department: Mapped["Department"] = relationship("Department", back_populates="faculty_members")
    subjects: Mapped[list["Subject"]] = relationship("Subject", secondary=faculty_subjects, back_populates="faculty_members")

    def __repr__(self) -> str:
        return f"<Faculty emp_id={self.employee_id}>"
