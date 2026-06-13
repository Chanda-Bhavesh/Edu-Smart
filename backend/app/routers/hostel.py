"""
Hostel Management Endpoints

Setup (org_admin / warden):
  POST   /hostels                              create hostel
  GET    /hostels                              list hostels
  GET    /hostels/{id}                         hostel detail
  PATCH  /hostels/{id}                         update hostel
  POST   /hostels/{id}/rooms                   add room
  GET    /hostels/{id}/rooms                   list rooms
  PATCH  /hostels/{id}/rooms/{room_id}         update room
  POST   /hostels/{id}/allocations             allocate student
  GET    /hostels/{id}/allocations             list allocations
  PATCH  /hostels/allocations/{alloc_id}/vacate vacate student

Outpass (student):
  POST   /hostels/outpass                      apply
  GET    /hostels/outpass/me                   own outpass list

Outpass (warden):
  GET    /hostels/{id}/outpass                 all outpasses for hostel
  PATCH  /hostels/outpass/{id}/review          approve / reject
  PATCH  /hostels/outpass/{id}/checkout        mark checked-out
  PATCH  /hostels/outpass/{id}/return          mark returned

Leave (student):
  POST   /hostels/leave                        apply
  GET    /hostels/leave/me                     own leave list

Leave (warden):
  GET    /hostels/{id}/leave                   all leaves for hostel
  PATCH  /hostels/leave/{id}/review            approve / reject

Visitor (warden):
  POST   /hostels/{id}/visitors                log visitor check-in
  GET    /hostels/{id}/visitors                list visitors
  PATCH  /hostels/visitors/{id}/checkout       log check-out

Dashboard (warden):
  GET    /hostels/{id}/dashboard               warden dashboard
"""
import uuid
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies.auth import (
    get_current_user, get_current_warden, require_role,
)
from app.models.hostel import HostelLeaveStatus, OutpassStatus
from app.models.user import User, UserRole
from app.schemas.hostel import (
    AllocationCreate, AllocationResponse,
    HostelCreate, HostelResponse, HostelUpdate,
    LeaveCreate, LeaveResponse, LeaveReview,
    OutpassCreate, OutpassResponse, OutpassReview,
    RoomCreate, RoomResponse, RoomUpdate,
    VisitorCreate, VisitorResponse, WardenDashboard,
)
from app.services.hostel import (
    allocate_room, apply_leave, apply_outpass,
    checkout_visitor, create_hostel, create_room,
    get_hostel, list_allocations, list_hostels,
    list_leaves, list_outpasses, list_rooms,
    list_visitors, log_visitor, mark_outpass_checkout,
    mark_outpass_returned, review_leave, review_outpass,
    update_hostel, update_room, vacate_room,
    warden_dashboard,
)

router = APIRouter(prefix="/hostels", tags=["Hostel Management"])


# ── Hostel Setup ───────────────────────────────────────────────────────────────

@router.post("", response_model=HostelResponse, status_code=201)
async def create_new_hostel(
    data: HostelCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(UserRole.org_admin)),
):
    return await create_hostel(db, data)


@router.get("", response_model=list[HostelResponse])
async def get_hostels(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return await list_hostels(db)


@router.get("/{hostel_id}", response_model=HostelResponse)
async def get_hostel_detail(
    hostel_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return await get_hostel(db, hostel_id)


@router.patch("/{hostel_id}", response_model=HostelResponse)
async def update_hostel_detail(
    hostel_id: uuid.UUID,
    data: HostelUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(UserRole.org_admin, UserRole.warden)),
):
    return await update_hostel(db, hostel_id, data)


# ── Rooms ──────────────────────────────────────────────────────────────────────

@router.post("/{hostel_id}/rooms", response_model=RoomResponse, status_code=201)
async def add_room(
    hostel_id: uuid.UUID,
    data: RoomCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(UserRole.org_admin, UserRole.warden)),
):
    return await create_room(db, hostel_id, data)


@router.get("/{hostel_id}/rooms", response_model=list[RoomResponse])
async def get_rooms(
    hostel_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return await list_rooms(db, hostel_id)


@router.patch("/{hostel_id}/rooms/{room_id}", response_model=RoomResponse)
async def update_room_detail(
    hostel_id: uuid.UUID,
    room_id: uuid.UUID,
    data: RoomUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(UserRole.org_admin, UserRole.warden)),
):
    return await update_room(db, hostel_id, room_id, data)


# ── Allocations ────────────────────────────────────────────────────────────────

@router.post("/{hostel_id}/allocations", response_model=AllocationResponse, status_code=201)
async def create_allocation(
    hostel_id: uuid.UUID,
    data: AllocationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.org_admin, UserRole.warden)),
):
    return await allocate_room(db, data, current_user.id)


@router.get("/{hostel_id}/allocations", response_model=list[AllocationResponse])
async def get_allocations(
    hostel_id: uuid.UUID,
    active_only: bool = Query(True),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(UserRole.org_admin, UserRole.warden)),
):
    return await list_allocations(db, hostel_id=hostel_id, active_only=active_only)


@router.patch("/allocations/{allocation_id}/vacate", response_model=AllocationResponse)
async def vacate_allocation(
    allocation_id: uuid.UUID,
    vacated_date: date = Query(default=None),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(UserRole.org_admin, UserRole.warden)),
):
    from datetime import date as dt_date
    vd = vacated_date or dt_date.today()
    return await vacate_room(db, allocation_id, vd)


# ── Outpass (student) ──────────────────────────────────────────────────────────

@router.post("/outpass", response_model=OutpassResponse, status_code=201)
async def student_apply_outpass(
    data: OutpassCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.student)),
):
    from sqlalchemy import select
    from app.models.student import Student
    result = await db.execute(select(Student).where(Student.user_id == current_user.id))
    student = result.scalar_one_or_none()
    if not student:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Student profile not found")
    return await apply_outpass(db, student.id, data)


@router.get("/outpass/me", response_model=list[OutpassResponse])
async def student_my_outpasses(
    status: Optional[OutpassStatus] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.student)),
):
    from sqlalchemy import select
    from app.models.student import Student
    result = await db.execute(select(Student).where(Student.user_id == current_user.id))
    student = result.scalar_one_or_none()
    if not student:
        return []
    return await list_outpasses(db, student_id=student.id, status=status)


# ── Outpass (warden) ───────────────────────────────────────────────────────────

@router.get("/{hostel_id}/outpass", response_model=list[OutpassResponse])
async def warden_list_outpasses(
    hostel_id: uuid.UUID,
    status: Optional[OutpassStatus] = Query(None),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_warden),
):
    return await list_outpasses(db, hostel_id=hostel_id, status=status)


@router.patch("/outpass/{outpass_id}/review", response_model=OutpassResponse)
async def warden_review_outpass(
    outpass_id: uuid.UUID,
    review: OutpassReview,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_warden),
):
    return await review_outpass(db, outpass_id, current_user.id, review)


@router.patch("/outpass/{outpass_id}/checkout", response_model=OutpassResponse)
async def warden_checkout_outpass(
    outpass_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_warden),
):
    return await mark_outpass_checkout(db, outpass_id)


@router.patch("/outpass/{outpass_id}/return", response_model=OutpassResponse)
async def warden_return_outpass(
    outpass_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_warden),
):
    return await mark_outpass_returned(db, outpass_id)


# ── Leave (student) ────────────────────────────────────────────────────────────

@router.post("/leave", response_model=LeaveResponse, status_code=201)
async def student_apply_leave(
    data: LeaveCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.student)),
):
    from sqlalchemy import select
    from app.models.student import Student
    result = await db.execute(select(Student).where(Student.user_id == current_user.id))
    student = result.scalar_one_or_none()
    if not student:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Student profile not found")
    return await apply_leave(db, student.id, data)


@router.get("/leave/me", response_model=list[LeaveResponse])
async def student_my_leaves(
    status: Optional[HostelLeaveStatus] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.student)),
):
    from sqlalchemy import select
    from app.models.student import Student
    result = await db.execute(select(Student).where(Student.user_id == current_user.id))
    student = result.scalar_one_or_none()
    if not student:
        return []
    return await list_leaves(db, student_id=student.id, status=status)


# ── Leave (warden) ─────────────────────────────────────────────────────────────

@router.get("/{hostel_id}/leave", response_model=list[LeaveResponse])
async def warden_list_leaves(
    hostel_id: uuid.UUID,
    status: Optional[HostelLeaveStatus] = Query(None),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_warden),
):
    return await list_leaves(db, hostel_id=hostel_id, status=status)


@router.patch("/leave/{leave_id}/review", response_model=LeaveResponse)
async def warden_review_leave(
    leave_id: uuid.UUID,
    review: LeaveReview,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_warden),
):
    return await review_leave(db, leave_id, current_user.id, review)


# ── Visitors ───────────────────────────────────────────────────────────────────

@router.post("/{hostel_id}/visitors", response_model=VisitorResponse, status_code=201)
async def log_new_visitor(
    hostel_id: uuid.UUID,
    data: VisitorCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_warden),
):
    return await log_visitor(db, data, current_user.id)


@router.get("/{hostel_id}/visitors", response_model=list[VisitorResponse])
async def get_visitors(
    hostel_id: uuid.UUID,
    today_only: bool = Query(False),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_warden),
):
    return await list_visitors(db, hostel_id, today_only=today_only)


@router.patch("/visitors/{visitor_id}/checkout", response_model=VisitorResponse)
async def visitor_checkout(
    visitor_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_warden),
):
    return await checkout_visitor(db, visitor_id)


# ── Dashboard ──────────────────────────────────────────────────────────────────

@router.get("/{hostel_id}/dashboard", response_model=WardenDashboard)
async def get_warden_dashboard(
    hostel_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_warden),
):
    return await warden_dashboard(db, hostel_id)
