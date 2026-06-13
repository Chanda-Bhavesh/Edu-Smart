import uuid
from fastapi import HTTPException, status
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.user import User, UserRole
from app.models.student import Student, StudentStatus
from app.schemas.student import StudentCreate, StudentUpdate, StudentStatusUpdate
from app.utils.security import hash_password, generate_token, token_expiry
from app.utils import email as email_utils


async def create_student(db: AsyncSession, payload: StudentCreate) -> Student:
    # Check email uniqueness
    result = await db.execute(select(User).where(User.email == payload.email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    # Check roll number uniqueness
    result = await db.execute(select(Student).where(Student.roll_number == payload.roll_number))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Roll number already exists")

    # Create User account
    verification_token = generate_token()
    user = User(
        email=payload.email,
        hashed_password=hash_password(payload.password),
        full_name=payload.full_name,
        role=UserRole.student,
        is_verified=False,
        verification_token=verification_token,
        verification_token_expires=token_expiry(hours=24),
    )
    db.add(user)
    await db.flush()

    # Create Student profile
    student = Student(
        user_id=user.id,
        roll_number=payload.roll_number,
        department_id=payload.department_id,
        semester_id=payload.semester_id,
        section=payload.section,
        phone=payload.phone,
        date_of_birth=payload.date_of_birth,
        blood_group=payload.blood_group,
        address=payload.address,
        guardian_name=payload.guardian_name,
        guardian_phone=payload.guardian_phone,
        guardian_relation=payload.guardian_relation,
    )
    db.add(student)
    await db.flush()

    try:
        email_utils.send_verification_email(user.email, user.full_name, verification_token)
    except Exception:
        pass

    return await _get_student_with_relations(db, student.id)


async def get_students(
    db: AsyncSession,
    department_id: uuid.UUID | None = None,
    semester_id: uuid.UUID | None = None,
    section: str | None = None,
    status: StudentStatus | None = None,
    search: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> dict:
    query = (
        select(Student)
        .join(Student.user)
        .options(
            selectinload(Student.user),
            selectinload(Student.department),
            selectinload(Student.semester),
        )
    )

    if department_id:
        query = query.where(Student.department_id == department_id)
    if semester_id:
        query = query.where(Student.semester_id == semester_id)
    if section:
        query = query.where(Student.section == section)
    if status:
        query = query.where(Student.status == status)
    if search:
        query = query.where(
            or_(
                User.full_name.ilike(f"%{search}%"),
                Student.roll_number.ilike(f"%{search}%"),
            )
        )

    count_result = await db.execute(select(func.count()).select_from(query.subquery()))
    total = count_result.scalar_one()

    query = query.order_by(Student.roll_number).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    students = list(result.scalars().all())

    return {"total": total, "page": page, "page_size": page_size, "items": students}


async def get_student_by_id(db: AsyncSession, student_id: uuid.UUID) -> Student:
    return await _get_student_with_relations(db, student_id)


async def get_student_by_user_id(db: AsyncSession, user_id: uuid.UUID) -> Student:
    result = await db.execute(
        select(Student)
        .where(Student.user_id == user_id)
        .options(selectinload(Student.user), selectinload(Student.department), selectinload(Student.semester))
    )
    student = result.scalar_one_or_none()
    if not student:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student profile not found")
    return student


async def update_student(db: AsyncSession, student_id: uuid.UUID, payload: StudentUpdate) -> Student:
    student = await _get_student_with_relations(db, student_id)

    update_data = payload.model_dump(exclude_none=True)
    full_name = update_data.pop("full_name", None)

    for field, value in update_data.items():
        setattr(student, field, value)

    if full_name:
        student.user.full_name = full_name

    await db.flush()
    return student


async def update_student_status(db: AsyncSession, student_id: uuid.UUID, payload: StudentStatusUpdate) -> Student:
    student = await _get_student_with_relations(db, student_id)
    student.status = payload.status
    await db.flush()
    return student


async def delete_student(db: AsyncSession, student_id: uuid.UUID) -> None:
    student = await _get_student_with_relations(db, student_id)
    student.status = StudentStatus.transferred
    student.user.is_active = False
    await db.flush()


async def _get_student_with_relations(db: AsyncSession, student_id: uuid.UUID) -> Student:
    result = await db.execute(
        select(Student)
        .where(Student.id == student_id)
        .options(selectinload(Student.user), selectinload(Student.department), selectinload(Student.semester))
    )
    student = result.scalar_one_or_none()
    if not student:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found")
    return student
