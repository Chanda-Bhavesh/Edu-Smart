import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.models.certificate import CertificateStatus, CertificateType


class CertificateRequestCreate(BaseModel):
    certificate_type: CertificateType
    purpose: str = Field(..., min_length=10, max_length=500,
                         description="Reason you need this certificate, e.g. 'for bank account opening'")


class AdminReview(BaseModel):
    status: CertificateStatus = Field(
        ...,
        description="Set to 'approved' or 'rejected'",
    )
    admin_remarks: Optional[str] = Field(
        default=None,
        max_length=1000,
        description="Reason for rejection or any notes for approval",
    )


class CertificateRequestResponse(BaseModel):
    id: uuid.UUID
    student_id: uuid.UUID
    certificate_type: CertificateType
    purpose: str
    status: CertificateStatus
    admin_remarks: Optional[str]
    reviewed_by_id: Optional[uuid.UUID]
    reviewed_at: Optional[datetime]
    certificate_number: Optional[str]
    certificate_url: Optional[str]
    issued_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class CertificateRequestAdminView(CertificateRequestResponse):
    """Extended admin view includes student name and roll number."""
    student_name: Optional[str] = None
    roll_number: Optional[str] = None
    department: Optional[str] = None
    semester: Optional[int] = None


class CertificateVerifyResponse(BaseModel):
    """Public verification response — no sensitive data."""
    certificate_number: str
    certificate_type: CertificateType
    student_name: str
    roll_number: str
    department: str
    issued_at: datetime
    is_valid: bool
