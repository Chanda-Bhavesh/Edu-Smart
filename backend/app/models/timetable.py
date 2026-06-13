import uuid
from datetime import datetime, time
from enum import Enum as PyEnum

from sqlalchemy import Time, DateTime, ForeignKey, Enum, String, Boolean, UniqueConstraint, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database import Base


class DayOfWeek(str, PyEnum):
    monday    = "monday"
    tuesday   = "tuesday"
    wednesday = "wednesday"
    thursday  = "thursday"
    friday    = "friday"
    saturday  = "saturday"


class TimetableSlot(Base):
    """
    One row = one recurring class period.
    e.g. "Machine Learning, Section A, every Monday 09:00–10:00, Room 204"
    """
    __tablename__ = "timetable_slots"
    __table_args__ = (
        # Same class cannot have two slots on the same day at the same start time
        UniqueConstraint(
            "course_assignment_id", "day_of_week", "start_time",
            name="uq_slot_assignment_day_time",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    course_assignment_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("course_assignments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    day_of_week:  Mapped[DayOfWeek]  = mapped_column(Enum(DayOfWeek),   nullable=False, index=True)
    start_time:   Mapped[time]       = mapped_column(Time,               nullable=False)
    end_time:     Mapped[time]       = mapped_column(Time,               nullable=False)
    room_number:  Mapped[str | None] = mapped_column(String(50),         nullable=True)
    is_active:    Mapped[bool]       = mapped_column(Boolean, default=True, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    course_assignment: Mapped["CourseAssignment"] = relationship(
        "CourseAssignment", foreign_keys=[course_assignment_id]
    )

    def __repr__(self) -> str:
        return f"<TimetableSlot {self.day_of_week} {self.start_time}–{self.end_time}>"
