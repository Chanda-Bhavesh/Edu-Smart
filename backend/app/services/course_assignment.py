import uuid
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.course_assignment import CourseAssignment
from app.models.student import Student, StudentStatus
from app.models.subject import student_enrollments
from app.models.faculty import Faculty
from app.models.subject import Subject
from app.models.semester import Semester
from app.models.user import User
from app.schemas.course_assignment import CourseAssignmentCreate, CourseAssignmentUpdate


async def create_assignment(db: AsyncSession, payload: CourseAssignmentCreate) -> CourseAssignment:
    # Verify faculty exists
    faculty_result = await db.execute(select(Faculty).where(Faculty.id == payload.faculty_id))
    if not faculty_result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Faculty not found")

    # Verify subject exists
    subject_result = await db.execute(select(Subject).where(Subject.id == payload.subject_id))
    if not subject_result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subject not found")

    # Verify semester exists
    semester_result = await db.execute(select(Semester).where(Semester.id == payload.semester_id))
    if not semester_result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Semester not found")

    # Check: this section+subject+semester is not already assigned to another faculty
    conflict = await db.execute(
        select(CourseAssignment).where(
            CourseAssignment.subject_id == payload.subject_id,
            CourseAssignment.semester_id == payload.semester_id,
            CourseAssignment.section == payload.section,
            CourseAssignment.is_active == True,
        )
    )
    if conflict.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Section '{payload.section}' already has a faculty assigned for this subject and semester",
        )

    assignment = CourseAssignment(**payload.model_dump())
    db.add(assignment)
    await db.flush()
    return await _load(db, assignment.id)


async def get_all_assignments(
    db: AsyncSession,
    faculty_id: uuid.UUID | None = None,
    subject_id: uuid.UUID | None = None,
    semester_id: uuid.UUID | None = None,
    section: str | None = None,
    is_active: bool | None = None,
) -> list[CourseAssignment]:
    query = (
        select(CourseAssignment)
        .options(
            selectinload(CourseAssignment.faculty).selectinload(Faculty.user),
            selectinload(CourseAssignment.subject),
            selectinload(CourseAssignment.semester),
        )
    )

    if faculty_id:
        query = query.where(CourseAssignment.faculty_id == faculty_id)
    if subject_id:
        query = query.where(CourseAssignment.subject_id == subject_id)
    if semester_id:
        query = query.where(CourseAssignment.semester_id == semester_id)
    if section:
        query = query.where(CourseAssignment.section == section)
    if is_active is not None:
        query = query.where(CourseAssignment.is_active == is_active)

    result = await db.execute(query.order_by(CourseAssignment.section))
    return list(result.scalars().all())


async def get_assignment(db: AsyncSession, assignment_id: uuid.UUID) -> CourseAssignment:
    return await _load(db, assignment_id)


async def get_my_classes(db: AsyncSession, faculty_user_id: uuid.UUID) -> list[CourseAssignment]:
    """Return all active course assignments for the logged-in faculty."""
    faculty_result = await db.execute(select(Faculty).where(Faculty.user_id == faculty_user_id))
    faculty = faculty_result.scalar_one_or_none()
    if not faculty:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Faculty profile not found")

    return await get_all_assignments(db, faculty_id=faculty.id, is_active=True)


async def get_students_in_class(db: AsyncSession, assignment_id: uuid.UUID) -> dict:
    """
    Return all students who belong to the assignment's section+subject+semester.
    Used by faculty when opening attendance page for a class.
    """
    assignment = await _load(db, assignment_id)

    # Students who are:
    # 1. In the same semester as the assignment
    # 2. In the same section
    # 3. Enrolled in the same subject
    # 4. Currently active
    result = await db.execute(
        select(Student, User)
        .join(User, Student.user_id == User.id)
        .join(student_enrollments, student_enrollments.c.student_id == Student.id)
        .where(
            student_enrollments.c.subject_id == assignment.subject_id,
            Student.semester_id == assignment.semester_id,
            Student.section == assignment.section,
            Student.status == StudentStatus.active,
        )
        .order_by(Student.roll_number)
    )
    rows = result.all()

    students = [
        {
            "id": str(student.id),
            "roll_number": student.roll_number,
            "section": student.section,
            "full_name": user.full_name,
            "email": user.email,
        }
        for student, user in rows
    ]

    return {
        "assignment": assignment,
        "students": students,
        "total_students": len(students),
    }


async def update_assignment(db: AsyncSession, assignment_id: uuid.UUID, payload: CourseAssignmentUpdate) -> CourseAssignment:
    assignment = await _load(db, assignment_id)
    assignment.is_active = payload.is_active
    await db.flush()
    return assignment


async def delete_assignment(db: AsyncSession, assignment_id: uuid.UUID) -> None:
    assignment = await _load(db, assignment_id)
    await db.delete(assignment)


async def _load(db: AsyncSession, assignment_id: uuid.UUID) -> CourseAssignment:
    result = await db.execute(
        select(CourseAssignment)
        .where(CourseAssignment.id == assignment_id)
        .options(
            selectinload(CourseAssignment.faculty).selectinload(Faculty.user),
            selectinload(CourseAssignment.subject),
            selectinload(CourseAssignment.semester),
        )
    )
    assignment = result.scalar_one_or_none()
    if not assignment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course assignment not found")
    return assignment
