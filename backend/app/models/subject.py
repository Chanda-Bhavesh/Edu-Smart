import uuid
from datetime import datetime

from sqlalchemy import String, DateTime, ForeignKey, Integer, UniqueConstraint, Table, Column, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database import Base

# Junction table: faculty ↔ subjects (many-to-many)
faculty_subjects = Table(
    "faculty_subjects",
    Base.metadata,
    Column("faculty_id", UUID(as_uuid=True), ForeignKey("faculty.id", ondelete="CASCADE"), primary_key=True),
    Column("subject_id", UUID(as_uuid=True), ForeignKey("subjects.id", ondelete="CASCADE"), primary_key=True),
)

# Junction table: students ↔ subjects (course enrollment)
student_enrollments = Table(
    "student_enrollments",
    Base.metadata,
    Column("student_id", UUID(as_uuid=True), ForeignKey("students.id", ondelete="CASCADE"), primary_key=True),
    Column("subject_id", UUID(as_uuid=True), ForeignKey("subjects.id", ondelete="CASCADE"), primary_key=True),
)


class Subject(Base):
    __tablename__ = "subjects"
    __table_args__ = (
        UniqueConstraint("code", name="uq_subject_code"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    code: Mapped[str] = mapped_column(String(20), nullable=False)
    department_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("departments.id", ondelete="CASCADE"), nullable=False)
    semester_number: Mapped[int] = mapped_column(Integer, nullable=False)
    credits: Mapped[int] = mapped_column(Integer, default=3, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    department: Mapped["Department"] = relationship("Department", back_populates="subjects")
    faculty_members: Mapped[list["Faculty"]] = relationship("Faculty", secondary=faculty_subjects, back_populates="subjects")
    enrolled_students: Mapped[list["Student"]] = relationship("Student", secondary=student_enrollments, back_populates="enrolled_subjects")

    def __repr__(self) -> str:
        return f"<Subject code={self.code} name={self.name}>"
