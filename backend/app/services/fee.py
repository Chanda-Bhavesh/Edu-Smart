"""
Fee Management service.

Admin flow:
  create fee structure → assign to all students in semester →
  record payments → apply waivers → view collection report

Student flow:
  view my fees → view payment history → download receipt
"""
import uuid
from datetime import date, datetime, timezone
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.department import Department
from app.models.faculty import Faculty
from app.models.fee import FeePayment, FeeStatus, FeeStructure, StudentFee
from app.models.semester import Semester
from app.models.student import Student
from app.models.user import User
from app.schemas.fee import (
    ApplyWaiver, FeeCollectionSummary, FeeStructureCreate,
    FeeStructureUpdate, RecordPayment,
    StudentFeeDetail, StudentFeeSummary,
)
from app.utils.receipt import generate_fee_receipt


# ── helpers ────────────────────────────────────────────────────────────────────

def _today() -> date:
    return datetime.now(timezone.utc).date()


def _generate_receipt_number() -> str:
    from datetime import datetime
    ts = datetime.now(timezone.utc)
    rand = uuid.uuid4().hex[:6].upper()
    return f"RCP-{ts.year}-{rand}"


async def _get_student_fee(db: AsyncSession, student_fee_id: uuid.UUID) -> StudentFee:
    result = await db.execute(
        select(StudentFee)
        .where(StudentFee.id == student_fee_id)
        .options(selectinload(StudentFee.fee_structure))
    )
    sf = result.scalar_one_or_none()
    if not sf:
        raise HTTPException(status_code=404, detail="Student fee record not found")
    return sf


def _recompute_student_fee(sf: StudentFee, structure: FeeStructure) -> None:
    """Recalculate net_amount and balance from current fields."""
    sf.net_amount = float(sf.total_amount) - float(sf.discount_amount) + float(sf.fine_amount)
    sf.balance = max(float(sf.net_amount) - float(sf.amount_paid), 0)

    if float(sf.balance) == 0 and float(sf.amount_paid) > 0:
        sf.status = FeeStatus.paid
    elif float(sf.amount_paid) > 0:
        sf.status = FeeStatus.partial
    elif _today() > sf.due_date:
        sf.status = FeeStatus.overdue
    else:
        sf.status = FeeStatus.pending


def _apply_daily_fine(sf: StudentFee, structure: FeeStructure) -> None:
    """Add late fine if past due date and still unpaid."""
    if _today() <= sf.due_date:
        return
    if sf.status in (FeeStatus.paid, FeeStatus.waived):
        return
    if float(structure.late_fine_per_day) <= 0:
        return

    days_overdue = (_today() - sf.due_date).days
    computed_fine = round(days_overdue * float(structure.late_fine_per_day), 2)
    if computed_fine > float(sf.fine_amount):
        sf.fine_amount = computed_fine
        _recompute_student_fee(sf, structure)


# ── Fee Structure CRUD ─────────────────────────────────────────────────────────

async def create_fee_structure(
    db: AsyncSession,
    payload: FeeStructureCreate,
    user_id: uuid.UUID,
) -> FeeStructure:
    total = (
        payload.tuition_fee + payload.exam_fee
        + payload.library_fee + payload.lab_fee + payload.other_fee
    )
    if total <= 0:
        raise HTTPException(status_code=400, detail="Total fee must be greater than zero")

    # Check uniqueness
    existing = await db.execute(
        select(FeeStructure).where(
            FeeStructure.department_id == payload.department_id,
            FeeStructure.semester_id == payload.semester_id,
            FeeStructure.academic_year == payload.academic_year,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=400,
            detail="A fee structure for this department/semester/year already exists",
        )

    fs = FeeStructure(
        department_id=payload.department_id,
        semester_id=payload.semester_id,
        academic_year=payload.academic_year,
        tuition_fee=payload.tuition_fee,
        exam_fee=payload.exam_fee,
        library_fee=payload.library_fee,
        lab_fee=payload.lab_fee,
        other_fee=payload.other_fee,
        total_fee=total,
        due_date=payload.due_date,
        late_fine_per_day=payload.late_fine_per_day,
        description=payload.description,
        created_by_id=user_id,
    )
    db.add(fs)
    await db.commit()
    await db.refresh(fs)
    return fs


async def update_fee_structure(
    db: AsyncSession,
    fee_structure_id: uuid.UUID,
    payload: FeeStructureUpdate,
    user_id: uuid.UUID,
) -> FeeStructure:
    result = await db.execute(
        select(FeeStructure).where(FeeStructure.id == fee_structure_id)
    )
    fs = result.scalar_one_or_none()
    if not fs:
        raise HTTPException(status_code=404, detail="Fee structure not found")

    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(fs, field, value)

    # Recalculate total
    fs.total_fee = (
        float(fs.tuition_fee) + float(fs.exam_fee)
        + float(fs.library_fee) + float(fs.lab_fee) + float(fs.other_fee)
    )
    await db.commit()
    await db.refresh(fs)
    return fs


async def delete_fee_structure(
    db: AsyncSession,
    fee_structure_id: uuid.UUID,
) -> None:
    result = await db.execute(
        select(FeeStructure).where(FeeStructure.id == fee_structure_id)
    )
    fs = result.scalar_one_or_none()
    if not fs:
        raise HTTPException(status_code=404, detail="Fee structure not found")

    # Block deletion if student fees are attached
    count_result = await db.execute(
        select(func.count(StudentFee.id)).where(StudentFee.fee_structure_id == fee_structure_id)
    )
    if (count_result.scalar() or 0) > 0:
        raise HTTPException(
            status_code=400,
            detail="Cannot delete: students are already assigned to this fee structure",
        )

    await db.delete(fs)
    await db.commit()


async def list_fee_structures(
    db: AsyncSession,
    department_id: Optional[uuid.UUID] = None,
    academic_year: Optional[str] = None,
) -> list[FeeStructure]:
    q = select(FeeStructure)
    if department_id:
        q = q.where(FeeStructure.department_id == department_id)
    if academic_year:
        q = q.where(FeeStructure.academic_year == academic_year)
    q = q.order_by(FeeStructure.created_at.desc())
    result = await db.execute(q)
    return list(result.scalars().all())


# ── Assign fee to students ─────────────────────────────────────────────────────

async def assign_fee_to_students(
    db: AsyncSession,
    fee_structure_id: uuid.UUID,
) -> dict:
    """
    Bulk-create StudentFee records for every active student in the
    semester + department that matches the fee structure.
    Skips students who already have a record for this structure.
    """
    result = await db.execute(
        select(FeeStructure).where(FeeStructure.id == fee_structure_id)
    )
    fs = result.scalar_one_or_none()
    if not fs:
        raise HTTPException(status_code=404, detail="Fee structure not found")

    students_q = await db.execute(
        select(Student).where(
            Student.department_id == fs.department_id,
            Student.semester_id == fs.semester_id,
        )
    )
    students = students_q.scalars().all()

    created = 0
    skipped = 0
    for student in students:
        # Check if already assigned
        exists = await db.execute(
            select(StudentFee).where(
                StudentFee.student_id == student.id,
                StudentFee.fee_structure_id == fee_structure_id,
            )
        )
        if exists.scalar_one_or_none():
            skipped += 1
            continue

        net = float(fs.total_fee)
        sf = StudentFee(
            student_id=student.id,
            fee_structure_id=fee_structure_id,
            total_amount=fs.total_fee,
            discount_amount=0,
            fine_amount=0,
            net_amount=net,
            amount_paid=0,
            balance=net,
            status=FeeStatus.pending,
            due_date=fs.due_date,
        )
        db.add(sf)
        created += 1

    await db.commit()
    return {"assigned": created, "skipped_already_assigned": skipped, "total_students": len(students)}


# ── Record Payment ─────────────────────────────────────────────────────────────

async def record_payment(
    db: AsyncSession,
    student_fee_id: uuid.UUID,
    payload: RecordPayment,
    user_id: uuid.UUID,
) -> FeePayment:
    sf = await _get_student_fee(db, student_fee_id)
    structure = sf.fee_structure

    if sf.status == FeeStatus.waived:
        raise HTTPException(status_code=400, detail="Fee has been waived — no payment needed")
    if sf.status == FeeStatus.paid:
        raise HTTPException(status_code=400, detail="Fee is already fully paid")

    # Apply any pending fine before recording payment
    _apply_daily_fine(sf, structure)

    if payload.amount > float(sf.balance):
        raise HTTPException(
            status_code=400,
            detail=f"Amount exceeds outstanding balance of ₹{sf.balance:,.2f}",
        )

    # Generate unique receipt number
    receipt_number = _generate_receipt_number()
    # Very unlikely collision but guard anyway
    while True:
        existing = await db.execute(
            select(FeePayment).where(FeePayment.receipt_number == receipt_number)
        )
        if not existing.scalar_one_or_none():
            break
        receipt_number = _generate_receipt_number()

    payment = FeePayment(
        student_fee_id=sf.id,
        student_id=sf.student_id,
        amount=payload.amount,
        payment_mode=payload.payment_mode,
        transaction_id=payload.transaction_id,
        payment_date=payload.payment_date,
        receipt_number=receipt_number,
        remarks=payload.remarks,
        recorded_by_id=user_id,
    )
    db.add(payment)

    # Update paid totals
    sf.amount_paid = float(sf.amount_paid) + payload.amount
    _recompute_student_fee(sf, structure)

    await db.commit()
    await db.refresh(payment)
    return payment


# ── Waiver ─────────────────────────────────────────────────────────────────────

async def apply_waiver(
    db: AsyncSession,
    student_fee_id: uuid.UUID,
    payload: ApplyWaiver,
    user_id: uuid.UUID,
) -> StudentFee:
    sf = await _get_student_fee(db, student_fee_id)

    if payload.discount_amount > float(sf.total_amount):
        raise HTTPException(
            status_code=400,
            detail="Discount cannot exceed total fee amount",
        )

    sf.discount_amount = payload.discount_amount
    sf.waiver_reason = payload.reason
    sf.waiver_approved_by_id = user_id

    _recompute_student_fee(sf, sf.fee_structure)

    # If discount covers the full net, mark as waived
    if float(sf.net_amount) <= 0:
        sf.status = FeeStatus.waived
        sf.balance = 0

    await db.commit()
    await db.refresh(sf)
    return sf


# ── Fine recalculation ─────────────────────────────────────────────────────────

async def recalculate_fine(
    db: AsyncSession,
    student_fee_id: uuid.UUID,
) -> StudentFee:
    sf = await _get_student_fee(db, student_fee_id)
    _apply_daily_fine(sf, sf.fee_structure)
    await db.commit()
    await db.refresh(sf)
    return sf


# ── Admin: List all student fees ───────────────────────────────────────────────

async def list_student_fees(
    db: AsyncSession,
    fee_structure_id: Optional[uuid.UUID] = None,
    status_filter: Optional[FeeStatus] = None,
    department_id: Optional[uuid.UUID] = None,
) -> list[StudentFee]:
    q = select(StudentFee).options(
        selectinload(StudentFee.student).selectinload(Student.user),
        selectinload(StudentFee.fee_structure),
    )
    if fee_structure_id:
        q = q.where(StudentFee.fee_structure_id == fee_structure_id)
    if status_filter:
        q = q.where(StudentFee.status == status_filter)
    if department_id:
        q = q.join(FeeStructure).where(FeeStructure.department_id == department_id)
    q = q.order_by(StudentFee.due_date.asc())
    result = await db.execute(q)
    return list(result.scalars().all())


# ── Collection report ──────────────────────────────────────────────────────────

async def get_collection_report(
    db: AsyncSession,
    fee_structure_id: uuid.UUID,
) -> FeeCollectionSummary:
    fs_result = await db.execute(
        select(FeeStructure)
        .where(FeeStructure.id == fee_structure_id)
        .options(
            selectinload(FeeStructure.department),
            selectinload(FeeStructure.semester),
        )
    )
    fs = fs_result.scalar_one_or_none()
    if not fs:
        raise HTTPException(status_code=404, detail="Fee structure not found")

    agg = await db.execute(
        select(
            func.count(StudentFee.id).label("total"),
            func.sum(
                (StudentFee.status == FeeStatus.paid).cast(type_=__import__("sqlalchemy").Integer)
            ).label("paid"),
            func.sum(
                (StudentFee.status == FeeStatus.partial).cast(type_=__import__("sqlalchemy").Integer)
            ).label("partial"),
            func.sum(
                (StudentFee.status == FeeStatus.pending).cast(type_=__import__("sqlalchemy").Integer)
            ).label("pending"),
            func.sum(
                (StudentFee.status == FeeStatus.overdue).cast(type_=__import__("sqlalchemy").Integer)
            ).label("overdue"),
            func.sum(
                (StudentFee.status == FeeStatus.waived).cast(type_=__import__("sqlalchemy").Integer)
            ).label("waived"),
            func.sum(StudentFee.net_amount).label("expected"),
            func.sum(StudentFee.amount_paid).label("collected"),
            func.sum(StudentFee.balance).label("balance"),
        ).where(StudentFee.fee_structure_id == fee_structure_id)
    )
    row = agg.one()

    total = row.total or 0
    collected = float(row.collected or 0)
    expected = float(row.expected or 0)
    pct = (collected / expected * 100) if expected > 0 else 0.0

    return FeeCollectionSummary(
        fee_structure_id=fee_structure_id,
        academic_year=fs.academic_year,
        department_name=fs.department.name if fs.department else "",
        semester_number=fs.semester.number if fs.semester else 0,
        total_students=total,
        paid_count=int(row.paid or 0),
        partial_count=int(row.partial or 0),
        pending_count=int(row.pending or 0),
        overdue_count=int(row.overdue or 0),
        waived_count=int(row.waived or 0),
        total_expected=expected,
        total_collected=collected,
        total_balance=float(row.balance or 0),
        collection_percentage=round(pct, 2),
    )


# ── Student: My fees ───────────────────────────────────────────────────────────

async def get_my_fees(
    db: AsyncSession,
    user_id: uuid.UUID,
) -> StudentFeeSummary:
    student_result = await db.execute(
        select(Student).where(Student.user_id == user_id)
        .options(selectinload(Student.user))
    )
    student = student_result.scalar_one_or_none()
    if not student:
        raise HTTPException(status_code=404, detail="Student profile not found")

    fees_result = await db.execute(
        select(StudentFee)
        .where(StudentFee.student_id == student.id)
        .options(
            selectinload(StudentFee.fee_structure).selectinload(FeeStructure.department),
            selectinload(StudentFee.fee_structure).selectinload(FeeStructure.semester),
        )
        .order_by(StudentFee.due_date.desc())
    )
    fees = fees_result.scalars().all()

    items: list[StudentFeeDetail] = []
    total_paid = 0.0
    total_outstanding = 0.0

    for f in fees:
        detail = StudentFeeDetail.model_validate(f)
        detail.academic_year = f.fee_structure.academic_year
        detail.tuition_fee = float(f.fee_structure.tuition_fee)
        detail.exam_fee = float(f.fee_structure.exam_fee)
        detail.library_fee = float(f.fee_structure.library_fee)
        detail.lab_fee = float(f.fee_structure.lab_fee)
        detail.other_fee = float(f.fee_structure.other_fee)
        if f.fee_structure.department:
            detail.department_name = f.fee_structure.department.name
        if f.fee_structure.semester:
            detail.semester_number = f.fee_structure.semester.number
        items.append(detail)
        total_paid += float(f.amount_paid)
        total_outstanding += float(f.balance)

    return StudentFeeSummary(
        student_id=student.id,
        student_name=f"{student.user.first_name} {student.user.last_name}",
        roll_number=student.roll_number,
        fees=items,
        total_paid_ever=total_paid,
        total_outstanding=total_outstanding,
    )


async def get_student_fee_payments(
    db: AsyncSession,
    student_fee_id: uuid.UUID,
    user_id: uuid.UUID,
    is_admin: bool = False,
) -> list[FeePayment]:
    sf = await _get_student_fee(db, student_fee_id)

    if not is_admin:
        # Verify it belongs to this student
        student_result = await db.execute(
            select(Student).where(Student.user_id == user_id)
        )
        student = student_result.scalar_one_or_none()
        if not student or sf.student_id != student.id:
            raise HTTPException(status_code=403, detail="Not your fee record")

    result = await db.execute(
        select(FeePayment)
        .where(FeePayment.student_fee_id == student_fee_id)
        .order_by(FeePayment.payment_date.asc())
    )
    return list(result.scalars().all())


# ── Receipt PDF ────────────────────────────────────────────────────────────────

async def get_receipt_pdf(
    db: AsyncSession,
    payment_id: uuid.UUID,
    user_id: uuid.UUID,
    is_admin: bool = False,
) -> bytes:
    result = await db.execute(
        select(FeePayment)
        .where(FeePayment.id == payment_id)
        .options(
            selectinload(FeePayment.student_fee)
            .selectinload(StudentFee.fee_structure)
            .selectinload(FeeStructure.department),
            selectinload(FeePayment.student_fee)
            .selectinload(StudentFee.fee_structure)
            .selectinload(FeeStructure.semester),
            selectinload(FeePayment.student)
            .selectinload(Student.user),
        )
    )
    payment = result.scalar_one_or_none()
    if not payment:
        raise HTTPException(status_code=404, detail="Payment record not found")

    if not is_admin:
        student_result = await db.execute(
            select(Student).where(Student.user_id == user_id)
        )
        student = student_result.scalar_one_or_none()
        if not student or payment.student_id != student.id:
            raise HTTPException(status_code=403, detail="Not your receipt")

    sf = payment.student_fee
    fs = sf.fee_structure
    stu = payment.student
    user = stu.user

    # All previous payments before this one
    prev_result = await db.execute(
        select(func.sum(FeePayment.amount)).where(
            FeePayment.student_fee_id == sf.id,
            FeePayment.id != payment_id,
            FeePayment.created_at < payment.created_at,
        )
    )
    prev_paid = float(prev_result.scalar() or 0)
    balance_after = max(float(sf.net_amount) - (prev_paid + float(payment.amount)), 0)

    pdf_bytes = generate_fee_receipt(
        receipt_number=payment.receipt_number,
        student_name=f"{user.first_name} {user.last_name}",
        roll_number=stu.roll_number,
        department=fs.department.name if fs.department else "N/A",
        semester=f"Semester {fs.semester.number}" if fs.semester else "N/A",
        academic_year=fs.academic_year,
        payment_date=payment.payment_date,
        payment_mode=payment.payment_mode.value,
        transaction_id=payment.transaction_id,
        amount_paid=float(payment.amount),
        total_fee=float(fs.total_fee),
        discount=float(sf.discount_amount),
        fine=float(sf.fine_amount),
        net_amount=float(sf.net_amount),
        previous_paid=prev_paid,
        balance_after=balance_after,
        fee_breakdown={
            "Tuition Fee": float(fs.tuition_fee),
            "Exam Fee": float(fs.exam_fee),
            "Library Fee": float(fs.library_fee),
            "Lab Fee": float(fs.lab_fee),
            "Other Fee": float(fs.other_fee),
        },
        status=sf.status.value,
    )
    return pdf_bytes
