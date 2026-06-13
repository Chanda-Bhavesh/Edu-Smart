import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.models.ai_prediction import RiskLevel


# ── Attendance Risk ────────────────────────────────────────────────────────────

class SubjectRisk(BaseModel):
    subject_id: uuid.UUID
    subject_name: str
    subject_code: str
    current_attendance_pct: float
    sessions_attended: int
    total_sessions: int
    sessions_remaining: int
    sessions_needed_for_75: int
    is_recoverable: bool
    risk_level: RiskLevel
    risk_score: float
    recommendation: str


class StudentRiskReport(BaseModel):
    student_id: uuid.UUID
    student_name: str
    roll_number: str
    department: str
    semester: int
    section: str
    overall_attendance_pct: float
    overall_risk_level: RiskLevel
    subject_risks: list[SubjectRisk]
    critical_subjects: int
    at_risk_subjects: int
    safe_subjects: int
    predicted_at: datetime


class AtRiskSummary(BaseModel):
    """Lightweight card for admin/faculty lists."""
    student_id: uuid.UUID
    student_name: str
    roll_number: str
    section: str
    overall_attendance_pct: float
    overall_risk_level: RiskLevel
    critical_subject_count: int


# ── Performance Prediction ─────────────────────────────────────────────────────

class SubjectPerformancePrediction(BaseModel):
    subject_id: uuid.UUID
    subject_name: str
    attendance_pct: float
    avg_marks_pct: float           # avg marks as % of max marks
    weighted_score: float          # attendance 30% + marks 70%
    predicted_grade: str           # A / B / C / D / F
    assignments_submitted: int
    assignments_total: int


class PerformancePrediction(BaseModel):
    student_id: uuid.UUID
    student_name: str
    roll_number: str
    overall_weighted_score: float
    predicted_overall_grade: str
    failure_risk: str              # low / medium / high
    subject_predictions: list[SubjectPerformancePrediction]
    key_concerns: list[str]        # plain-language warnings
    strengths: list[str]           # subjects performing well
    generated_at: datetime


# ── Chatbot ────────────────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    session_id: Optional[uuid.UUID] = None  # None = create new session


class ChatMessageResponse(BaseModel):
    id: uuid.UUID
    role: str
    content: str
    created_at: datetime

    model_config = {"from_attributes": True}


class ChatResponse(BaseModel):
    session_id: uuid.UUID
    session_title: str
    reply: str
    created_at: datetime


class ChatSessionResponse(BaseModel):
    id: uuid.UUID
    title: str
    created_at: datetime
    last_message_at: datetime
    message_count: int

    model_config = {"from_attributes": True}


class ChatHistoryResponse(BaseModel):
    session_id: uuid.UUID
    title: str
    messages: list[ChatMessageResponse]
