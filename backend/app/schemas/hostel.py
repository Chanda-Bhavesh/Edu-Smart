import uuid
from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.models.hostel import HostelLeaveStatus, HostelType, OutpassStatus, RoomType


# ── Hostel ─────────────────────────────────────────────────────────────────────

class HostelCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=200)
    hostel_type: HostelType
    warden_id: Optional[uuid.UUID] = None
    address: Optional[str] = None
    phone: Optional[str] = None
    total_capacity: int = Field(default=0, ge=0)


class HostelUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=200)
    hostel_type: Optional[HostelType] = None
    warden_id: Optional[uuid.UUID] = None
    address: Optional[str] = None
    phone: Optional[str] = None
    total_capacity: Optional[int] = Field(None, ge=0)
    is_active: Optional[bool] = None


class HostelResponse(BaseModel):
    id: uuid.UUID
    name: str
    hostel_type: HostelType
    warden_id: Optional[uuid.UUID]
    warden_name: Optional[str]
    address: Optional[str]
    phone: Optional[str]
    total_capacity: int
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Room ───────────────────────────────────────────────────────────────────────

class RoomCreate(BaseModel):
    room_number: str = Field(..., min_length=1, max_length=20)
    floor: int = Field(default=0, ge=0)
    room_type: RoomType
    capacity: int = Field(default=1, ge=1)


class RoomUpdate(BaseModel):
    room_number: Optional[str] = None
    floor: Optional[int] = Field(None, ge=0)
    room_type: Optional[RoomType] = None
    capacity: Optional[int] = Field(None, ge=1)
    is_active: Optional[bool] = None


class RoomResponse(BaseModel):
    id: uuid.UUID
    hostel_id: uuid.UUID
    room_number: str
    floor: int
    room_type: RoomType
    capacity: int
    current_occupancy: int = 0
    is_active: bool

    model_config = {"from_attributes": True}


# ── Allocation ─────────────────────────────────────────────────────────────────

class AllocationCreate(BaseModel):
    student_id: uuid.UUID
    room_id: uuid.UUID
    allocated_date: date
    notes: Optional[str] = None


class AllocationResponse(BaseModel):
    id: uuid.UUID
    student_id: uuid.UUID
    student_name: str
    roll_number: str
    room_id: uuid.UUID
    room_number: str
    hostel_name: str
    allocated_date: date
    vacated_date: Optional[date]
    is_active: bool
    notes: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Outpass ────────────────────────────────────────────────────────────────────

class OutpassCreate(BaseModel):
    reason: str = Field(..., min_length=5)
    destination: str = Field(..., min_length=3, max_length=300)
    contact_at_destination: Optional[str] = None
    from_datetime: datetime
    to_datetime: datetime


class OutpassReview(BaseModel):
    action: str = Field(..., pattern="^(approve|reject)$")
    remarks: Optional[str] = None


class OutpassResponse(BaseModel):
    id: uuid.UUID
    student_id: uuid.UUID
    student_name: str
    roll_number: str
    reason: str
    destination: str
    contact_at_destination: Optional[str]
    from_datetime: datetime
    to_datetime: datetime
    status: OutpassStatus
    reviewed_by: Optional[uuid.UUID]
    reviewer_name: Optional[str]
    reviewed_at: Optional[datetime]
    warden_remarks: Optional[str]
    requested_at: datetime

    model_config = {"from_attributes": True}


# ── Hostel Leave ───────────────────────────────────────────────────────────────

class LeaveCreate(BaseModel):
    reason: str = Field(..., min_length=5)
    destination: str = Field(..., min_length=3, max_length=300)
    from_date: date
    to_date: date
    parent_name: Optional[str] = None
    parent_contact: Optional[str] = None
    parent_relation: Optional[str] = None


class LeaveReview(BaseModel):
    action: str = Field(..., pattern="^(approve|reject)$")
    remarks: Optional[str] = None


class LeaveResponse(BaseModel):
    id: uuid.UUID
    student_id: uuid.UUID
    student_name: str
    roll_number: str
    reason: str
    destination: str
    from_date: date
    to_date: date
    parent_name: Optional[str]
    parent_contact: Optional[str]
    parent_relation: Optional[str]
    status: HostelLeaveStatus
    reviewed_by: Optional[uuid.UUID]
    reviewer_name: Optional[str]
    reviewed_at: Optional[datetime]
    warden_remarks: Optional[str]
    requested_at: datetime

    model_config = {"from_attributes": True}


# ── Visitor Log ────────────────────────────────────────────────────────────────

class VisitorCreate(BaseModel):
    student_id: uuid.UUID
    visitor_name: str = Field(..., min_length=2, max_length=200)
    visitor_relation: str = Field(..., min_length=2, max_length=100)
    visitor_phone: Optional[str] = None
    visitor_id_type: Optional[str] = None
    visitor_id_number: Optional[str] = None
    purpose: Optional[str] = None
    notes: Optional[str] = None


class VisitorResponse(BaseModel):
    id: uuid.UUID
    student_id: uuid.UUID
    student_name: str
    roll_number: str
    visitor_name: str
    visitor_relation: str
    visitor_phone: Optional[str]
    visitor_id_type: Optional[str]
    visitor_id_number: Optional[str]
    purpose: Optional[str]
    check_in_time: datetime
    check_out_time: Optional[datetime]
    logged_by: uuid.UUID
    logger_name: str
    notes: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Warden Dashboard ───────────────────────────────────────────────────────────

class WardenDashboard(BaseModel):
    hostel_id: uuid.UUID
    hostel_name: str
    total_capacity: int
    current_occupancy: int
    available_beds: int
    pending_outpasses: int
    pending_leaves: int
    todays_visitors: int
    recent_outpasses: list[OutpassResponse]
    recent_leaves: list[LeaveResponse]
