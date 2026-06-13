import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database import Base


class CertificateType(str, enum.Enum):
    bonafide = "bonafide"
    character = "character"
    course_completion = "course_completion"
    transfer = "transfer"
    provisional = "provisional"


class CertificateStatus(str, enum.Enum):
    pending = "pending"           # student submitted request
    under_review = "under_review" # admin opened it
    approved = "approved"         # approved but PDF not yet generated
    rejected = "rejected"         # request denied
    issued = "issued"             # PDF generated and available for download


# Short codes used in certificate numbers
CERT_TYPE_CODE = {
    CertificateType.bonafide: "BON",
    CertificateType.character: "CHAR",
    CertificateType.course_completion: "COMP",
    CertificateType.transfer: "TRANS",
    CertificateType.provisional: "PROV",
}


class CertificateRequest(Base):
    __tablename__ = "certificate_requests"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    student_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("students.id", ondelete="CASCADE"), nullable=False
    )

    certificate_type: Mapped[CertificateType] = mapped_column(
        Enum(CertificateType), nullable=False
    )
    purpose: Mapped[str] = mapped_column(
        String(500), nullable=False
    )  # e.g. "for bank account opening", "for passport application"

    status: Mapped[CertificateStatus] = mapped_column(
        Enum(CertificateStatus), default=CertificateStatus.pending, nullable=False
    )

    # Admin review fields
    admin_remarks: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviewed_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Issue fields (populated when status → issued)
    certificate_number: Mapped[str | None] = mapped_column(String(60), unique=True, nullable=True)
    certificate_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    issued_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    student = relationship("Student", backref="certificate_requests")
    reviewed_by = relationship("User", foreign_keys=[reviewed_by_id])
