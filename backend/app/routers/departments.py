import uuid
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies.auth import get_current_user, get_current_admin
from app.models.user import User
from app.schemas.department import (
    DepartmentCreate, DepartmentUpdate, DepartmentResponse,
    SemesterCreate, SemesterUpdate, SemesterResponse,
    SubjectCreate, SubjectUpdate, SubjectResponse,
)
from app.services import department as dept_service

router = APIRouter(prefix="/departments", tags=["Departments"])


# ── Departments ───────────────────────────────────────────────────────────────

@router.post("", response_model=DepartmentResponse, status_code=status.HTTP_201_CREATED)
async def create_department(
    payload: DepartmentCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    return await dept_service.create_department(db, payload)


@router.get("", response_model=list[DepartmentResponse])
async def list_departments(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return await dept_service.get_all_departments(db)


@router.get("/{dept_id}", response_model=DepartmentResponse)
async def get_department(
    dept_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return await dept_service.get_department(db, dept_id)


@router.put("/{dept_id}", response_model=DepartmentResponse)
async def update_department(
    dept_id: uuid.UUID,
    payload: DepartmentUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    return await dept_service.update_department(db, dept_id, payload)


@router.delete("/{dept_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_department(
    dept_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    await dept_service.delete_department(db, dept_id)


# ── Semesters ─────────────────────────────────────────────────────────────────

@router.post("/{dept_id}/semesters", response_model=SemesterResponse, status_code=status.HTTP_201_CREATED)
async def create_semester(
    dept_id: uuid.UUID,
    payload: SemesterCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    payload.department_id = dept_id
    return await dept_service.create_semester(db, payload)


@router.get("/{dept_id}/semesters", response_model=list[SemesterResponse])
async def list_semesters(
    dept_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return await dept_service.get_semesters_by_dept(db, dept_id)


# ── Subjects ──────────────────────────────────────────────────────────────────

@router.post("/{dept_id}/subjects", response_model=SubjectResponse, status_code=status.HTTP_201_CREATED)
async def create_subject(
    dept_id: uuid.UUID,
    payload: SubjectCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    payload.department_id = dept_id
    return await dept_service.create_subject(db, payload)


@router.get("/{dept_id}/subjects", response_model=list[SubjectResponse])
async def list_subjects(
    dept_id: uuid.UUID,
    semester_number: int | None = None,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return await dept_service.get_subjects_by_dept(db, dept_id, semester_number)


@router.put("/subjects/{subject_id}", response_model=SubjectResponse)
async def update_subject(
    subject_id: uuid.UUID,
    payload: SubjectUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    return await dept_service.update_subject(db, subject_id, payload)


@router.delete("/subjects/{subject_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_subject(
    subject_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    await dept_service.delete_subject(db, subject_id)
