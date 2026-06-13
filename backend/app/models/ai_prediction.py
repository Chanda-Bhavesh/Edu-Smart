import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, Float, ForeignKey, Integer, String, Text, UUID, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database import Base


class RiskLevel(str, enum.Enum):
    low = "low"           # attendance >= 85%
    medium = "medium"     # 75% <= attendance < 85%
    high = "high"         # 65% <= attendance < 75%
    critical = "critical" # attendance < 65% OR impossible to reach 75%


class AIRiskPrediction(Base):
    """
    Stores the most recent attendance risk score for a student per subject.
    Refreshed on demand or via a scheduled job.
    """
    __tablename__ = "ai_risk_predictions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    student_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("students.id", ondelete="CASCADE"), nullable=False
    )
    subject_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("subjects.id", ondelete="CASCADE"), nullable=True
    )  # NULL = overall (all subjects combined)

    risk_level: Mapped[RiskLevel] = mapped_column(Enum(RiskLevel), nullable=False)
    risk_score: Mapped[float] = mapped_column(Float, nullable=False)  # 0–100 (higher = more at risk)

    current_attendance_pct: Mapped[float] = mapped_column(Float, nullable=False)
    sessions_attended: Mapped[int] = mapped_column(Integer, default=0)
    total_sessions: Mapped[int] = mapped_column(Integer, default=0)
    sessions_remaining: Mapped[int] = mapped_column(Integer, default=0)
    sessions_needed_for_75: Mapped[int] = mapped_column(Integer, default=0)
    is_recoverable: Mapped[bool] = mapped_column(default=True)

    recommendation: Mapped[str | None] = mapped_column(Text, nullable=True)
    features_snapshot: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    predicted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    student = relationship("Student", backref="risk_predictions")
    subject = relationship("Subject", backref="risk_predictions")


class ChatSession(Base):
    """One conversation thread between a user and the AI assistant."""
    __tablename__ = "chat_sessions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(200), default="New Chat")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    last_message_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    user = relationship("User", backref="chat_sessions")
    messages = relationship(
        "ChatMessage", back_populates="session",
        cascade="all, delete-orphan", order_by="ChatMessage.created_at"
    )


class ChatMessage(Base):
    """A single message within a ChatSession."""
    __tablename__ = "chat_messages"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("chat_sessions.id", ondelete="CASCADE"), nullable=False
    )
    role: Mapped[str] = mapped_column(String(20), nullable=False)  # "user" | "assistant"
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    session = relationship("ChatSession", back_populates="messages")
