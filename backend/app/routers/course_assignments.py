import uuid
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies.auth import get_current_admin, get_current_faculty, get_current_user
from app.models.user import User
from app.schemas.course_assignment import (
    CourseAssignmentCreate,
    CourseAssignmentUpdate,
    CourseAssignmentResponse,
    CourseAssignmentWithStudents,
)
from app.services import course_assignment as ca_service

router = APIRouter(prefix="/course-assignments", tags=["Course Assignments"])


@router.post("", response_model=CourseAssignmentResponse, status_code=status.HTTP_201_CREATED)
async def create_assignment(
    payload: CourseAssignmentCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    """Assign a faculty to teach a subject for a specific section and semester."""
    return await ca_service.create_assignment(db, payload)


@router.get("", response_model=list[CourseAssignmentResponse])
async def list_assignments(
    faculty_id: uuid.UUID | None = None,
    subject_id: uuid.UUID | None = None,
    semester_id: uuid.UUID | None = None,
    section: str | None = None,
    is_active: bool | None = None,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    """List all course assignments with optional filters."""
    return await ca_service.get_all_assignments(db, faculty_id, subject_id, semester_id, section, is_active)


@router.get("/my-classes", response_model=list[CourseAssignmentResponse])
async def my_classes(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_faculty),
):
    """Faculty: see all classes they are assigned to teach."""
    return await ca_service.get_my_classes(db, current_user.id)


@router.get("/{assignment_id}", response_model=CourseAssignmentResponse)
async def get_assignment(
    assignment_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Get a single course assignment by ID."""
    return await ca_service.get_assignment(db, assignment_id)


@router.get("/{assignment_id}/students", response_model=CourseAssignmentWithStudents)
async def get_students_in_class(
    assignment_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """
    Get all students belonging to this class.
    Faculty uses this when opening the attendance page — it shows exactly
    which students to mark attendance for.
    """
    return await ca_service.get_students_in_class(db, assignment_id)


@router.patch("/{assignment_id}", response_model=CourseAssignmentResponse)
async def update_assignment(
    assignment_id: uuid.UUID,
    payload: CourseAssignmentUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    """Activate or deactivate a course assignment."""
    return await ca_service.update_assignment(db, assignment_id, payload)


@router.delete("/{assignment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_assignment(
    assignment_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    """Permanently remove a course assignment."""
    await ca_service.delete_assignment(db, assignment_id)
