import uuid
from datetime import datetime

from sqlalchemy import String, DateTime, ForeignKey, Text, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database import Base


class Department(Base):
    __tablename__ = "departments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    head_faculty_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    semesters: Mapped[list["Semester"]] = relationship("Semester", back_populates="department", cascade="all, delete-orphan")
    subjects: Mapped[list["Subject"]] = relationship("Subject", back_populates="department", cascade="all, delete-orphan")
    students: Mapped[list["Student"]] = relationship("Student", back_populates="department")
    faculty_members: Mapped[list["Faculty"]] = relationship("Faculty", back_populates="department")

    def __repr__(self) -> str:
        return f"<Department code={self.code} name={self.name}>"
