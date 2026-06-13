import enum
import uuid
from datetime import date, datetime

from sqlalchemy import (
    Boolean, Date, DateTime, Enum, ForeignKey,
    Index, Integer, String, Text, UniqueConstraint, UUID,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func, text

from app.database import Base


class HostelType(str, enum.Enum):
    boys = "boys"
    girls = "girls"
    mixed = "mixed"


class RoomType(str, enum.Enum):
    single = "single"
    double = "double"
    triple = "triple"
    dormitory = "dormitory"


class OutpassStatus(str, enum.Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"
    checked_out = "checked_out"   # student physically left
    returned = "returned"         # student back in campus


class HostelLeaveStatus(str, enum.Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"


class Hostel(Base):
    __tablename__ = "hostels"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False, unique=True)
    hostel_type: Mapped[HostelType] = mapped_column(Enum(HostelType), nullable=False)
    warden_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    total_capacity: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    warden = relationship("User", foreign_keys=[warden_id])
    rooms = relationship("HostelRoom", back_populates="hostel", cascade="all, delete-orphan")


class HostelRoom(Base):
    __tablename__ = "hostel_rooms"
    __table_args__ = (
        UniqueConstraint("hostel_id", "room_number", name="uq_hostel_room"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    hostel_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("hostels.id", ondelete="CASCADE"), nullable=False
    )
    room_number: Mapped[str] = mapped_column(String(20), nullable=False)
    floor: Mapped[int] = mapped_column(Integer, default=0)
    room_type: Mapped[RoomType] = mapped_column(Enum(RoomType), nullable=False)
    capacity: Mapped[int] = mapped_column(Integer, default=1)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    hostel = relationship("Hostel", back_populates="rooms")
    allocations = relationship(
        "HostelAllocation", back_populates="room", cascade="all, delete-orphan"
    )


class HostelAllocation(Base):
    """One active room allocation per student at any time."""
    __tablename__ = "hostel_allocations"
    __table_args__ = (
        # partial unique index: only one active allocation per student
        Index(
            "uq_active_student_allocation",
            "student_id",
            unique=True,
            postgresql_where=text("is_active = TRUE"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    student_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("students.id", ondelete="CASCADE"), nullable=False
    )
    room_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("hostel_rooms.id", ondelete="CASCADE"), nullable=False
    )
    allocated_date: Mapped[date] = mapped_column(Date, nullable=False)
    vacated_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    allocated_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    student = relationship("Student", backref="hostel_allocation")
    room = relationship("HostelRoom", back_populates="allocations")
    allocator = relationship("User", foreign_keys=[allocated_by])


class Outpass(Base):
    """Short-duration outpass request (hours to 1-2 days)."""
    __tablename__ = "outpasses"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    student_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("students.id", ondelete="CASCADE"), nullable=False
    )
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    destination: Mapped[str] = mapped_column(String(300), nullable=False)
    contact_at_destination: Mapped[str | None] = mapped_column(String(20), nullable=True)
    from_datetime: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    to_datetime: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[OutpassStatus] = mapped_column(
        Enum(OutpassStatus), default=OutpassStatus.pending, nullable=False
    )
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    warden_remarks: Mapped[str | None] = mapped_column(Text, nullable=True)
    requested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    student = relationship("Student", backref="outpasses")
    reviewer = relationship("User", foreign_keys=[reviewed_by])


class HostelLeaveRequest(Base):
    """Multi-day leave request (home visit, medical, etc.)."""
    __tablename__ = "hostel_leave_requests"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    student_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("students.id", ondelete="CASCADE"), nullable=False
    )
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    destination: Mapped[str] = mapped_column(String(300), nullable=False)
    from_date: Mapped[date] = mapped_column(Date, nullable=False)
    to_date: Mapped[date] = mapped_column(Date, nullable=False)
    parent_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    parent_contact: Mapped[str | None] = mapped_column(String(20), nullable=True)
    parent_relation: Mapped[str | None] = mapped_column(String(50), nullable=True)
    status: Mapped[HostelLeaveStatus] = mapped_column(
        Enum(HostelLeaveStatus), default=HostelLeaveStatus.pending, nullable=False
    )
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    warden_remarks: Mapped[str | None] = mapped_column(Text, nullable=True)
    requested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    student = relationship("Student", backref="hostel_leave_requests")
    reviewer = relationship("User", foreign_keys=[reviewed_by])


class VisitorLog(Base):
    """Visitor check-in/out log maintained by the warden/guard."""
    __tablename__ = "hostel_visitor_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    student_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("students.id", ondelete="CASCADE"), nullable=False
    )
    visitor_name: Mapped[str] = mapped_column(String(200), nullable=False)
    visitor_relation: Mapped[str] = mapped_column(String(100), nullable=False)
    visitor_phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    visitor_id_type: Mapped[str | None] = mapped_column(String(50), nullable=True)   # Aadhaar, DL, etc.
    visitor_id_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    purpose: Mapped[str | None] = mapped_column(Text, nullable=True)
    check_in_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    check_out_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    logged_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    student = relationship("Student", backref="visitor_logs")
    logger = relationship("User", foreign_keys=[logged_by])
