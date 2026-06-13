"""
Assignment & Submission endpoints.

Faculty:
  POST   /assignments                        → create (draft)
  GET    /assignments                        → my assignments
  GET    /assignments/{id}                   → detail
  PUT    /assignments/{id}                   → edit
  DELETE /assignments/{id}                   → delete (draft only)
  POST   /assignments/{id}/file              → upload/replace attachment
  PUT    /assignments/{id}/publish           → draft → published
  PUT    /assignments/{id}/close             → published → closed
  PUT    /assignments/{id}/publish-grades    → closed → graded (release grades)
  GET    /assignments/{id}/submissions       → all student submissions
  PUT    /submissions/{id}/grade             → grade one submission
  GET    /assignments/{id}/stats             → submission statistics

Student:
  GET    /assignments/my                     → assignments for my subjects
  GET    /assignments/{id}                   → view assignment
  POST   /assignments/{id}/submit            → submit file/text
  GET    /assignments/{id}/my-submission     → view my submission & grade
"""
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies.auth import get_current_faculty, get_current_student, get_current_user
from app.models.assignment import AssignmentStatus
from app.models.user import User
from app.schemas.assignment import (
    AssignmentCreate, AssignmentResponse, AssignmentListItem,
    AssignmentStats, AssignmentUpdate,
    GradeSubmission, SubmissionResponse, SubmissionWithStudent,
)
from app.services import assignment as asgn_service

router = APIRouter(prefix="/assignments", tags=["Assignments"])


# ── Faculty: CRUD ──────────────────────────────────────────────────────────────

@router.post("", response_model=AssignmentResponse, status_code=status.HTTP_201_CREATED)
async def create_assignment(
    payload: AssignmentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_faculty),
):
    """Faculty: create a new assignment in draft state."""
    return await asgn_service.create_assignment(db, payload, current_user.id)


@router.get("", response_model=list[AssignmentResponse])
async def list_my_assignments(
    subject_id: Optional[uuid.UUID] = Query(default=None),
    status_filter: Optional[AssignmentStatus] = Query(default=None, alias="status"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_faculty),
):
    """Faculty: list all my assignments (optionally filter by subject or status)."""
    return await asgn_service.get_faculty_assignments(
        db, current_user.id, subject_id, status_filter
    )


@router.get("/my", response_model=list[AssignmentListItem])
async def student_assignments(
    subject_id: Optional[uuid.UUID] = Query(default=None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_student),
):
    """Student: view all assignments for subjects I am enrolled in."""
    return await asgn_service.get_student_assignments(db, current_user.id, subject_id)


@router.get("/{assignment_id}", response_model=AssignmentResponse)
async def get_assignment(
    assignment_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Any authenticated user: get assignment details."""
    from sqlalchemy import select
    from app.models.assignment import Assignment
    result = await db.execute(select(Assignment).where(Assignment.id == assignment_id))
    a = result.scalar_one_or_none()
    if not a:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Assignment not found")
    return a


@router.put("/{assignment_id}", response_model=AssignmentResponse)
async def update_assignment(
    assignment_id: uuid.UUID,
    payload: AssignmentUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_faculty),
):
    """Faculty: update assignment title, description, deadline, or marks."""
    return await asgn_service.update_assignment(db, assignment_id, payload, current_user.id)


@router.delete("/{assignment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_assignment(
    assignment_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_faculty),
):
    """Faculty: delete a draft assignment."""
    await asgn_service.delete_assignment(db, assignment_id, current_user.id)


# ── Faculty: File upload ───────────────────────────────────────────────────────

@router.post("/{assignment_id}/file", response_model=AssignmentResponse)
async def upload_file(
    assignment_id: uuid.UUID,
    file: UploadFile = File(..., description="Assignment attachment (PDF, DOCX, etc.)"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_faculty),
):
    """Faculty: attach a file to an assignment."""
    return await asgn_service.upload_assignment_file(db, assignment_id, file, current_user.id)


# ── Faculty: Status transitions ────────────────────────────────────────────────

@router.put("/{assignment_id}/publish", response_model=AssignmentResponse)
async def publish_assignment(
    assignment_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_faculty),
):
    """Faculty: publish assignment so students can see and submit."""
    return await asgn_service.publish_assignment(db, assignment_id, current_user.id)


@router.put("/{assignment_id}/close", response_model=AssignmentResponse)
async def close_assignment(
    assignment_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_faculty),
):
    """Faculty: close assignment for new submissions."""
    return await asgn_service.close_assignment(db, assignment_id, current_user.id)


@router.put("/{assignment_id}/publish-grades", response_model=AssignmentResponse)
async def publish_grades(
    assignment_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_faculty),
):
    """Faculty: release all grades — students can now see their marks."""
    return await asgn_service.publish_grades(db, assignment_id, current_user.id)


# ── Faculty: Submissions ───────────────────────────────────────────────────────

@router.get("/{assignment_id}/submissions", response_model=list[SubmissionWithStudent])
async def list_submissions(
    assignment_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_faculty),
):
    """Faculty: view all student submissions for an assignment."""
    return await asgn_service.get_assignment_submissions(db, assignment_id, current_user.id)


@router.get("/{assignment_id}/stats", response_model=AssignmentStats)
async def assignment_stats(
    assignment_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_faculty),
):
    """Faculty: get submission statistics for an assignment."""
    return await asgn_service.get_assignment_stats(db, assignment_id, current_user.id)


# ── Submissions router (separate prefix) ──────────────────────────────────────
sub_router = APIRouter(prefix="/submissions", tags=["Assignments"])


@sub_router.put("/{submission_id}/grade", response_model=SubmissionResponse)
async def grade_submission(
    submission_id: uuid.UUID,
    payload: GradeSubmission,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_faculty),
):
    """Faculty: assign marks and feedback to a student submission."""
    return await asgn_service.grade_submission(db, submission_id, payload, current_user.id)


# ── Student: Submit ────────────────────────────────────────────────────────────

@router.post("/{assignment_id}/submit", response_model=SubmissionResponse, status_code=status.HTTP_201_CREATED)
async def submit_assignment(
    assignment_id: uuid.UUID,
    content: Optional[str] = Form(default=None, description="Text answer (optional if file provided)"),
    file: Optional[UploadFile] = File(default=None, description="Submission file (optional if content provided)"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_student),
):
    """Student: submit an assignment (file, text, or both)."""
    return await asgn_service.submit_assignment(
        db, assignment_id, content, file, current_user.id
    )


@router.get("/{assignment_id}/my-submission", response_model=SubmissionResponse)
async def my_submission(
    assignment_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_student),
):
    """Student: view my submission details and grade (visible after grades are published)."""
    return await asgn_service.get_my_submission(db, assignment_id, current_user.id)
