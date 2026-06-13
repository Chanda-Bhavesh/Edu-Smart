"""
Hostel Management service.

Covers:
  - Hostel & room CRUD (org_admin / warden)
  - Student room allocation & vacation
  - Outpass: apply (student), approve/reject/checkout/return (warden)
  - Leave: apply (student), approve/reject (warden)
  - Visitor log: check-in / check-out (warden)
  - Warden dashboard aggregates
"""
import uuid
from datetime import date, datetime, timezone
from typing import Optional

from fastapi import HTTPException
from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.hostel import (
    Hostel, HostelAllocation, HostelLeaveRequest, HostelLeaveStatus,
    HostelRoom, Outpass, OutpassStatus, RoomType, VisitorLog,
)
from app.models.student import Student
from app.models.user import User
from app.schemas.hostel import (
    AllocationCreate, AllocationResponse,
    HostelCreate, HostelResponse, HostelUpdate,
    LeaveCreate, LeaveResponse, LeaveReview,
    OutpassCreate, OutpassResponse, OutpassReview,
    RoomCreate, RoomResponse, RoomUpdate,
    VisitorCreate, VisitorResponse, WardenDashboard,
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


# ── Helpers ────────────────────────────────────────────────────────────────────

async def _get_student(db: AsyncSession, student_id: uuid.UUID) -> Student:
    result = await db.execute(
        select(Student).where(Student.id == student_id).options(selectinload(Student.user))
    )
    s = result.scalar_one_or_none()
    if not s:
        raise HTTPException(status_code=404, detail="Student not found")
    return s


def _student_name(s: Student) -> str:
    return s.user.full_name if s.user else "Unknown"


async def _room_occupancy(db: AsyncSession, room_id: uuid.UUID) -> int:
    result = await db.execute(
        select(func.count(HostelAllocation.id)).where(
            HostelAllocation.room_id == room_id,
            HostelAllocation.is_active == True,
        )
    )
    return result.scalar() or 0


def _hostel_response(hostel: Hostel) -> HostelResponse:
    return HostelResponse(
        id=hostel.id,
        name=hostel.name,
        hostel_type=hostel.hostel_type,
        warden_id=hostel.warden_id,
        warden_name=hostel.warden.full_name if hostel.warden else None,
        address=hostel.address,
        phone=hostel.phone,
        total_capacity=hostel.total_capacity,
        is_active=hostel.is_active,
        created_at=hostel.created_at,
    )


def _outpass_response(op: Outpass) -> OutpassResponse:
    s = op.student
    return OutpassResponse(
        id=op.id,
        student_id=op.student_id,
        student_name=_student_name(s) if s else "Unknown",
        roll_number=s.roll_number if s else "",
        reason=op.reason,
        destination=op.destination,
        contact_at_destination=op.contact_at_destination,
        from_datetime=op.from_datetime,
        to_datetime=op.to_datetime,
        status=op.status,
        reviewed_by=op.reviewed_by,
        reviewer_name=op.reviewer.full_name if op.reviewer else None,
        reviewed_at=op.reviewed_at,
        warden_remarks=op.warden_remarks,
        requested_at=op.requested_at,
    )


def _leave_response(lr: HostelLeaveRequest) -> LeaveResponse:
    s = lr.student
    return LeaveResponse(
        id=lr.id,
        student_id=lr.student_id,
        student_name=_student_name(s) if s else "Unknown",
        roll_number=s.roll_number if s else "",
        reason=lr.reason,
        destination=lr.destination,
        from_date=lr.from_date,
        to_date=lr.to_date,
        parent_name=lr.parent_name,
        parent_contact=lr.parent_contact,
        parent_relation=lr.parent_relation,
        status=lr.status,
        reviewed_by=lr.reviewed_by,
        reviewer_name=lr.reviewer.full_name if lr.reviewer else None,
        reviewed_at=lr.reviewed_at,
        warden_remarks=lr.warden_remarks,
        requested_at=lr.requested_at,
    )


def _visitor_response(v: VisitorLog) -> VisitorResponse:
    s = v.student
    return VisitorResponse(
        id=v.id,
        student_id=v.student_id,
        student_name=_student_name(s) if s else "Unknown",
        roll_number=s.roll_number if s else "",
        visitor_name=v.visitor_name,
        visitor_relation=v.visitor_relation,
        visitor_phone=v.visitor_phone,
        visitor_id_type=v.visitor_id_type,
        visitor_id_number=v.visitor_id_number,
        purpose=v.purpose,
        check_in_time=v.check_in_time,
        check_out_time=v.check_out_time,
        logged_by=v.logged_by,
        logger_name=v.logger.full_name if v.logger else "Unknown",
        notes=v.notes,
        created_at=v.created_at,
    )


# ── Hostel CRUD ────────────────────────────────────────────────────────────────

async def create_hostel(db: AsyncSession, data: HostelCreate) -> HostelResponse:
    hostel = Hostel(**data.model_dump())
    db.add(hostel)
    await db.commit()
    await db.refresh(hostel)
    # load warden
    await db.execute(select(Hostel).where(Hostel.id == hostel.id).options(selectinload(Hostel.warden)))
    result = await db.execute(
        select(Hostel).where(Hostel.id == hostel.id).options(selectinload(Hostel.warden))
    )
    hostel = result.scalar_one()
    return _hostel_response(hostel)


async def list_hostels(db: AsyncSession) -> list[HostelResponse]:
    result = await db.execute(
        select(Hostel).options(selectinload(Hostel.warden)).order_by(Hostel.name)
    )
    return [_hostel_response(h) for h in result.scalars().all()]


async def get_hostel(db: AsyncSession, hostel_id: uuid.UUID) -> HostelResponse:
    result = await db.execute(
        select(Hostel).where(Hostel.id == hostel_id).options(selectinload(Hostel.warden))
    )
    hostel = result.scalar_one_or_none()
    if not hostel:
        raise HTTPException(status_code=404, detail="Hostel not found")
    return _hostel_response(hostel)


async def update_hostel(db: AsyncSession, hostel_id: uuid.UUID, data: HostelUpdate) -> HostelResponse:
    result = await db.execute(select(Hostel).where(Hostel.id == hostel_id))
    hostel = result.scalar_one_or_none()
    if not hostel:
        raise HTTPException(status_code=404, detail="Hostel not found")
    for k, v in data.model_dump(exclude_none=True).items():
        setattr(hostel, k, v)
    await db.commit()
    result = await db.execute(
        select(Hostel).where(Hostel.id == hostel_id).options(selectinload(Hostel.warden))
    )
    return _hostel_response(result.scalar_one())


# ── Room CRUD ──────────────────────────────────────────────────────────────────

async def create_room(db: AsyncSession, hostel_id: uuid.UUID, data: RoomCreate) -> RoomResponse:
    result = await db.execute(select(Hostel).where(Hostel.id == hostel_id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Hostel not found")
    room = HostelRoom(hostel_id=hostel_id, **data.model_dump())
    db.add(room)
    await db.commit()
    await db.refresh(room)
    occ = await _room_occupancy(db, room.id)
    resp = RoomResponse.model_validate(room)
    resp.current_occupancy = occ
    return resp


async def list_rooms(db: AsyncSession, hostel_id: uuid.UUID) -> list[RoomResponse]:
    result = await db.execute(
        select(HostelRoom).where(HostelRoom.hostel_id == hostel_id).order_by(
            HostelRoom.floor, HostelRoom.room_number
        )
    )
    rooms = result.scalars().all()
    out = []
    for r in rooms:
        occ = await _room_occupancy(db, r.id)
        resp = RoomResponse.model_validate(r)
        resp.current_occupancy = occ
        out.append(resp)
    return out


async def update_room(
    db: AsyncSession, hostel_id: uuid.UUID, room_id: uuid.UUID, data: RoomUpdate
) -> RoomResponse:
    result = await db.execute(
        select(HostelRoom).where(HostelRoom.id == room_id, HostelRoom.hostel_id == hostel_id)
    )
    room = result.scalar_one_or_none()
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    for k, v in data.model_dump(exclude_none=True).items():
        setattr(room, k, v)
    await db.commit()
    await db.refresh(room)
    occ = await _room_occupancy(db, room.id)
    resp = RoomResponse.model_validate(room)
    resp.current_occupancy = occ
    return resp


# ── Allocation ─────────────────────────────────────────────────────────────────

async def allocate_room(
    db: AsyncSession, data: AllocationCreate, allocated_by: uuid.UUID
) -> AllocationResponse:
    # Check room exists and has space
    room_result = await db.execute(
        select(HostelRoom)
        .where(HostelRoom.id == data.room_id, HostelRoom.is_active == True)
        .options(selectinload(HostelRoom.hostel))
    )
    room = room_result.scalar_one_or_none()
    if not room:
        raise HTTPException(status_code=404, detail="Room not found or inactive")

    occ = await _room_occupancy(db, room.id)
    if occ >= room.capacity:
        raise HTTPException(status_code=409, detail="Room is at full capacity")

    # Check student doesn't already have active allocation
    existing = await db.execute(
        select(HostelAllocation).where(
            HostelAllocation.student_id == data.student_id,
            HostelAllocation.is_active == True,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Student already has an active room allocation")

    student = await _get_student(db, data.student_id)

    alloc = HostelAllocation(
        student_id=data.student_id,
        room_id=data.room_id,
        allocated_date=data.allocated_date,
        is_active=True,
        allocated_by=allocated_by,
        notes=data.notes,
    )
    db.add(alloc)
    await db.commit()
    await db.refresh(alloc)

    return AllocationResponse(
        id=alloc.id,
        student_id=alloc.student_id,
        student_name=_student_name(student),
        roll_number=student.roll_number,
        room_id=room.id,
        room_number=room.room_number,
        hostel_name=room.hostel.name,
        allocated_date=alloc.allocated_date,
        vacated_date=alloc.vacated_date,
        is_active=alloc.is_active,
        notes=alloc.notes,
        created_at=alloc.created_at,
    )


async def vacate_room(
    db: AsyncSession, allocation_id: uuid.UUID, vacated_date: date
) -> AllocationResponse:
    result = await db.execute(
        select(HostelAllocation)
        .where(HostelAllocation.id == allocation_id)
        .options(
            selectinload(HostelAllocation.student).selectinload(Student.user),
            selectinload(HostelAllocation.room).selectinload(HostelRoom.hostel),
        )
    )
    alloc = result.scalar_one_or_none()
    if not alloc:
        raise HTTPException(status_code=404, detail="Allocation not found")
    if not alloc.is_active:
        raise HTTPException(status_code=400, detail="Allocation is already vacated")

    alloc.is_active = False
    alloc.vacated_date = vacated_date
    await db.commit()
    await db.refresh(alloc)

    return AllocationResponse(
        id=alloc.id,
        student_id=alloc.student_id,
        student_name=_student_name(alloc.student),
        roll_number=alloc.student.roll_number,
        room_id=alloc.room.id,
        room_number=alloc.room.room_number,
        hostel_name=alloc.room.hostel.name,
        allocated_date=alloc.allocated_date,
        vacated_date=alloc.vacated_date,
        is_active=alloc.is_active,
        notes=alloc.notes,
        created_at=alloc.created_at,
    )


async def list_allocations(
    db: AsyncSession,
    hostel_id: Optional[uuid.UUID] = None,
    active_only: bool = True,
) -> list[AllocationResponse]:
    q = (
        select(HostelAllocation)
        .options(
            selectinload(HostelAllocation.student).selectinload(Student.user),
            selectinload(HostelAllocation.room).selectinload(HostelRoom.hostel),
        )
    )
    if active_only:
        q = q.where(HostelAllocation.is_active == True)
    if hostel_id:
        q = q.join(HostelRoom).where(HostelRoom.hostel_id == hostel_id)
    rows = (await db.execute(q)).scalars().all()
    return [
        AllocationResponse(
            id=a.id,
            student_id=a.student_id,
            student_name=_student_name(a.student),
            roll_number=a.student.roll_number,
            room_id=a.room.id,
            room_number=a.room.room_number,
            hostel_name=a.room.hostel.name,
            allocated_date=a.allocated_date,
            vacated_date=a.vacated_date,
            is_active=a.is_active,
            notes=a.notes,
            created_at=a.created_at,
        )
        for a in rows
    ]


# ── Outpass ────────────────────────────────────────────────────────────────────

async def apply_outpass(
    db: AsyncSession, student_id: uuid.UUID, data: OutpassCreate
) -> OutpassResponse:
    if data.from_datetime >= data.to_datetime:
        raise HTTPException(status_code=400, detail="from_datetime must be before to_datetime")

    student = await _get_student(db, student_id)
    op = Outpass(student_id=student_id, **data.model_dump())
    db.add(op)
    await db.commit()
    await db.execute(
        select(Outpass)
        .where(Outpass.id == op.id)
        .options(
            selectinload(Outpass.student).selectinload(Student.user),
            selectinload(Outpass.reviewer),
        )
    )
    result = await db.execute(
        select(Outpass)
        .where(Outpass.id == op.id)
        .options(
            selectinload(Outpass.student).selectinload(Student.user),
            selectinload(Outpass.reviewer),
        )
    )
    return _outpass_response(result.scalar_one())


async def review_outpass(
    db: AsyncSession, outpass_id: uuid.UUID, reviewer_id: uuid.UUID, review: OutpassReview
) -> OutpassResponse:
    result = await db.execute(
        select(Outpass)
        .where(Outpass.id == outpass_id)
        .options(
            selectinload(Outpass.student).selectinload(Student.user),
            selectinload(Outpass.reviewer),
        )
    )
    op = result.scalar_one_or_none()
    if not op:
        raise HTTPException(status_code=404, detail="Outpass not found")
    if op.status != OutpassStatus.pending:
        raise HTTPException(status_code=400, detail=f"Cannot review — current status: {op.status.value}")

    op.status = OutpassStatus.approved if review.action == "approve" else OutpassStatus.rejected
    op.reviewed_by = reviewer_id
    op.reviewed_at = _now()
    op.warden_remarks = review.remarks
    await db.commit()

    result = await db.execute(
        select(Outpass)
        .where(Outpass.id == outpass_id)
        .options(
            selectinload(Outpass.student).selectinload(Student.user),
            selectinload(Outpass.reviewer),
        )
    )
    return _outpass_response(result.scalar_one())


async def mark_outpass_checkout(db: AsyncSession, outpass_id: uuid.UUID) -> OutpassResponse:
    result = await db.execute(
        select(Outpass)
        .where(Outpass.id == outpass_id)
        .options(
            selectinload(Outpass.student).selectinload(Student.user),
            selectinload(Outpass.reviewer),
        )
    )
    op = result.scalar_one_or_none()
    if not op:
        raise HTTPException(status_code=404, detail="Outpass not found")
    if op.status != OutpassStatus.approved:
        raise HTTPException(status_code=400, detail="Outpass must be approved before checkout")
    op.status = OutpassStatus.checked_out
    await db.commit()
    result = await db.execute(
        select(Outpass)
        .where(Outpass.id == outpass_id)
        .options(
            selectinload(Outpass.student).selectinload(Student.user),
            selectinload(Outpass.reviewer),
        )
    )
    return _outpass_response(result.scalar_one())


async def mark_outpass_returned(db: AsyncSession, outpass_id: uuid.UUID) -> OutpassResponse:
    result = await db.execute(
        select(Outpass)
        .where(Outpass.id == outpass_id)
        .options(
            selectinload(Outpass.student).selectinload(Student.user),
            selectinload(Outpass.reviewer),
        )
    )
    op = result.scalar_one_or_none()
    if not op:
        raise HTTPException(status_code=404, detail="Outpass not found")
    if op.status != OutpassStatus.checked_out:
        raise HTTPException(status_code=400, detail="Student has not checked out yet")
    op.status = OutpassStatus.returned
    await db.commit()
    result = await db.execute(
        select(Outpass)
        .where(Outpass.id == outpass_id)
        .options(
            selectinload(Outpass.student).selectinload(Student.user),
            selectinload(Outpass.reviewer),
        )
    )
    return _outpass_response(result.scalar_one())


async def list_outpasses(
    db: AsyncSession,
    student_id: Optional[uuid.UUID] = None,
    status: Optional[OutpassStatus] = None,
    hostel_id: Optional[uuid.UUID] = None,
    limit: int = 50,
) -> list[OutpassResponse]:
    q = (
        select(Outpass)
        .options(
            selectinload(Outpass.student).selectinload(Student.user),
            selectinload(Outpass.reviewer),
        )
        .order_by(Outpass.requested_at.desc())
        .limit(limit)
    )
    if student_id:
        q = q.where(Outpass.student_id == student_id)
    if status:
        q = q.where(Outpass.status == status)
    if hostel_id:
        # filter by hostel via allocation
        q = q.join(
            HostelAllocation,
            (HostelAllocation.student_id == Outpass.student_id) & (HostelAllocation.is_active == True),
        ).join(
            HostelRoom, HostelAllocation.room_id == HostelRoom.id
        ).where(HostelRoom.hostel_id == hostel_id)
    rows = (await db.execute(q)).scalars().all()
    return [_outpass_response(op) for op in rows]


# ── Hostel Leave ───────────────────────────────────────────────────────────────

async def apply_leave(
    db: AsyncSession, student_id: uuid.UUID, data: LeaveCreate
) -> LeaveResponse:
    if data.from_date > data.to_date:
        raise HTTPException(status_code=400, detail="from_date must be on or before to_date")

    student = await _get_student(db, student_id)
    lr = HostelLeaveRequest(student_id=student_id, **data.model_dump())
    db.add(lr)
    await db.commit()
    result = await db.execute(
        select(HostelLeaveRequest)
        .where(HostelLeaveRequest.id == lr.id)
        .options(
            selectinload(HostelLeaveRequest.student).selectinload(Student.user),
            selectinload(HostelLeaveRequest.reviewer),
        )
    )
    return _leave_response(result.scalar_one())


async def review_leave(
    db: AsyncSession, leave_id: uuid.UUID, reviewer_id: uuid.UUID, review: LeaveReview
) -> LeaveResponse:
    result = await db.execute(
        select(HostelLeaveRequest)
        .where(HostelLeaveRequest.id == leave_id)
        .options(
            selectinload(HostelLeaveRequest.student).selectinload(Student.user),
            selectinload(HostelLeaveRequest.reviewer),
        )
    )
    lr = result.scalar_one_or_none()
    if not lr:
        raise HTTPException(status_code=404, detail="Leave request not found")
    if lr.status != HostelLeaveStatus.pending:
        raise HTTPException(status_code=400, detail=f"Cannot review — current status: {lr.status.value}")

    lr.status = HostelLeaveStatus.approved if review.action == "approve" else HostelLeaveStatus.rejected
    lr.reviewed_by = reviewer_id
    lr.reviewed_at = _now()
    lr.warden_remarks = review.remarks
    await db.commit()

    result = await db.execute(
        select(HostelLeaveRequest)
        .where(HostelLeaveRequest.id == leave_id)
        .options(
            selectinload(HostelLeaveRequest.student).selectinload(Student.user),
            selectinload(HostelLeaveRequest.reviewer),
        )
    )
    return _leave_response(result.scalar_one())


async def list_leaves(
    db: AsyncSession,
    student_id: Optional[uuid.UUID] = None,
    status: Optional[HostelLeaveStatus] = None,
    hostel_id: Optional[uuid.UUID] = None,
    limit: int = 50,
) -> list[LeaveResponse]:
    q = (
        select(HostelLeaveRequest)
        .options(
            selectinload(HostelLeaveRequest.student).selectinload(Student.user),
            selectinload(HostelLeaveRequest.reviewer),
        )
        .order_by(HostelLeaveRequest.requested_at.desc())
        .limit(limit)
    )
    if student_id:
        q = q.where(HostelLeaveRequest.student_id == student_id)
    if status:
        q = q.where(HostelLeaveRequest.status == status)
    if hostel_id:
        q = q.join(
            HostelAllocation,
            (HostelAllocation.student_id == HostelLeaveRequest.student_id)
            & (HostelAllocation.is_active == True),
        ).join(
            HostelRoom, HostelAllocation.room_id == HostelRoom.id
        ).where(HostelRoom.hostel_id == hostel_id)
    rows = (await db.execute(q)).scalars().all()
    return [_leave_response(lr) for lr in rows]


# ── Visitor Log ────────────────────────────────────────────────────────────────

async def log_visitor(
    db: AsyncSession, data: VisitorCreate, logged_by: uuid.UUID
) -> VisitorResponse:
    await _get_student(db, data.student_id)
    v = VisitorLog(
        logged_by=logged_by,
        check_in_time=_now(),
        **data.model_dump(),
    )
    db.add(v)
    await db.commit()
    result = await db.execute(
        select(VisitorLog)
        .where(VisitorLog.id == v.id)
        .options(
            selectinload(VisitorLog.student).selectinload(Student.user),
            selectinload(VisitorLog.logger),
        )
    )
    return _visitor_response(result.scalar_one())


async def checkout_visitor(db: AsyncSession, visitor_id: uuid.UUID) -> VisitorResponse:
    result = await db.execute(
        select(VisitorLog)
        .where(VisitorLog.id == visitor_id)
        .options(
            selectinload(VisitorLog.student).selectinload(Student.user),
            selectinload(VisitorLog.logger),
        )
    )
    v = result.scalar_one_or_none()
    if not v:
        raise HTTPException(status_code=404, detail="Visitor log not found")
    if v.check_out_time:
        raise HTTPException(status_code=400, detail="Visitor has already checked out")
    v.check_out_time = _now()
    await db.commit()
    result = await db.execute(
        select(VisitorLog)
        .where(VisitorLog.id == visitor_id)
        .options(
            selectinload(VisitorLog.student).selectinload(Student.user),
            selectinload(VisitorLog.logger),
        )
    )
    return _visitor_response(result.scalar_one())


async def list_visitors(
    db: AsyncSession,
    hostel_id: uuid.UUID,
    today_only: bool = False,
    limit: int = 100,
) -> list[VisitorResponse]:
    q = (
        select(VisitorLog)
        .join(
            HostelAllocation,
            (HostelAllocation.student_id == VisitorLog.student_id)
            & (HostelAllocation.is_active == True),
        )
        .join(HostelRoom, HostelAllocation.room_id == HostelRoom.id)
        .where(HostelRoom.hostel_id == hostel_id)
        .options(
            selectinload(VisitorLog.student).selectinload(Student.user),
            selectinload(VisitorLog.logger),
        )
        .order_by(VisitorLog.check_in_time.desc())
        .limit(limit)
    )
    if today_only:
        from sqlalchemy import cast, Date as SADate
        today = _now().date()
        q = q.where(cast(VisitorLog.check_in_time, SADate) == today)
    rows = (await db.execute(q)).scalars().all()
    return [_visitor_response(v) for v in rows]


# ── Warden Dashboard ───────────────────────────────────────────────────────────

async def warden_dashboard(db: AsyncSession, hostel_id: uuid.UUID) -> WardenDashboard:
    hostel_result = await db.execute(
        select(Hostel).where(Hostel.id == hostel_id).options(selectinload(Hostel.warden))
    )
    hostel = hostel_result.scalar_one_or_none()
    if not hostel:
        raise HTTPException(status_code=404, detail="Hostel not found")

    # Occupancy
    occ_result = await db.execute(
        select(func.count(HostelAllocation.id))
        .join(HostelRoom)
        .where(
            HostelRoom.hostel_id == hostel_id,
            HostelAllocation.is_active == True,
        )
    )
    occupancy = occ_result.scalar() or 0

    # Pending outpasses for this hostel
    pending_op = await db.execute(
        select(func.count(Outpass.id))
        .join(
            HostelAllocation,
            (HostelAllocation.student_id == Outpass.student_id) & (HostelAllocation.is_active == True),
        )
        .join(HostelRoom, HostelAllocation.room_id == HostelRoom.id)
        .where(HostelRoom.hostel_id == hostel_id, Outpass.status == OutpassStatus.pending)
    )
    pending_outpasses = pending_op.scalar() or 0

    # Pending leaves
    pending_lv = await db.execute(
        select(func.count(HostelLeaveRequest.id))
        .join(
            HostelAllocation,
            (HostelAllocation.student_id == HostelLeaveRequest.student_id)
            & (HostelAllocation.is_active == True),
        )
        .join(HostelRoom, HostelAllocation.room_id == HostelRoom.id)
        .where(HostelRoom.hostel_id == hostel_id, HostelLeaveRequest.status == HostelLeaveStatus.pending)
    )
    pending_leaves = pending_lv.scalar() or 0

    # Today's visitors
    from sqlalchemy import cast, Date as SADate
    today = _now().date()
    today_vis = await db.execute(
        select(func.count(VisitorLog.id))
        .join(
            HostelAllocation,
            (HostelAllocation.student_id == VisitorLog.student_id) & (HostelAllocation.is_active == True),
        )
        .join(HostelRoom, HostelAllocation.room_id == HostelRoom.id)
        .where(
            HostelRoom.hostel_id == hostel_id,
            cast(VisitorLog.check_in_time, SADate) == today,
        )
    )
    todays_visitors = today_vis.scalar() or 0

    recent_outpasses = await list_outpasses(db, hostel_id=hostel_id,
                                             status=OutpassStatus.pending, limit=10)
    recent_leaves = await list_leaves(db, hostel_id=hostel_id,
                                       status=HostelLeaveStatus.pending, limit=10)

    return WardenDashboard(
        hostel_id=hostel.id,
        hostel_name=hostel.name,
        total_capacity=hostel.total_capacity,
        current_occupancy=occupancy,
        available_beds=max(hostel.total_capacity - occupancy, 0),
        pending_outpasses=pending_outpasses,
        pending_leaves=pending_leaves,
        todays_visitors=todays_visitors,
        recent_outpasses=recent_outpasses,
        recent_leaves=recent_leaves,
    )
