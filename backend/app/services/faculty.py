import uuid
from fastapi import HTTPException, status
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.user import User, UserRole
from app.models.faculty import Faculty
from app.models.subject import Subject
from app.schemas.faculty import FacultyCreate, FacultyUpdate
from app.utils.security import hash_password, generate_token, token_expiry
from app.utils import email as email_utils


async def create_faculty(db: AsyncSession, payload: FacultyCreate) -> Faculty:
    # Check email uniqueness
    result = await db.execute(select(User).where(User.email == payload.email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    # Check employee_id uniqueness
    result = await db.execute(select(Faculty).where(Faculty.employee_id == payload.employee_id))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Employee ID already exists")

    # Create User account
    verification_token = generate_token()
    user = User(
        email=payload.email,
        hashed_password=hash_password(payload.password),
        full_name=payload.full_name,
        role=UserRole.faculty,
        is_verified=False,
        verification_token=verification_token,
        verification_token_expires=token_expiry(hours=24),
    )
    db.add(user)
    await db.flush()

    # Create Faculty profile
    faculty = Faculty(
        user_id=user.id,
        employee_id=payload.employee_id,
        department_id=payload.department_id,
        designation=payload.designation,
        specialization=payload.specialization,
        phone=payload.phone,
        office_location=payload.office_location,
    )
    db.add(faculty)
    await db.flush()

    try:
        email_utils.send_verification_email(user.email, user.full_name, verification_token)
    except Exception:
        pass

    return await _get_faculty_with_relations(db, faculty.id)


async def get_faculty_list(
    db: AsyncSession,
    department_id: uuid.UUID | None = None,
    search: str | None = None,
    is_active: bool | None = None,
    page: int = 1,
    page_size: int = 20,
) -> dict:
    query = (
        select(Faculty)
        .join(Faculty.user)
        .options(selectinload(Faculty.user), selectinload(Faculty.department))
    )

    if department_id:
        query = query.where(Faculty.department_id == department_id)
    if is_active is not None:
        query = query.where(Faculty.is_active == is_active)
    if search:
        query = query.where(
            or_(
                User.full_name.ilike(f"%{search}%"),
                Faculty.employee_id.ilike(f"%{search}%"),
            )
        )

    count_result = await db.execute(select(func.count()).select_from(query.subquery()))
    total = count_result.scalar_one()

    query = query.order_by(Faculty.employee_id).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    faculty_list = list(result.scalars().all())

    return {"total": total, "page": page, "page_size": page_size, "items": faculty_list}


async def get_faculty_by_id(db: AsyncSession, faculty_id: uuid.UUID) -> Faculty:
    return await _get_faculty_with_relations(db, faculty_id)


async def get_faculty_by_user_id(db: AsyncSession, user_id: uuid.UUID) -> Faculty:
    result = await db.execute(
        select(Faculty)
        .where(Faculty.user_id == user_id)
        .options(selectinload(Faculty.user), selectinload(Faculty.department), selectinload(Faculty.subjects))
    )
    faculty = result.scalar_one_or_none()
    if not faculty:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Faculty profile not found")
    return faculty


async def update_faculty(db: AsyncSession, faculty_id: uuid.UUID, payload: FacultyUpdate) -> Faculty:
    faculty = await _get_faculty_with_relations(db, faculty_id)

    update_data = payload.model_dump(exclude_none=True)
    full_name = update_data.pop("full_name", None)

    for field, value in update_data.items():
        setattr(faculty, field, value)

    if full_name:
        faculty.user.full_name = full_name

    await db.flush()
    return faculty


async def deactivate_faculty(db: AsyncSession, faculty_id: uuid.UUID) -> Faculty:
    faculty = await _get_faculty_with_relations(db, faculty_id)
    faculty.is_active = False
    faculty.user.is_active = False
    await db.flush()
    return faculty


async def assign_subject(db: AsyncSession, faculty_id: uuid.UUID, subject_id: uuid.UUID) -> Faculty:
    faculty = await _get_faculty_with_relations(db, faculty_id)

    result = await db.execute(select(Subject).where(Subject.id == subject_id))
    subject = result.scalar_one_or_none()
    if not subject:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subject not found")

    if subject in faculty.subjects:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Subject already assigned to this faculty")

    faculty.subjects.append(subject)
    await db.flush()
    return faculty


async def remove_subject(db: AsyncSession, faculty_id: uuid.UUID, subject_id: uuid.UUID) -> Faculty:
    faculty = await _get_faculty_with_relations(db, faculty_id)

    result = await db.execute(select(Subject).where(Subject.id == subject_id))
    subject = result.scalar_one_or_none()
    if not subject or subject not in faculty.subjects:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subject not assigned to this faculty")

    faculty.subjects.remove(subject)
    await db.flush()
    return faculty


async def _get_faculty_with_relations(db: AsyncSession, faculty_id: uuid.UUID) -> Faculty:
    result = await db.execute(
        select(Faculty)
        .where(Faculty.id == faculty_id)
        .options(
            selectinload(Faculty.user),
            selectinload(Faculty.department),
            selectinload(Faculty.subjects),
        )
    )
    faculty = result.scalar_one_or_none()
    if not faculty:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Faculty not found")
    return faculty
