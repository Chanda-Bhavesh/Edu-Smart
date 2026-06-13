import uuid
from fastapi import HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.department import Department
from app.models.semester import Semester
from app.models.subject import Subject
from app.schemas.department import (
    DepartmentCreate, DepartmentUpdate,
    SemesterCreate, SemesterUpdate,
    SubjectCreate, SubjectUpdate,
)


# ── Department ────────────────────────────────────────────────────────────────

async def create_department(db: AsyncSession, payload: DepartmentCreate) -> Department:
    existing = await db.execute(select(Department).where(Department.code == payload.code.upper()))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Department code already exists")

    dept = Department(**payload.model_dump(), code=payload.code.upper())
    db.add(dept)
    await db.flush()
    return dept


async def get_all_departments(db: AsyncSession) -> list[Department]:
    result = await db.execute(select(Department).order_by(Department.name))
    return list(result.scalars().all())


async def get_department(db: AsyncSession, dept_id: uuid.UUID) -> Department:
    result = await db.execute(select(Department).where(Department.id == dept_id))
    dept = result.scalar_one_or_none()
    if not dept:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Department not found")
    return dept


async def update_department(db: AsyncSession, dept_id: uuid.UUID, payload: DepartmentUpdate) -> Department:
    dept = await get_department(db, dept_id)
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(dept, field, value)
    await db.flush()
    return dept


async def delete_department(db: AsyncSession, dept_id: uuid.UUID) -> None:
    dept = await get_department(db, dept_id)
    await db.delete(dept)


# ── Semester ──────────────────────────────────────────────────────────────────

async def create_semester(db: AsyncSession, payload: SemesterCreate) -> Semester:
    await get_department(db, payload.department_id)

    existing = await db.execute(
        select(Semester).where(
            Semester.department_id == payload.department_id,
            Semester.number == payload.number,
            Semester.academic_year == payload.academic_year,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Semester already exists for this department and year")

    semester = Semester(**payload.model_dump())
    db.add(semester)
    await db.flush()
    return semester


async def get_semesters_by_dept(db: AsyncSession, dept_id: uuid.UUID) -> list[Semester]:
    result = await db.execute(
        select(Semester).where(Semester.department_id == dept_id).order_by(Semester.number)
    )
    return list(result.scalars().all())


async def get_semester(db: AsyncSession, semester_id: uuid.UUID) -> Semester:
    result = await db.execute(select(Semester).where(Semester.id == semester_id))
    sem = result.scalar_one_or_none()
    if not sem:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Semester not found")
    return sem


# ── Subject ───────────────────────────────────────────────────────────────────

async def create_subject(db: AsyncSession, payload: SubjectCreate) -> Subject:
    await get_department(db, payload.department_id)

    existing = await db.execute(select(Subject).where(Subject.code == payload.code.upper()))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Subject code already exists")

    subject = Subject(**payload.model_dump(), code=payload.code.upper())
    db.add(subject)
    await db.flush()
    return subject


async def get_subjects_by_dept(db: AsyncSession, dept_id: uuid.UUID, semester_number: int | None = None) -> list[Subject]:
    query = select(Subject).where(Subject.department_id == dept_id)
    if semester_number:
        query = query.where(Subject.semester_number == semester_number)
    result = await db.execute(query.order_by(Subject.name))
    return list(result.scalars().all())


async def get_subject(db: AsyncSession, subject_id: uuid.UUID) -> Subject:
    result = await db.execute(select(Subject).where(Subject.id == subject_id))
    subject = result.scalar_one_or_none()
    if not subject:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subject not found")
    return subject


async def update_subject(db: AsyncSession, subject_id: uuid.UUID, payload: SubjectUpdate) -> Subject:
    subject = await get_subject(db, subject_id)
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(subject, field, value)
    await db.flush()
    return subject


async def delete_subject(db: AsyncSession, subject_id: uuid.UUID) -> None:
    subject = await get_subject(db, subject_id)
    await db.delete(subject)
