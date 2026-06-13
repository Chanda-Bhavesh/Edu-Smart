"""
Certificate Management service.

Student flow:
  request certificate → wait for admin approval → download PDF

Admin flow:
  see pending requests → review (approve / reject) → issue (generate PDF)

Public:
  verify certificate by certificate number
"""
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.certificate import (
    CERT_TYPE_CODE, CertificateRequest, CertificateStatus, CertificateType,
)
from app.models.department import Department
from app.models.faculty import Faculty
from app.models.semester import Semester
from app.models.student import Student
from app.models.user import User
from app.schemas.certificate import (
    AdminReview, CertificateRequestAdminView, CertificateVerifyResponse,
    CertificateRequestCreate,
)
from app.utils.certificate_pdf import generate_certificate_pdf
from app.config import settings


CERT_UPLOAD_DIR = Path("uploads/certificates")


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _generate_cert_number(cert_type: CertificateType) -> str:
    year = _now().year
    code = CERT_TYPE_CODE.get(cert_type, "GEN")
    rand = uuid.uuid4().hex[:6].upper()
    return f"CERT-{year}-{code}-{rand}"


async def _load_student_with_relations(db: AsyncSession, user_id: uuid.UUID) -> Student:
    result = await db.execute(
        select(Student)
        .where(Student.user_id == user_id)
        .options(
            selectinload(Student.user),
            selectinload(Student.department),
            selectinload(Student.semester),
        )
    )
    student = result.scalar_one_or_none()
    if not student:
        raise HTTPException(status_code=404, detail="Student profile not found")
    return student


# ── Student: Request ───────────────────────────────────────────────────────────

async def request_certificate(
    db: AsyncSession,
    payload: CertificateRequestCreate,
    user_id: uuid.UUID,
) -> CertificateRequest:
    student = await _load_student_with_relations(db, user_id)

    # Prevent duplicate pending requests of the same type
    existing = await db.execute(
        select(CertificateRequest).where(
            CertificateRequest.student_id == student.id,
            CertificateRequest.certificate_type == payload.certificate_type,
            CertificateRequest.status.in_([
                CertificateStatus.pending,
                CertificateStatus.under_review,
                CertificateStatus.approved,
            ]),
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=400,
            detail="You already have a pending or approved request for this certificate type. "
                   "Wait for it to be processed or contact admin.",
        )

    req = CertificateRequest(
        student_id=student.id,
        certificate_type=payload.certificate_type,
        purpose=payload.purpose,
        status=CertificateStatus.pending,
    )
    db.add(req)
    await db.commit()
    await db.refresh(req)
    return req


# ── Student: My requests ───────────────────────────────────────────────────────

async def get_my_requests(
    db: AsyncSession,
    user_id: uuid.UUID,
) -> list[CertificateRequest]:
    student = await _load_student_with_relations(db, user_id)
    result = await db.execute(
        select(CertificateRequest)
        .where(CertificateRequest.student_id == student.id)
        .order_by(CertificateRequest.created_at.desc())
    )
    return list(result.scalars().all())


# ── Admin: List requests ───────────────────────────────────────────────────────

async def list_requests(
    db: AsyncSession,
    status_filter: Optional[CertificateStatus] = None,
    cert_type: Optional[CertificateType] = None,
) -> list[CertificateRequestAdminView]:
    q = (
        select(CertificateRequest)
        .options(
            selectinload(CertificateRequest.student)
            .selectinload(Student.user),
            selectinload(CertificateRequest.student)
            .selectinload(Student.department),
            selectinload(CertificateRequest.student)
            .selectinload(Student.semester),
        )
        .order_by(CertificateRequest.created_at.asc())
    )
    if status_filter:
        q = q.where(CertificateRequest.status == status_filter)
    if cert_type:
        q = q.where(CertificateRequest.certificate_type == cert_type)

    result = await db.execute(q)
    requests = result.scalars().all()

    items: list[CertificateRequestAdminView] = []
    for r in requests:
        item = CertificateRequestAdminView.model_validate(r)
        if r.student:
            s = r.student
            item.roll_number = s.roll_number
            item.department = s.department.name if s.department else None
            item.semester = s.semester.number if s.semester else None
            if s.user:
                item.student_name = f"{s.user.first_name} {s.user.last_name}"
        items.append(item)
    return items


# ── Admin: Review (approve / reject) ──────────────────────────────────────────

async def review_request(
    db: AsyncSession,
    request_id: uuid.UUID,
    payload: AdminReview,
    user_id: uuid.UUID,
) -> CertificateRequest:
    result = await db.execute(
        select(CertificateRequest).where(CertificateRequest.id == request_id)
    )
    req = result.scalar_one_or_none()
    if not req:
        raise HTTPException(status_code=404, detail="Certificate request not found")

    if req.status not in (CertificateStatus.pending, CertificateStatus.under_review):
        raise HTTPException(
            status_code=400,
            detail=f"Cannot review a request with status '{req.status.value}'",
        )

    if payload.status not in (CertificateStatus.approved, CertificateStatus.rejected):
        raise HTTPException(
            status_code=400,
            detail="Review status must be 'approved' or 'rejected'",
        )

    req.status = payload.status
    req.admin_remarks = payload.admin_remarks
    req.reviewed_by_id = user_id
    req.reviewed_at = _now()

    await db.commit()
    await db.refresh(req)
    return req


# ── Admin: Mark under review ───────────────────────────────────────────────────

async def mark_under_review(
    db: AsyncSession,
    request_id: uuid.UUID,
    user_id: uuid.UUID,
) -> CertificateRequest:
    result = await db.execute(
        select(CertificateRequest).where(CertificateRequest.id == request_id)
    )
    req = result.scalar_one_or_none()
    if not req:
        raise HTTPException(status_code=404, detail="Certificate request not found")
    if req.status != CertificateStatus.pending:
        raise HTTPException(status_code=400, detail="Only pending requests can be moved to under_review")

    req.status = CertificateStatus.under_review
    req.reviewed_by_id = user_id
    await db.commit()
    await db.refresh(req)
    return req


# ── Admin: Issue (generate PDF) ────────────────────────────────────────────────

async def issue_certificate(
    db: AsyncSession,
    request_id: uuid.UUID,
    user_id: uuid.UUID,
) -> CertificateRequest:
    result = await db.execute(
        select(CertificateRequest)
        .where(CertificateRequest.id == request_id)
        .options(
            selectinload(CertificateRequest.student)
            .selectinload(Student.user),
            selectinload(CertificateRequest.student)
            .selectinload(Student.department),
            selectinload(CertificateRequest.student)
            .selectinload(Student.semester),
        )
    )
    req = result.scalar_one_or_none()
    if not req:
        raise HTTPException(status_code=404, detail="Certificate request not found")
    if req.status != CertificateStatus.approved:
        raise HTTPException(
            status_code=400,
            detail="Only approved requests can be issued. Approve it first.",
        )

    student = req.student
    user = student.user
    dept = student.department
    sem = student.semester

    student_name = f"{user.first_name} {user.last_name}"
    department_name = dept.name if dept else "N/A"
    semester_num = sem.number if sem else 0
    academic_year = sem.academic_year if sem else "N/A"

    # Generate unique certificate number
    cert_number = _generate_cert_number(req.certificate_type)
    while True:
        dup = await db.execute(
            select(CertificateRequest).where(CertificateRequest.certificate_number == cert_number)
        )
        if not dup.scalar_one_or_none():
            break
        cert_number = _generate_cert_number(req.certificate_type)

    verify_url = f"{getattr(settings, 'frontend_url', 'http://localhost:3000')}/verify-certificate/{cert_number}"
    issued_date = _now().date()

    # Build PDF kwargs shared by all types
    common = dict(
        student_name=student_name,
        roll_number=student.roll_number,
        department=department_name,
        purpose=req.purpose,
        certificate_number=cert_number,
        issued_date=issued_date,
        institution_name=getattr(settings, "app_name", "Smart Campus"),
        verify_url=verify_url,
        academic_year=academic_year,
    )

    cert_type = req.certificate_type

    if cert_type in (CertificateType.bonafide, CertificateType.character, CertificateType.transfer):
        common["semester"] = semester_num
        common["section"] = student.section or "N/A"

    if cert_type in (CertificateType.course_completion, CertificateType.provisional):
        common["program"] = dept.code if dept else department_name
        # remove keys not used by these generators
        common.pop("semester", None)
        common.pop("section", None)

    pdf_bytes = generate_certificate_pdf(cert_type.value, **common)

    # Save PDF to disk
    CERT_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"{cert_number}.pdf"
    file_path = CERT_UPLOAD_DIR / filename
    file_path.write_bytes(pdf_bytes)

    req.certificate_number = cert_number
    req.certificate_url = f"/uploads/certificates/{filename}"
    req.issued_at = _now()
    req.status = CertificateStatus.issued

    await db.commit()
    await db.refresh(req)
    return req


# ── Download certificate ───────────────────────────────────────────────────────

async def download_certificate(
    db: AsyncSession,
    request_id: uuid.UUID,
    user_id: uuid.UUID,
    is_admin: bool = False,
) -> bytes:
    result = await db.execute(
        select(CertificateRequest)
        .where(CertificateRequest.id == request_id)
        .options(selectinload(CertificateRequest.student))
    )
    req = result.scalar_one_or_none()
    if not req:
        raise HTTPException(status_code=404, detail="Certificate request not found")
    if req.status != CertificateStatus.issued:
        raise HTTPException(status_code=400, detail="Certificate has not been issued yet")

    if not is_admin:
        student_result = await db.execute(
            select(Student).where(Student.user_id == user_id)
        )
        student = student_result.scalar_one_or_none()
        if not student or req.student_id != student.id:
            raise HTTPException(status_code=403, detail="Not your certificate")

    if not req.certificate_url:
        raise HTTPException(status_code=500, detail="Certificate file not found")

    file_path = Path(req.certificate_url.lstrip("/"))
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Certificate file missing from storage")

    return file_path.read_bytes()


# ── Public: Verify ─────────────────────────────────────────────────────────────

async def verify_certificate(
    db: AsyncSession,
    certificate_number: str,
) -> CertificateVerifyResponse:
    result = await db.execute(
        select(CertificateRequest)
        .where(CertificateRequest.certificate_number == certificate_number)
        .options(
            selectinload(CertificateRequest.student).selectinload(Student.user),
            selectinload(CertificateRequest.student).selectinload(Student.department),
        )
    )
    req = result.scalar_one_or_none()

    if not req or req.status != CertificateStatus.issued:
        raise HTTPException(
            status_code=404,
            detail="Certificate not found or not valid. It may have been revoked.",
        )

    student = req.student
    user = student.user
    return CertificateVerifyResponse(
        certificate_number=certificate_number,
        certificate_type=req.certificate_type,
        student_name=f"{user.first_name} {user.last_name}",
        roll_number=student.roll_number,
        department=student.department.name if student.department else "N/A",
        issued_at=req.issued_at,
        is_valid=True,
    )
