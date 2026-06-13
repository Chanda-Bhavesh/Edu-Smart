import uuid
from datetime import datetime, date
from enum import Enum as PyEnum

from sqlalchemy import String, DateTime, Date, ForeignKey, Enum, Text, UniqueConstraint, Boolean, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database import Base


class AttendanceStatus(str, PyEnum):
    present = "present"
    absent  = "absent"
    late    = "late"
    medical = "medical"


class AttendanceMethod(str, PyEnum):
    manual = "manual"
    qr     = "qr"
    face   = "face"


class Attendance(Base):
    __tablename__ = "attendance"
    __table_args__ = (
        # One student can only have ONE record per timetable slot per date
        # (replaces the old daily-once constraint)
        UniqueConstraint(
            "student_id", "timetable_slot_id", "date",
            name="uq_attendance_student_slot_date",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    student_id:           Mapped[uuid.UUID]      = mapped_column(ForeignKey("students.id",           ondelete="CASCADE"),  nullable=False, index=True)
    timetable_slot_id:    Mapped[uuid.UUID]      = mapped_column(ForeignKey("timetable_slots.id",    ondelete="CASCADE"),  nullable=False, index=True)
    subject_id:           Mapped[uuid.UUID]      = mapped_column(ForeignKey("subjects.id",           ondelete="CASCADE"),  nullable=False, index=True)
    faculty_id:           Mapped[uuid.UUID | None] = mapped_column(ForeignKey("faculty.id",          ondelete="SET NULL"), nullable=True,  index=True)
    course_assignment_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("course_assignments.id", ondelete="SET NULL"), nullable=True)

    date:      Mapped[date]             = mapped_column(Date,                   nullable=False, index=True)
    status:    Mapped[AttendanceStatus] = mapped_column(Enum(AttendanceStatus), nullable=False)
    method:    Mapped[AttendanceMethod] = mapped_column(Enum(AttendanceMethod), nullable=False, default=AttendanceMethod.manual)
    notes:     Mapped[str | None]       = mapped_column(Text,                   nullable=True)
    marked_at: Mapped[datetime]         = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    student:           Mapped["Student"]               = relationship("Student",          foreign_keys=[student_id])
    timetable_slot:    Mapped["TimetableSlot"]         = relationship("TimetableSlot",    foreign_keys=[timetable_slot_id])
    subject:           Mapped["Subject"]               = relationship("Subject",          foreign_keys=[subject_id])
    faculty:           Mapped["Faculty | None"]        = relationship("Faculty",          foreign_keys=[faculty_id])
    course_assignment: Mapped["CourseAssignment | None"] = relationship("CourseAssignment", foreign_keys=[course_assignment_id])

    def __repr__(self) -> str:
        return (
            f"<Attendance student={self.student_id} "
            f"slot={self.timetable_slot_id} date={self.date} status={self.status}>"
        )


class QRSession(Base):
    """Tracks active QR attendance sessions — now tied to a specific timetable slot."""
    __tablename__ = "qr_sessions"

    id:                   Mapped[uuid.UUID]  = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    timetable_slot_id:    Mapped[uuid.UUID]  = mapped_column(ForeignKey("timetable_slots.id",    ondelete="CASCADE"), nullable=False)
    course_assignment_id: Mapped[uuid.UUID]  = mapped_column(ForeignKey("course_assignments.id", ondelete="CASCADE"), nullable=False)
    faculty_id:           Mapped[uuid.UUID]  = mapped_column(ForeignKey("faculty.id",            ondelete="CASCADE"), nullable=False)
    date:                 Mapped[date]       = mapped_column(Date,                nullable=False)
    token:                Mapped[str]        = mapped_column(String(512), unique=True, nullable=False)
    expires_at:           Mapped[datetime]   = mapped_column(DateTime(timezone=True), nullable=False)
    is_active:            Mapped[bool]       = mapped_column(Boolean, default=True, nullable=False)
    created_at:           Mapped[datetime]   = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    timetable_slot:    Mapped["TimetableSlot"]    = relationship("TimetableSlot",    foreign_keys=[timetable_slot_id])
    course_assignment: Mapped["CourseAssignment"] = relationship("CourseAssignment", foreign_keys=[course_assignment_id])
    faculty:           Mapped["Faculty"]          = relationship("Faculty",          foreign_keys=[faculty_id])

    def __repr__(self) -> str:
        return f"<QRSession slot={self.timetable_slot_id} date={self.date} active={self.is_active}>"
