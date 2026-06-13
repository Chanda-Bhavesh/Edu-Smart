import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean, DateTime, Enum, ForeignKey,
    String, Text, UniqueConstraint, UUID,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database import Base


class AnnouncementTarget(str, enum.Enum):
    all = "all"                          # every user in the system
    students = "students"                # all students
    faculty = "faculty"                  # all faculty
    department = "department"            # everyone in a department
    department_students = "dept_students"  # only students in a department
    department_faculty = "dept_faculty"    # only faculty in a department
    semester_section = "semester_section"  # students in a specific sem + section


class AnnouncementPriority(str, enum.Enum):
    normal = "normal"
    important = "important"
    urgent = "urgent"


class NotificationType(str, enum.Enum):
    announcement = "announcement"
    assignment_created = "assignment_created"
    assignment_graded = "assignment_graded"
    assignment_deadline = "assignment_deadline"
    fee_assigned = "fee_assigned"
    fee_payment_recorded = "fee_payment_recorded"
    fee_overdue = "fee_overdue"
    attendance_low = "attendance_low"
    leave_approved = "leave_approved"
    leave_rejected = "leave_rejected"
    general = "general"


class Announcement(Base):
    __tablename__ = "announcements"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)

    # Targeting
    target_type: Mapped[AnnouncementTarget] = mapped_column(
        Enum(AnnouncementTarget), default=AnnouncementTarget.all, nullable=False
    )
    department_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("departments.id", ondelete="SET NULL"), nullable=True
    )
    semester_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("semesters.id", ondelete="SET NULL"), nullable=True
    )
    section: Mapped[str | None] = mapped_column(String(10), nullable=True)
    target_role: Mapped[str | None] = mapped_column(String(30), nullable=True)

    # Display options
    is_pinned: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    priority: Mapped[AnnouncementPriority] = mapped_column(
        Enum(AnnouncementPriority), default=AnnouncementPriority.normal, nullable=False
    )

    # Optional file attachment
    file_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    file_name: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Email flag — if True, send email to all targeted users
    send_email: Mapped[bool] = mapped_column(Boolean, default=False)

    created_by_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    published_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    created_by = relationship("User", foreign_keys=[created_by_id])
    department = relationship("Department", backref="announcements")
    semester = relationship("Semester", backref="announcements")
    reads = relationship("AnnouncementRead", back_populates="announcement", cascade="all, delete-orphan")


class AnnouncementRead(Base):
    """Tracks which users have read which announcements."""
    __tablename__ = "announcement_reads"
    __table_args__ = (
        UniqueConstraint("announcement_id", "user_id", name="uq_announcement_read"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    announcement_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("announcements.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    read_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    announcement = relationship("Announcement", back_populates="reads")
    user = relationship("User", backref="announcement_reads")


class Notification(Base):
    """
    Per-user event-based notification.
    Created programmatically when key events occur
    (assignment published, fee payment recorded, leave approved, etc.)
    """
    __tablename__ = "notifications"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    notification_type: Mapped[NotificationType] = mapped_column(
        Enum(NotificationType), default=NotificationType.general, nullable=False
    )

    # Optional: link back to the object that triggered the notification
    reference_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    reference_type: Mapped[str | None] = mapped_column(String(50), nullable=True)

    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    user = relationship("User", backref="notifications")
