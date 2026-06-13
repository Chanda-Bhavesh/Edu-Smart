"""
Certificate Management endpoints.

Student:
  POST   /certificates/request                → submit a new certificate request
  GET    /certificates/my                     → list my requests + statuses
  GET    /certificates/{id}/download          → download issued PDF

Admin:
  GET    /certificates/requests               → list all requests (filter by status/type)
  PUT    /certificates/{id}/under-review      → mark as being reviewed
  PUT    /certificates/{id}/review            → approve or reject
  PUT    /certificates/{id}/issue             → generate PDF and mark as issued
  GET    /certificates/{id}/download          → download any issued PDF

Public (no auth required):
  GET    /certificates/verify/{cert_number}   → verify a certificate is genuine
"""
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies.auth import get_current_admin, get_current_student, get_current_user
from app.models.certificate import CertificateStatus, CertificateType
from app.models.user import User, UserRole
from app.schemas.certificate import (
    AdminReview, CertificateRequestAdminView, CertificateRequestCreate,
    CertificateRequestResponse, CertificateVerifyResponse,
)
from app.services import certificate as cert_service

router = APIRouter(prefix="/certificates", tags=["Certificates"])


# ── Student endpoints ──────────────────────────────────────────────────────────

@router.post("/request", response_model=CertificateRequestResponse, status_code=status.HTTP_201_CREATED)
async def request_certificate(
    payload: CertificateRequestCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_student),
):
    """
    Student: submit a certificate request.
    Specify the type (bonafide / character / course_completion / transfer / provisional)
    and the purpose (e.g. 'for bank account opening').
    """
    return await cert_service.request_certificate(db, payload, current_user.id)


@router.get("/my", response_model=list[CertificateRequestResponse])
async def my_requests(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_student),
):
    """Student: view all my certificate requests and their current status."""
    return await cert_service.get_my_requests(db, current_user.id)


# ── Admin endpoints ────────────────────────────────────────────────────────────

@router.get("/requests", response_model=list[CertificateRequestAdminView])
async def list_requests(
    status_filter: Optional[CertificateStatus] = Query(default=None, alias="status"),
    cert_type: Optional[CertificateType] = Query(default=None),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    """Admin: list all certificate requests. Filter by status or certificate type."""
    return await cert_service.list_requests(db, status_filter, cert_type)


@router.put("/{request_id}/under-review", response_model=CertificateRequestResponse)
async def mark_under_review(
    request_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    """Admin: mark a pending request as under review (signals student it is being processed)."""
    return await cert_service.mark_under_review(db, request_id, current_user.id)


@router.put("/{request_id}/review", response_model=CertificateRequestResponse)
async def review_request(
    request_id: uuid.UUID,
    payload: AdminReview,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    """
    Admin: approve or reject a certificate request.
    - Set status='approved' to allow certificate generation.
    - Set status='rejected' with admin_remarks explaining why.
    """
    return await cert_service.review_request(db, request_id, payload, current_user.id)


@router.put("/{request_id}/issue", response_model=CertificateRequestResponse)
async def issue_certificate(
    request_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    """
    Admin: generate the PDF certificate and mark it as issued.
    Only works on approved requests.
    The PDF is saved locally and a download URL is returned in the response.
    """
    return await cert_service.issue_certificate(db, request_id, current_user.id)


# ── Shared: Download ───────────────────────────────────────────────────────────

@router.get("/{request_id}/download")
async def download_certificate(
    request_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Download the issued PDF certificate.
    Students can only download their own certificates.
    Admins can download any certificate.
    """
    is_admin = current_user.role in (UserRole.dept_admin, UserRole.org_admin)
    pdf_bytes = await cert_service.download_certificate(
        db, request_id, current_user.id, is_admin=is_admin
    )
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="certificate_{request_id}.pdf"'
        },
    )


# ── Public: Verify ─────────────────────────────────────────────────────────────

@router.get("/verify/{certificate_number}", response_model=CertificateVerifyResponse)
async def verify_certificate(
    certificate_number: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Public endpoint — no login required.
    Anyone can verify a certificate's authenticity by entering the certificate number
    printed on the document (e.g. CERT-2024-BON-A3F9B2).
    The QR code on each certificate links here directly.
    """
    return await cert_service.verify_certificate(db, certificate_number)
