import uuid
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies.auth import get_current_user, get_current_admin, get_current_faculty
from app.models.user import User
from app.schemas.faculty import (
    FacultyCreate, FacultyUpdate, FacultySubjectAssign,
    FacultyResponse, PaginatedFaculty,
)
from app.services import faculty as faculty_service

router = APIRouter(prefix="/faculty", tags=["Faculty"])


@router.post("", response_model=FacultyResponse, status_code=status.HTTP_201_CREATED)
async def create_faculty(
    payload: FacultyCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    return await faculty_service.create_faculty(db, payload)


@router.get("", response_model=PaginatedFaculty)
async def list_faculty(
    department_id: uuid.UUID | None = None,
    search: str | None = None,
    is_active: bool | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    return await faculty_service.get_faculty_list(db, department_id, search, is_active, page, page_size)


@router.get("/me", response_model=FacultyResponse)
async def get_my_profile(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_faculty),
):
    return await faculty_service.get_faculty_by_user_id(db, current_user.id)


@router.get("/{faculty_id}", response_model=FacultyResponse)
async def get_faculty(
    faculty_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    return await faculty_service.get_faculty_by_id(db, faculty_id)


@router.put("/{faculty_id}", response_model=FacultyResponse)
async def update_faculty(
    faculty_id: uuid.UUID,
    payload: FacultyUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    return await faculty_service.update_faculty(db, faculty_id, payload)


@router.delete("/{faculty_id}", status_code=status.HTTP_204_NO_CONTENT)
async def deactivate_faculty(
    faculty_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    await faculty_service.deactivate_faculty(db, faculty_id)


@router.post("/{faculty_id}/subjects", response_model=FacultyResponse)
async def assign_subject(
    faculty_id: uuid.UUID,
    payload: FacultySubjectAssign,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    return await faculty_service.assign_subject(db, faculty_id, payload.subject_id)


@router.delete("/{faculty_id}/subjects/{subject_id}", response_model=FacultyResponse)
async def remove_subject(
    faculty_id: uuid.UUID,
    subject_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    return await faculty_service.remove_subject(db, faculty_id, subject_id)
