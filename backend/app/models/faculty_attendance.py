import uuid
from datetime import datetime, date
from enum import Enum as PyEnum

from sqlalchemy import String, DateTime, Date, Time, ForeignKey, Enum, Text, Float, UniqueConstraint, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database import Base


class FacultyAttendanceStatus(str, PyEnum):
    present  = "present"
    absent   = "absent"
    on_leave = "on_leave"
    half_day = "half_day"


class LeaveType(str, PyEnum):
    casual    = "casual"
    medical   = "medical"
    emergency = "emergency"
    maternity = "maternity"
    other     = "other"


class LeaveStatus(str, PyEnum):
    pending  = "pending"
    approved = "approved"
    rejected = "rejected"


class FacultyAttendance(Base):
    __tablename__ = "faculty_attendance"
    __table_args__ = (
        UniqueConstraint("faculty_id", "date", name="uq_faculty_attendance_date"),
    )

    id:             Mapped[uuid.UUID]              = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    faculty_id:     Mapped[uuid.UUID]              = mapped_column(ForeignKey("faculty.id", ondelete="CASCADE"), nullable=False, index=True)
    date:           Mapped[date]                   = mapped_column(Date, nullable=False, index=True)
    status:         Mapped[FacultyAttendanceStatus] = mapped_column(Enum(FacultyAttendanceStatus), nullable=False, default=FacultyAttendanceStatus.present)
    check_in_time:  Mapped[datetime | None]        = mapped_column(DateTime(timezone=True), nullable=True)
    check_out_time: Mapped[datetime | None]        = mapped_column(DateTime(timezone=True), nullable=True)
    working_hours:  Mapped[float | None]           = mapped_column(Float, nullable=True)
    notes:          Mapped[str | None]             = mapped_column(Text, nullable=True)
    created_at:     Mapped[datetime]               = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at:     Mapped[datetime]               = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    faculty: Mapped["Faculty"] = relationship("Faculty", foreign_keys=[faculty_id])

    def __repr__(self) -> str:
        return f"<FacultyAttendance faculty={self.faculty_id} date={self.date} status={self.status}>"


class LeaveRequest(Base):
    __tablename__ = "leave_requests"

    id:             Mapped[uuid.UUID]  = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    faculty_id:     Mapped[uuid.UUID]  = mapped_column(ForeignKey("faculty.id", ondelete="CASCADE"), nullable=False, index=True)
    leave_type:     Mapped[LeaveType]  = mapped_column(Enum(LeaveType),   nullable=False)
    start_date:     Mapped[date]       = mapped_column(Date, nullable=False)
    end_date:       Mapped[date]       = mapped_column(Date, nullable=False)
    reason:         Mapped[str]        = mapped_column(Text, nullable=False)
    status:         Mapped[LeaveStatus] = mapped_column(Enum(LeaveStatus), default=LeaveStatus.pending, nullable=False)
    reviewed_by:    Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    review_comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    applied_at:     Mapped[datetime]   = mapped_column(DateTime(timezone=True), server_default=func.now())
    reviewed_at:    Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    faculty:   Mapped["Faculty"]      = relationship("Faculty", foreign_keys=[faculty_id])
    reviewer:  Mapped["User | None"]  = relationship("User",    foreign_keys=[reviewed_by])

    def __repr__(self) -> str:
        return f"<LeaveRequest faculty={self.faculty_id} type={self.leave_type} status={self.status}>"
