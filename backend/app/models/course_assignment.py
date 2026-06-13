import uuid
from datetime import datetime

from sqlalchemy import String, DateTime, ForeignKey, Boolean, UniqueConstraint, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database import Base


class CourseAssignment(Base):
    """
    Maps a faculty member to a subject + semester + section.
    This is the 'class' entity — it answers:
    'Who teaches what, to which section, in which semester?'
    """
    __tablename__ = "course_assignments"
    __table_args__ = (
        # One faculty cannot be assigned the same subject+section+semester twice
        UniqueConstraint("faculty_id", "subject_id", "semester_id", "section", name="uq_course_assignment"),
        # One section can only have one faculty per subject per semester
        UniqueConstraint("subject_id", "semester_id", "section", name="uq_section_subject_semester"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    faculty_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("faculty.id", ondelete="CASCADE"), nullable=False, index=True
    )
    subject_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    semester_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("semesters.id", ondelete="CASCADE"), nullable=False, index=True
    )
    section: Mapped[str] = mapped_column(String(10), nullable=False)
    academic_year: Mapped[str] = mapped_column(String(9), nullable=False)  # e.g. "2024-2025"
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    faculty: Mapped["Faculty"] = relationship("Faculty", foreign_keys=[faculty_id])
    subject: Mapped["Subject"] = relationship("Subject", foreign_keys=[subject_id])
    semester: Mapped["Semester"] = relationship("Semester", foreign_keys=[semester_id])

    def __repr__(self) -> str:
        return f"<CourseAssignment faculty={self.faculty_id} subject={self.subject_id} section={self.section}>"
