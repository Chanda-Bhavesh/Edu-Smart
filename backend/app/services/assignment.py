"""
Assignment Management service.

Faculty flow:  create (draft) → upload file (optional) → publish → close → grade → publish grades
Student flow:  view published → submit file/text → view grade
"""
import uuid
from datetime import datetime, timezone

from fastapi import HTTPException, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.assignment import Assignment, AssignmentStatus, Submission, SubmissionStatus
from app.models.course_assignment import CourseAssignment
from app.models.faculty import Faculty
from app.models.student import Student
from app.models.subject import student_enrollments
from app.schemas.assignment import (
    AssignmentCreate, AssignmentListItem, AssignmentStats,
    AssignmentUpdate, GradeSubmission, SubmissionWithStudent,
)
from app.utils.files import (
    delete_file, save_assignment_file, save_submission_file,
)


# ── helpers ────────────────────────────────────────────────────────────────────

def _now() -> datetime:
    return datetime.now(timezone.utc)


async def _get_faculty(db: AsyncSession, user_id: uuid.UUID) -> Faculty:
    result = await db.execute(select(Faculty).where(Faculty.user_id == user_id))
    faculty = result.scalar_one_or_none()
    if not faculty:
        raise HTTPException(status_code=404, detail="Faculty profile not found")
    return faculty


async def _get_student(db: AsyncSession, user_id: uuid.UUID) -> Student:
    result = await db.execute(select(Student).where(Student.user_id == user_id))
    student = result.scalar_one_or_none()
    if not student:
        raise HTTPException(status_code=404, detail="Student profile not found")
    return student


async def _get_assignment(db: AsyncSession, assignment_id: uuid.UUID) -> Assignment:
    result = await db.execute(
        select(Assignment).where(Assignment.id == assignment_id)
    )
    assignment = result.scalar_one_or_none()
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")
    return assignment


# ── Faculty: Create / Edit / Delete ───────────────────────────────────────────

async def create_assignment(
    db: AsyncSession,
    payload: AssignmentCreate,
    user_id: uuid.UUID,
) -> Assignment:
    faculty = await _get_faculty(db, user_id)

    assignment = Assignment(
        title=payload.title,
        description=payload.description,
        subject_id=payload.subject_id,
        faculty_id=faculty.id,
        course_assignment_id=payload.course_assignment_id,
        semester_id=payload.semester_id,
        deadline=payload.deadline,
        max_marks=payload.max_marks,
        allow_late_submission=payload.allow_late_submission,
        status=AssignmentStatus.draft,
    )
    db.add(assignment)
    await db.commit()
    await db.refresh(assignment)
    return assignment


async def upload_assignment_file(
    db: AsyncSession,
    assignment_id: uuid.UUID,
    file: UploadFile,
    user_id: uuid.UUID,
) -> Assignment:
    faculty = await _get_faculty(db, user_id)
    assignment = await _get_assignment(db, assignment_id)

    if assignment.faculty_id != faculty.id:
        raise HTTPException(status_code=403, detail="Not your assignment")
    if assignment.status == AssignmentStatus.closed:
        raise HTTPException(status_code=400, detail="Cannot modify a closed assignment")

    # Delete old file if replacing
    if assignment.file_url:
        delete_file(assignment.file_url)

    file_url, file_name = await save_assignment_file(file, assignment_id)
    assignment.file_url = file_url
    assignment.file_name = file_name
    await db.commit()
    await db.refresh(assignment)
    return assignment


async def update_assignment(
    db: AsyncSession,
    assignment_id: uuid.UUID,
    payload: AssignmentUpdate,
    user_id: uuid.UUID,
) -> Assignment:
    faculty = await _get_faculty(db, user_id)
    assignment = await _get_assignment(db, assignment_id)

    if assignment.faculty_id != faculty.id:
        raise HTTPException(status_code=403, detail="Not your assignment")
    if assignment.status == AssignmentStatus.closed:
        raise HTTPException(status_code=400, detail="Cannot edit a closed assignment")

    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(assignment, field, value)

    await db.commit()
    await db.refresh(assignment)
    return assignment


async def delete_assignment(
    db: AsyncSession,
    assignment_id: uuid.UUID,
    user_id: uuid.UUID,
) -> None:
    faculty = await _get_faculty(db, user_id)
    assignment = await _get_assignment(db, assignment_id)

    if assignment.faculty_id != faculty.id:
        raise HTTPException(status_code=403, detail="Not your assignment")
    if assignment.status != AssignmentStatus.draft:
        raise HTTPException(
            status_code=400,
            detail="Only draft assignments can be deleted. Close it first.",
        )

    if assignment.file_url:
        delete_file(assignment.file_url)

    await db.delete(assignment)
    await db.commit()


# ── Faculty: Publish / Close ───────────────────────────────────────────────────

async def publish_assignment(
    db: AsyncSession,
    assignment_id: uuid.UUID,
    user_id: uuid.UUID,
) -> Assignment:
    faculty = await _get_faculty(db, user_id)
    assignment = await _get_assignment(db, assignment_id)

    if assignment.faculty_id != faculty.id:
        raise HTTPException(status_code=403, detail="Not your assignment")
    if assignment.status != AssignmentStatus.draft:
        raise HTTPException(status_code=400, detail="Only draft assignments can be published")

    assignment.status = AssignmentStatus.published
    assignment.published_at = _now()
    await db.commit()
    await db.refresh(assignment)
    return assignment


async def close_assignment(
    db: AsyncSession,
    assignment_id: uuid.UUID,
    user_id: uuid.UUID,
) -> Assignment:
    faculty = await _get_faculty(db, user_id)
    assignment = await _get_assignment(db, assignment_id)

    if assignment.faculty_id != faculty.id:
        raise HTTPException(status_code=403, detail="Not your assignment")
    if assignment.status != AssignmentStatus.published:
        raise HTTPException(status_code=400, detail="Only published assignments can be closed")

    assignment.status = AssignmentStatus.closed
    await db.commit()
    await db.refresh(assignment)
    return assignment


# ── Faculty: List / Get assignments ───────────────────────────────────────────

async def get_faculty_assignments(
    db: AsyncSession,
    user_id: uuid.UUID,
    subject_id: uuid.UUID | None = None,
    status_filter: AssignmentStatus | None = None,
) -> list[Assignment]:
    faculty = await _get_faculty(db, user_id)

    q = select(Assignment).where(Assignment.faculty_id == faculty.id)
    if subject_id:
        q = q.where(Assignment.subject_id == subject_id)
    if status_filter:
        q = q.where(Assignment.status == status_filter)
    q = q.order_by(Assignment.deadline.asc())

    result = await db.execute(q)
    return list(result.scalars().all())


# ── Faculty: View all submissions for an assignment ────────────────────────────

async def get_assignment_submissions(
    db: AsyncSession,
    assignment_id: uuid.UUID,
    user_id: uuid.UUID,
) -> list[SubmissionWithStudent]:
    faculty = await _get_faculty(db, user_id)
    assignment = await _get_assignment(db, assignment_id)

    if assignment.faculty_id != faculty.id:
        raise HTTPException(status_code=403, detail="Not your assignment")

    result = await db.execute(
        select(Submission)
        .where(Submission.assignment_id == assignment_id)
        .options(selectinload(Submission.student).selectinload(Student.user))
        .order_by(Submission.submitted_at.asc())
    )
    submissions = result.scalars().all()

    items: list[SubmissionWithStudent] = []
    for sub in submissions:
        item = SubmissionWithStudent.model_validate(sub)
        if sub.student and sub.student.user:
            item.student_name = (
                f"{sub.student.user.first_name} {sub.student.user.last_name}"
            )
            item.roll_number = sub.student.roll_number
        items.append(item)
    return items


# ── Faculty: Grade ─────────────────────────────────────────────────────────────

async def grade_submission(
    db: AsyncSession,
    submission_id: uuid.UUID,
    payload: GradeSubmission,
    user_id: uuid.UUID,
) -> Submission:
    faculty = await _get_faculty(db, user_id)
    result = await db.execute(
        select(Submission)
        .where(Submission.id == submission_id)
        .options(selectinload(Submission.assignment))
    )
    submission = result.scalar_one_or_none()
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")

    if submission.assignment.faculty_id != faculty.id:
        raise HTTPException(status_code=403, detail="Not your assignment")
    if submission.assignment.status not in (AssignmentStatus.closed, AssignmentStatus.graded):
        raise HTTPException(status_code=400, detail="Assignment must be closed before grading")
    if payload.marks > submission.assignment.max_marks:
        raise HTTPException(
            status_code=400,
            detail=f"Marks exceed max_marks ({submission.assignment.max_marks})",
        )

    submission.marks = payload.marks
    submission.feedback = payload.feedback
    submission.status = SubmissionStatus.graded
    submission.graded_at = _now()
    submission.graded_by_id = faculty.id

    await db.commit()
    await db.refresh(submission)
    return submission


async def publish_grades(
    db: AsyncSession,
    assignment_id: uuid.UUID,
    user_id: uuid.UUID,
) -> Assignment:
    """Mark assignment as graded — signals students they can view grades."""
    faculty = await _get_faculty(db, user_id)
    assignment = await _get_assignment(db, assignment_id)

    if assignment.faculty_id != faculty.id:
        raise HTTPException(status_code=403, detail="Not your assignment")
    if assignment.status != AssignmentStatus.closed:
        raise HTTPException(status_code=400, detail="Assignment must be closed first")

    assignment.status = AssignmentStatus.graded
    await db.commit()
    await db.refresh(assignment)
    return assignment


# ── Assignment statistics ──────────────────────────────────────────────────────

async def get_assignment_stats(
    db: AsyncSession,
    assignment_id: uuid.UUID,
    user_id: uuid.UUID,
) -> AssignmentStats:
    faculty = await _get_faculty(db, user_id)
    assignment = await _get_assignment(db, assignment_id)

    if assignment.faculty_id != faculty.id:
        raise HTTPException(status_code=403, detail="Not your assignment")

    # Count total enrolled students
    total_q = (
        select(func.count())
        .select_from(student_enrollments)
        .where(student_enrollments.c.subject_id == assignment.subject_id)
    )
    total_result = await db.execute(total_q)
    total = total_result.scalar() or 0

    # Aggregate submission data
    agg_q = select(
        func.count(Submission.id).label("submitted"),
        func.sum(
            (Submission.is_late == True).cast(type_=__import__("sqlalchemy").Integer)
        ).label("late"),
        func.sum(
            (Submission.status == SubmissionStatus.graded).cast(
                type_=__import__("sqlalchemy").Integer
            )
        ).label("graded"),
        func.avg(Submission.marks).label("avg_marks"),
    ).where(Submission.assignment_id == assignment_id)

    agg_result = await db.execute(agg_q)
    row = agg_result.one()

    submitted = row.submitted or 0
    late = int(row.late or 0)
    graded = int(row.graded or 0)
    avg = float(row.avg_marks) if row.avg_marks else None

    return AssignmentStats(
        assignment_id=assignment_id,
        title=assignment.title,
        total_students=total,
        submitted=submitted,
        not_submitted=max(total - submitted, 0),
        late_submissions=late,
        graded=graded,
        average_marks=avg,
        max_marks=assignment.max_marks,
    )


# ── Student: View assignments ──────────────────────────────────────────────────

async def get_student_assignments(
    db: AsyncSession,
    user_id: uuid.UUID,
    subject_id: uuid.UUID | None = None,
) -> list[AssignmentListItem]:
    """
    Return published/closed/graded assignments for subjects the student is enrolled in.
    Each item shows whether the student has already submitted and their marks.
    """
    student = await _get_student(db, user_id)

    # Assignments visible to this student (via enrollment or semester+section via CourseAssignment)
    enr_sub_q = (
        select(student_enrollments.c.subject_id)
        .where(student_enrollments.c.student_id == student.id)
    )

    q = (
        select(Assignment)
        .where(
            Assignment.subject_id.in_(enr_sub_q),
            Assignment.status.in_(
                [AssignmentStatus.published, AssignmentStatus.closed, AssignmentStatus.graded]
            ),
        )
    )
    if subject_id:
        q = q.where(Assignment.subject_id == subject_id)
    q = q.order_by(Assignment.deadline.asc())

    result = await db.execute(q)
    assignments = result.scalars().all()

    items: list[AssignmentListItem] = []
    for a in assignments:
        # Check if student has submitted
        sub_result = await db.execute(
            select(Submission).where(
                Submission.assignment_id == a.id,
                Submission.student_id == student.id,
            )
        )
        sub = sub_result.scalar_one_or_none()

        items.append(
            AssignmentListItem(
                id=a.id,
                title=a.title,
                subject_id=a.subject_id,
                deadline=a.deadline,
                max_marks=a.max_marks,
                status=a.status,
                file_url=a.file_url,
                submission_status=sub.status if sub else None,
                marks=sub.marks if (sub and a.status == AssignmentStatus.graded) else None,
                is_late=sub.is_late if sub else None,
            )
        )
    return items


# ── Student: Submit ────────────────────────────────────────────────────────────

async def submit_assignment(
    db: AsyncSession,
    assignment_id: uuid.UUID,
    content: str | None,
    file: UploadFile | None,
    user_id: uuid.UUID,
) -> Submission:
    student = await _get_student(db, user_id)
    assignment = await _get_assignment(db, assignment_id)

    if assignment.status == AssignmentStatus.draft:
        raise HTTPException(status_code=400, detail="Assignment is not yet published")
    if assignment.status in (AssignmentStatus.closed, AssignmentStatus.graded):
        if not assignment.allow_late_submission:
            raise HTTPException(status_code=400, detail="Assignment is closed for submissions")

    if not content and not file:
        raise HTTPException(status_code=400, detail="Provide a file or text content to submit")

    now = _now()
    is_late = now > assignment.deadline.replace(tzinfo=timezone.utc)

    # Check existing submission
    existing_result = await db.execute(
        select(Submission).where(
            Submission.assignment_id == assignment_id,
            Submission.student_id == student.id,
        )
    )
    existing = existing_result.scalar_one_or_none()

    if existing:
        # Allow resubmission only before deadline
        if is_late and not assignment.allow_late_submission:
            raise HTTPException(status_code=400, detail="Resubmission not allowed after deadline")

        if file and existing.file_url:
            delete_file(existing.file_url)

        file_url = existing.file_url
        file_name = existing.file_name
        if file:
            file_url, file_name = await save_submission_file(file, existing.id)

        existing.file_url = file_url
        existing.file_name = file_name
        existing.content = content if content else existing.content
        existing.submitted_at = now
        existing.is_late = is_late
        existing.status = SubmissionStatus.resubmitted
        # Reset grade on resubmission
        existing.marks = None
        existing.feedback = None
        existing.graded_at = None
        existing.graded_by_id = None

        await db.commit()
        await db.refresh(existing)
        return existing

    # New submission — create first to get ID for file path
    sub = Submission(
        assignment_id=assignment_id,
        student_id=student.id,
        content=content,
        submitted_at=now,
        is_late=is_late,
        status=SubmissionStatus.late if is_late else SubmissionStatus.submitted,
    )
    db.add(sub)
    await db.flush()  # get sub.id

    if file:
        file_url, file_name = await save_submission_file(file, sub.id)
        sub.file_url = file_url
        sub.file_name = file_name

    await db.commit()
    await db.refresh(sub)
    return sub


# ── Student: View my submission ────────────────────────────────────────────────

async def get_my_submission(
    db: AsyncSession,
    assignment_id: uuid.UUID,
    user_id: uuid.UUID,
) -> Submission:
    student = await _get_student(db, user_id)
    result = await db.execute(
        select(Submission).where(
            Submission.assignment_id == assignment_id,
            Submission.student_id == student.id,
        )
    )
    sub = result.scalar_one_or_none()
    if not sub:
        raise HTTPException(status_code=404, detail="No submission found for this assignment")
    return sub
