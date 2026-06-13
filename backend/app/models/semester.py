import uuid
from datetime import datetime, date

from sqlalchemy import String, DateTime, Date, ForeignKey, Integer, UniqueConstraint, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database import Base


class Semester(Base):
    __tablename__ = "semesters"
    __table_args__ = (
        UniqueConstraint("department_id", "number", "academic_year", name="uq_semester_dept_number_year"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    number: Mapped[int] = mapped_column(Integer, nullable=False)
    academic_year: Mapped[str] = mapped_column(String(9), nullable=False)  # e.g. "2024-2025"
    department_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("departments.id", ondelete="CASCADE"), nullable=False)
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    department: Mapped["Department"] = relationship("Department", back_populates="semesters")
    students: Mapped[list["Student"]] = relationship("Student", back_populates="semester")

    def __repr__(self) -> str:
        return f"<Semester {self.number} dept={self.department_id} year={self.academic_year}>"
