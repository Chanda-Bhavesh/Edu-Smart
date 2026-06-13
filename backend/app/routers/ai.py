"""
AI Feature Endpoints
  GET  /ai/attendance-risk                   - list at-risk students (admin/faculty)
  GET  /ai/attendance-risk/me                - own risk report (student)
  GET  /ai/attendance-risk/{student_id}      - risk report for a student (admin/faculty)
  GET  /ai/performance/me                    - own performance prediction (student)
  GET  /ai/performance/{student_id}          - performance prediction (admin/faculty)
  POST /ai/chat                              - send a message to the AI assistant
  GET  /ai/chat/sessions                     - list own chat sessions
  GET  /ai/chat/sessions/{session_id}        - get chat history for a session
"""
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies.auth import get_current_user, require_role
from app.models.ai_prediction import RiskLevel
from app.models.user import User, UserRole
from app.schemas.ai import (
    AtRiskSummary, ChatHistoryResponse, ChatRequest, ChatResponse,
    ChatSessionResponse, PerformancePrediction, StudentRiskReport,
)
from app.services.ai_risk import (
    compute_student_risk, get_at_risk_students, predict_performance,
)
from app.services.ai_chatbot import (
    chat, get_session_history, list_sessions,
)

router = APIRouter(prefix="/ai", tags=["AI Features"])


# ── Attendance Risk ────────────────────────────────────────────────────────────

@router.get(
    "/attendance-risk",
    response_model=list[AtRiskSummary],
    summary="List at-risk students (admin / faculty)",
)
async def list_at_risk_students(
    semester_id: Optional[uuid.UUID] = Query(None),
    department_id: Optional[uuid.UUID] = Query(None),
    min_level: RiskLevel = Query(RiskLevel.high),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(
        require_role(UserRole.dept_admin, UserRole.org_admin, UserRole.faculty)
    ),
):
    return await get_at_risk_students(db, semester_id, department_id, min_level)


@router.get(
    "/attendance-risk/me",
    response_model=StudentRiskReport,
    summary="Own attendance risk report (student)",
)
async def my_attendance_risk(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.student)),
):
    from app.models.student import Student
    from sqlalchemy import select

    result = await db.execute(
        select(Student).where(Student.user_id == current_user.id)
    )
    student = result.scalar_one_or_none()
    if not student:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Student profile not found")
    return await compute_student_risk(db, student.id)


@router.get(
    "/attendance-risk/{student_id}",
    response_model=StudentRiskReport,
    summary="Attendance risk report for a specific student (admin / faculty)",
)
async def student_attendance_risk(
    student_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(
        require_role(UserRole.dept_admin, UserRole.org_admin, UserRole.faculty)
    ),
):
    return await compute_student_risk(db, student_id)


# ── Performance Prediction ─────────────────────────────────────────────────────

@router.get(
    "/performance/me",
    response_model=PerformancePrediction,
    summary="Own performance prediction (student)",
)
async def my_performance(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.student)),
):
    from app.models.student import Student
    from sqlalchemy import select

    result = await db.execute(
        select(Student).where(Student.user_id == current_user.id)
    )
    student = result.scalar_one_or_none()
    if not student:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Student profile not found")
    return await predict_performance(db, student.id)


@router.get(
    "/performance/{student_id}",
    response_model=PerformancePrediction,
    summary="Performance prediction for a specific student (admin / faculty)",
)
async def student_performance(
    student_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(
        require_role(UserRole.dept_admin, UserRole.org_admin, UserRole.faculty)
    ),
):
    return await predict_performance(db, student_id)


# ── Chatbot ────────────────────────────────────────────────────────────────────

@router.post(
    "/chat",
    response_model=ChatResponse,
    summary="Send a message to the AI campus assistant",
)
async def send_message(
    payload: ChatRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await chat(db, current_user, payload.message, payload.session_id)


@router.get(
    "/chat/sessions",
    response_model=list[ChatSessionResponse],
    summary="List own chat sessions",
)
async def my_chat_sessions(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await list_sessions(db, current_user.id)


@router.get(
    "/chat/sessions/{session_id}",
    response_model=ChatHistoryResponse,
    summary="Get message history for a chat session",
)
async def chat_session_history(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await get_session_history(db, current_user.id, session_id)
