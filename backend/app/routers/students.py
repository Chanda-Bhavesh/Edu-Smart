import uuid
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies.auth import get_current_user, get_current_admin, get_current_student
from app.models.student import StudentStatus
from app.models.user import User
from app.schemas.student import (
    StudentCreate, StudentUpdate, StudentStatusUpdate,
    StudentResponse, PaginatedStudents,
)
from app.services import student as student_service

router = APIRouter(prefix="/students", tags=["Students"])


@router.post("", response_model=StudentResponse, status_code=status.HTTP_201_CREATED)
async def create_student(
    payload: StudentCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    return await student_service.create_student(db, payload)


@router.get("", response_model=PaginatedStudents)
async def list_students(
    department_id: uuid.UUID | None = None,
    semester_id: uuid.UUID | None = None,
    section: str | None = None,
    student_status: StudentStatus | None = Query(None, alias="status"),
    search: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    return await student_service.get_students(
        db, department_id, semester_id, section, student_status, search, page, page_size
    )


@router.get("/me", response_model=StudentResponse)
async def get_my_profile(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_student),
):
    return await student_service.get_student_by_user_id(db, current_user.id)


@router.get("/{student_id}", response_model=StudentResponse)
async def get_student(
    student_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    return await student_service.get_student_by_id(db, student_id)


@router.put("/{student_id}", response_model=StudentResponse)
async def update_student(
    student_id: uuid.UUID,
    payload: StudentUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    return await student_service.update_student(db, student_id, payload)


@router.patch("/{student_id}/status", response_model=StudentResponse)
async def update_student_status(
    student_id: uuid.UUID,
    payload: StudentStatusUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    return await student_service.update_student_status(db, student_id, payload)


@router.delete("/{student_id}", status_code=status.HTTP_204_NO_CONTENT)
async def deactivate_student(
    student_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    await student_service.delete_student(db, student_id)
