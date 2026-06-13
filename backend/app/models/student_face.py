import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, LargeBinary, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database import Base


class StudentFaceEncoding(Base):
    """Stores the face encoding (numpy array) for a student used in face recognition attendance."""
    __tablename__ = "student_face_encodings"

    id:         Mapped[uuid.UUID]    = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    student_id: Mapped[uuid.UUID]    = mapped_column(ForeignKey("students.id", ondelete="CASCADE"), unique=True, nullable=False)
    encoding:   Mapped[bytes]        = mapped_column(LargeBinary, nullable=False)  # serialised numpy array
    created_at: Mapped[datetime]     = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime]     = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    student: Mapped["Student"] = relationship("Student", foreign_keys=[student_id])

    def __repr__(self) -> str:
        return f"<StudentFaceEncoding student={self.student_id}>"
