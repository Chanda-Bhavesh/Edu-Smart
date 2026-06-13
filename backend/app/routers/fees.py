"""
Fee Management endpoints.

Admin:
  POST   /fee-structures                          → create fee structure
  GET    /fee-structures                          → list all structures
  GET    /fee-structures/{id}                     → get one structure
  PUT    /fee-structures/{id}                     → update structure
  DELETE /fee-structures/{id}                     → delete (if no students assigned)
  POST   /fee-structures/{id}/assign              → bulk-assign to all students in semester
  GET    /fee-structures/{id}/report              → collection report

  GET    /student-fees                            → list all student fee records
  GET    /student-fees/{id}                       → get one student fee record
  PUT    /student-fees/{id}/waiver                → apply discount/waiver
  PUT    /student-fees/{id}/recalculate-fine      → recalculate late fine
  POST   /student-fees/{id}/payment              → record a payment
  GET    /student-fees/{id}/payments             → list all payments for a record

  GET    /fee-payments/{id}/receipt              → download PDF receipt

Student:
  GET    /fees/my                                 → view all my fee records + summary
  GET    /fees/my/{student_fee_id}/payments       → view my payment history
  GET    /fee-payments/{id}/receipt              → download my receipt
"""
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies.auth import (
    get_current_admin, get_current_student, get_current_user,
)
from app.models.fee import FeeStatus
from app.models.user import User
from app.schemas.fee import (
    ApplyWaiver, FeeCollectionSummary, FeePaymentResponse,
    FeeStructureCreate, FeeStructureResponse, FeeStructureUpdate,
    RecordPayment, StudentFeeResponse, StudentFeeSummary,
)
from app.services import fee as fee_service

# ── Fee Structures router ──────────────────────────────────────────────────────
fs_router = APIRouter(prefix="/fee-structures", tags=["Fee Management"])


@fs_router.post("", response_model=FeeStructureResponse, status_code=status.HTTP_201_CREATED)
async def create_fee_structure(
    payload: FeeStructureCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    """Admin: define the fee components for a department + semester + academic year."""
    return await fee_service.create_fee_structure(db, payload, current_user.id)


@fs_router.get("", response_model=list[FeeStructureResponse])
async def list_fee_structures(
    department_id: Optional[uuid.UUID] = Query(default=None),
    academic_year: Optional[str] = Query(default=None),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    """Admin: list all fee structures (filter by department or academic year)."""
    return await fee_service.list_fee_structures(db, department_id, academic_year)


@fs_router.get("/{fee_structure_id}", response_model=FeeStructureResponse)
async def get_fee_structure(
    fee_structure_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    """Admin: get a single fee structure."""
    from sqlalchemy import select
    from app.models.fee import FeeStructure
    result = await db.execute(
        select(FeeStructure).where(FeeStructure.id == fee_structure_id)
    )
    fs = result.scalar_one_or_none()
    if not fs:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Fee structure not found")
    return fs


@fs_router.put("/{fee_structure_id}", response_model=FeeStructureResponse)
async def update_fee_structure(
    fee_structure_id: uuid.UUID,
    payload: FeeStructureUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    """Admin: update fee amounts, due date, or fine rate."""
    return await fee_service.update_fee_structure(db, fee_structure_id, payload, current_user.id)


@fs_router.delete("/{fee_structure_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_fee_structure(
    fee_structure_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    """Admin: delete a fee structure (only if no students are assigned yet)."""
    await fee_service.delete_fee_structure(db, fee_structure_id)


@fs_router.post("/{fee_structure_id}/assign")
async def assign_to_students(
    fee_structure_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    """
    Admin: bulk-assign this fee structure to every student
    in the matching department + semester.
    """
    return await fee_service.assign_fee_to_students(db, fee_structure_id)


@fs_router.get("/{fee_structure_id}/report", response_model=FeeCollectionSummary)
async def collection_report(
    fee_structure_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    """Admin: see how much has been collected vs expected for a fee structure."""
    return await fee_service.get_collection_report(db, fee_structure_id)


# ── Student Fees router ────────────────────────────────────────────────────────
sf_router = APIRouter(prefix="/student-fees", tags=["Fee Management"])


@sf_router.get("", response_model=list[StudentFeeResponse])
async def list_student_fees(
    fee_structure_id: Optional[uuid.UUID] = Query(default=None),
    status_filter: Optional[FeeStatus] = Query(default=None, alias="status"),
    department_id: Optional[uuid.UUID] = Query(default=None),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    """Admin: list all student fee records (filter by structure, status, or department)."""
    return await fee_service.list_student_fees(db, fee_structure_id, status_filter, department_id)


@sf_router.get("/{student_fee_id}", response_model=StudentFeeResponse)
async def get_student_fee(
    student_fee_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    """Admin: view one student fee record."""
    from sqlalchemy import select
    from app.models.fee import StudentFee
    result = await db.execute(select(StudentFee).where(StudentFee.id == student_fee_id))
    sf = result.scalar_one_or_none()
    if not sf:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Student fee not found")
    return sf


@sf_router.put("/{student_fee_id}/waiver", response_model=StudentFeeResponse)
async def apply_waiver(
    student_fee_id: uuid.UUID,
    payload: ApplyWaiver,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    """Admin: apply a scholarship discount or waiver to a student's fee."""
    return await fee_service.apply_waiver(db, student_fee_id, payload, current_user.id)


@sf_router.put("/{student_fee_id}/recalculate-fine", response_model=StudentFeeResponse)
async def recalculate_fine(
    student_fee_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    """Admin: recalculate and apply late payment fine based on days overdue."""
    return await fee_service.recalculate_fine(db, student_fee_id)


@sf_router.post("/{student_fee_id}/payment", response_model=FeePaymentResponse, status_code=status.HTTP_201_CREATED)
async def record_payment(
    student_fee_id: uuid.UUID,
    payload: RecordPayment,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    """Admin: record a fee payment (cash, online, cheque, or demand draft)."""
    return await fee_service.record_payment(db, student_fee_id, payload, current_user.id)


@sf_router.get("/{student_fee_id}/payments", response_model=list[FeePaymentResponse])
async def get_payments_for_fee(
    student_fee_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    """Admin: view all payment transactions for a student fee record."""
    return await fee_service.get_student_fee_payments(
        db, student_fee_id, current_user.id, is_admin=True
    )


# ── Student-facing router ──────────────────────────────────────────────────────
student_fee_router = APIRouter(prefix="/fees", tags=["Fee Management"])


@student_fee_router.get("/my", response_model=StudentFeeSummary)
async def my_fees(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_student),
):
    """Student: view all my fee records across all semesters with full breakdown."""
    return await fee_service.get_my_fees(db, current_user.id)


@student_fee_router.get("/my/{student_fee_id}/payments", response_model=list[FeePaymentResponse])
async def my_payments(
    student_fee_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_student),
):
    """Student: view payment history for one of my fee records."""
    return await fee_service.get_student_fee_payments(
        db, student_fee_id, current_user.id, is_admin=False
    )


# ── Receipt router (shared: admin + student) ───────────────────────────────────
receipt_router = APIRouter(prefix="/fee-payments", tags=["Fee Management"])


@receipt_router.get("/{payment_id}/receipt")
async def download_receipt(
    payment_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Download a PDF fee receipt for a specific payment.
    Students can only download their own receipts.
    Admins can download any receipt.
    """
    from app.models.user import UserRole
    is_admin = current_user.role in (
        UserRole.dept_admin, UserRole.org_admin
    )
    pdf_bytes = await fee_service.get_receipt_pdf(
        db, payment_id, current_user.id, is_admin=is_admin
    )
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="receipt_{payment_id}.pdf"'
        },
    )
