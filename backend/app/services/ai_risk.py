"""
AI Risk & Performance Prediction service.

Attendance Risk:
  - Computes current attendance % per subject
  - Projects whether student can recover to 75% with remaining sessions
  - Produces a risk score (0-100) and risk level

Performance Prediction:
  - Weighted score: attendance 30% + assignment avg 70%
  - Maps to letter grade and failure risk category
  - Identifies concerning subjects and strengths

No external ML model needed on first run — pure rule-based math.
Predictions are optionally persisted to ai_risk_predictions for fast retrieval.
"""
import math
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException
from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.ai_prediction import AIRiskPrediction, RiskLevel
from app.models.assignment import Assignment, AssignmentStatus, Submission
from app.models.attendance import Attendance, AttendanceStatus
from app.models.course_assignment import CourseAssignment
from app.models.student import Student
from app.models.subject import Subject, student_enrollments
from app.models.timetable import TimetableSlot
from app.schemas.ai import (
    AtRiskSummary, PerformancePrediction, StudentRiskReport,
    SubjectPerformancePrediction, SubjectRisk,
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _risk_level(pct: float) -> RiskLevel:
    if pct >= 85:
        return RiskLevel.low
    if pct >= 75:
        return RiskLevel.medium
    if pct >= 65:
        return RiskLevel.high
    return RiskLevel.critical


def _risk_score(pct: float) -> float:
    """
    0 = perfectly safe, 100 = worst case.
    Grows sharply below 75%.
    """
    if pct >= 85:
        return max(0.0, (85 - pct))
    if pct >= 75:
        return 15 + (85 - pct) * 1.5
    return min(100.0, 30 + (75 - pct) * 2.8)


def _make_recommendation(
    pct: float,
    needed: int,
    remaining: int,
    recoverable: bool,
    subject: str,
) -> str:
    if pct >= 85:
        return f"Good standing in {subject}. Keep it up."
    if pct >= 75:
        return (
            f"{subject}: Safe but approaching the 75% threshold. "
            f"Don't miss more than {remaining - needed} more sessions."
        )
    if recoverable:
        return (
            f"{subject}: Below 75%. You must attend the next {needed} consecutive "
            f"sessions to recover. {remaining} sessions remain this semester."
        )
    return (
        f"{subject}: CRITICAL — even attending all remaining {remaining} sessions "
        f"is not enough to reach 75%. Contact your advisor immediately."
    )


# ── Student Risk Report ────────────────────────────────────────────────────────

async def compute_student_risk(
    db: AsyncSession,
    student_id: uuid.UUID,
    persist: bool = True,
) -> StudentRiskReport:
    """
    Compute full risk report for one student.
    If persist=True, upserts results into ai_risk_predictions.
    """
    s_result = await db.execute(
        select(Student)
        .where(Student.id == student_id)
        .options(
            selectinload(Student.user),
            selectinload(Student.department),
            selectinload(Student.semester),
        )
    )
    student = s_result.scalar_one_or_none()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    # Attendance per subject
    att_q = (
        select(
            Subject.id,
            Subject.name,
            Subject.code,
            func.count(Attendance.id).label("total"),
            func.sum(
                case((Attendance.status == AttendanceStatus.present, 1), else_=0)
            ).label("present"),
        )
        .join(TimetableSlot, Attendance.timetable_slot_id == TimetableSlot.id)
        .join(CourseAssignment, TimetableSlot.course_assignment_id == CourseAssignment.id)
        .join(Subject, CourseAssignment.subject_id == Subject.id)
        .where(Attendance.student_id == student_id)
        .group_by(Subject.id, Subject.name, Subject.code)
    )
    att_rows = (await db.execute(att_q)).all()

    # Enrolled subjects total slots (to estimate remaining)
    enrolled_q = (
        select(
            Subject.id,
            func.count(TimetableSlot.id).label("total_slots"),
        )
        .join(student_enrollments, Subject.id == student_enrollments.c.subject_id)
        .join(
            CourseAssignment,
            (CourseAssignment.subject_id == Subject.id)
            & (CourseAssignment.semester_id == student.semester_id),
        )
        .join(TimetableSlot, TimetableSlot.course_assignment_id == CourseAssignment.id)
        .where(
            student_enrollments.c.student_id == student_id,
            TimetableSlot.is_active == True,
        )
        .group_by(Subject.id)
    )
    slots_map = {
        row.id: row.total_slots
        for row in (await db.execute(enrolled_q)).all()
    }

    subject_risks: list[SubjectRisk] = []
    total_present = 0
    total_sessions = 0

    for row in att_rows:
        t = row.total or 0
        p = int(row.present or 0)
        total_present += p
        total_sessions += t

        pct = round((p / t * 100) if t > 0 else 0.0, 1)

        # Estimate remaining from total slots - done
        total_planned = slots_map.get(row.id, t)
        remaining = max(total_planned - t, 0)

        # Sessions needed: ceil(0.75 * total_planned) - p
        need_for_75 = math.ceil(0.75 * total_planned) - p
        need_for_75 = max(need_for_75, 0)
        recoverable = need_for_75 <= remaining

        level = _risk_level(pct)
        score = round(_risk_score(pct), 1)
        rec = _make_recommendation(pct, need_for_75, remaining, recoverable, row.name)

        subject_risks.append(SubjectRisk(
            subject_id=row.id,
            subject_name=row.name,
            subject_code=row.code,
            current_attendance_pct=pct,
            sessions_attended=p,
            total_sessions=t,
            sessions_remaining=remaining,
            sessions_needed_for_75=need_for_75,
            is_recoverable=recoverable,
            risk_level=level,
            risk_score=score,
            recommendation=rec,
        ))

        if persist:
            # Upsert into ai_risk_predictions
            existing = await db.execute(
                select(AIRiskPrediction).where(
                    AIRiskPrediction.student_id == student_id,
                    AIRiskPrediction.subject_id == row.id,
                )
            )
            pred = existing.scalar_one_or_none()
            if not pred:
                pred = AIRiskPrediction(student_id=student_id, subject_id=row.id)
                db.add(pred)
            pred.risk_level = level
            pred.risk_score = score
            pred.current_attendance_pct = pct
            pred.sessions_attended = p
            pred.total_sessions = t
            pred.sessions_remaining = remaining
            pred.sessions_needed_for_75 = need_for_75
            pred.is_recoverable = recoverable
            pred.recommendation = rec
            pred.predicted_at = _now()

    overall_pct = round((total_present / total_sessions * 100) if total_sessions > 0 else 0, 1)
    overall_level = _risk_level(overall_pct)

    critical = sum(1 for r in subject_risks if r.risk_level == RiskLevel.critical)
    at_risk = sum(1 for r in subject_risks if r.risk_level in (RiskLevel.high, RiskLevel.critical))
    safe = sum(1 for r in subject_risks if r.risk_level in (RiskLevel.low, RiskLevel.medium))

    if persist:
        await db.commit()

    student_name = (
        student.user.full_name
        if student.user else "Unknown"
    )

    return StudentRiskReport(
        student_id=student_id,
        student_name=student_name,
        roll_number=student.roll_number,
        department=student.department.name if student.department else "N/A",
        semester=student.semester.number if student.semester else 0,
        section=student.section or "",
        overall_attendance_pct=overall_pct,
        overall_risk_level=overall_level,
        subject_risks=subject_risks,
        critical_subjects=critical,
        at_risk_subjects=at_risk,
        safe_subjects=safe,
        predicted_at=_now(),
    )


# ── Admin/Faculty: all at-risk students ───────────────────────────────────────

async def get_at_risk_students(
    db: AsyncSession,
    semester_id: Optional[uuid.UUID] = None,
    department_id: Optional[uuid.UUID] = None,
    min_level: RiskLevel = RiskLevel.high,
) -> list[AtRiskSummary]:
    """
    Return students whose latest stored risk prediction meets min_level.
    Falls back to computing on-the-fly from stored predictions.
    """
    levels_to_include = {
        RiskLevel.high: [RiskLevel.high, RiskLevel.critical],
        RiskLevel.medium: [RiskLevel.medium, RiskLevel.high, RiskLevel.critical],
        RiskLevel.low: list(RiskLevel),
        RiskLevel.critical: [RiskLevel.critical],
    }[min_level]

    q = (
        select(
            Student.id,
            Student.roll_number,
            Student.section,
            func.avg(AIRiskPrediction.current_attendance_pct).label("overall_pct"),
            func.max(AIRiskPrediction.risk_score).label("max_score"),
            func.sum(
                case(
                    (AIRiskPrediction.risk_level == RiskLevel.critical, 1),
                    else_=0,
                )
            ).label("critical_count"),
        )
        .join(Student, AIRiskPrediction.student_id == Student.id)
        .where(AIRiskPrediction.risk_level.in_(levels_to_include))
        .group_by(Student.id, Student.roll_number, Student.section)
        .order_by(func.max(AIRiskPrediction.risk_score).desc())
    )
    if semester_id:
        q = q.where(Student.semester_id == semester_id)
    if department_id:
        q = q.where(Student.department_id == department_id)

    rows = (await db.execute(q)).all()

    # Load names
    student_ids = [r.id for r in rows]
    if not student_ids:
        return []

    users_result = await db.execute(
        select(Student)
        .where(Student.id.in_(student_ids))
        .options(selectinload(Student.user))
    )
    student_map = {s.id: s for s in users_result.scalars().all()}

    items: list[AtRiskSummary] = []
    for row in rows:
        s = student_map.get(row.id)
        name = (
            f"{s.user.first_name} {s.user.last_name}"
            if s and s.user else "Unknown"
        )
        overall_pct = round(float(row.overall_pct or 0), 1)
        items.append(AtRiskSummary(
            student_id=row.id,
            student_name=name,
            roll_number=row.roll_number,
            section=row.section or "",
            overall_attendance_pct=overall_pct,
            overall_risk_level=_risk_level(overall_pct),
            critical_subject_count=int(row.critical_count or 0),
        ))
    return items


# ── Performance Prediction ─────────────────────────────────────────────────────

def _grade(score: float) -> str:
    if score >= 90: return "A"
    if score >= 80: return "B"
    if score >= 70: return "C"
    if score >= 60: return "D"
    return "F"


async def predict_performance(
    db: AsyncSession,
    student_id: uuid.UUID,
) -> PerformancePrediction:
    s_result = await db.execute(
        select(Student)
        .where(Student.id == student_id)
        .options(
            selectinload(Student.user),
            selectinload(Student.department),
        )
    )
    student = s_result.scalar_one_or_none()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    # Attendance per subject
    att_q = (
        select(
            Subject.id,
            Subject.name,
            func.count(Attendance.id).label("total"),
            func.sum(
                case((Attendance.status == AttendanceStatus.present, 1), else_=0)
            ).label("present"),
        )
        .join(TimetableSlot, Attendance.timetable_slot_id == TimetableSlot.id)
        .join(CourseAssignment, TimetableSlot.course_assignment_id == CourseAssignment.id)
        .join(Subject, CourseAssignment.subject_id == Subject.id)
        .where(Attendance.student_id == student_id)
        .group_by(Subject.id, Subject.name)
    )
    att_map = {
        row.id: {
            "name": row.name,
            "pct": round((int(row.present or 0) / row.total * 100) if row.total else 0, 1),
        }
        for row in (await db.execute(att_q)).all()
    }

    # Assignment avg per subject
    asgn_q = (
        select(
            Assignment.subject_id,
            Subject.name,
            func.count(Submission.id).label("submitted"),
            func.count(Assignment.id).label("total"),
            func.avg(
                case(
                    (Submission.marks.isnot(None), Submission.marks * 100.0 / Assignment.max_marks),
                    else_=None,
                )
            ).label("avg_pct"),
        )
        .join(Subject, Assignment.subject_id == Subject.id)
        .outerjoin(
            Submission,
            (Submission.assignment_id == Assignment.id)
            & (Submission.student_id == student_id),
        )
        .where(
            Assignment.subject_id.in_(
                select(student_enrollments.c.subject_id).where(
                    student_enrollments.c.student_id == student_id
                )
            ),
            Assignment.status.in_([
                AssignmentStatus.closed, AssignmentStatus.graded
            ]),
        )
        .group_by(Assignment.subject_id, Subject.name)
    )
    asgn_rows = (await db.execute(asgn_q)).all()

    subject_preds: list[SubjectPerformancePrediction] = []
    weighted_scores: list[float] = []
    concerns: list[str] = []
    strengths: list[str] = []

    for row in asgn_rows:
        att_info = att_map.get(row.subject_id, {"name": row.name, "pct": 0})
        att_pct = att_info["pct"]
        marks_pct = float(row.avg_pct or 0)
        weighted = round(att_pct * 0.30 + marks_pct * 0.70, 1)
        grade = _grade(weighted)
        weighted_scores.append(weighted)

        if att_pct < 75:
            concerns.append(f"Low attendance in {row.name} ({att_pct}%)")
        if marks_pct < 50 and row.submitted > 0:
            concerns.append(f"Low assignment scores in {row.name} ({marks_pct:.1f}%)")
        if int(row.submitted) < int(row.total):
            missed = int(row.total) - int(row.submitted)
            concerns.append(f"{missed} unsubmitted assignment(s) in {row.name}")
        if weighted >= 80:
            strengths.append(f"{row.name}: strong performance ({grade}, {weighted}%)")

        subject_preds.append(SubjectPerformancePrediction(
            subject_id=row.subject_id,
            subject_name=row.name,
            attendance_pct=att_pct,
            avg_marks_pct=round(marks_pct, 1),
            weighted_score=weighted,
            predicted_grade=grade,
            assignments_submitted=int(row.submitted),
            assignments_total=int(row.total),
        ))

    overall = round(sum(weighted_scores) / len(weighted_scores), 1) if weighted_scores else 0.0
    overall_grade = _grade(overall)

    if overall < 60 or any("CRITICAL" in c for c in concerns):
        failure_risk = "high"
    elif overall < 70 or len(concerns) > 2:
        failure_risk = "medium"
    else:
        failure_risk = "low"

    student_name = (
        student.user.full_name
        if student.user else "Unknown"
    )

    return PerformancePrediction(
        student_id=student_id,
        student_name=student_name,
        roll_number=student.roll_number,
        overall_weighted_score=overall,
        predicted_overall_grade=overall_grade,
        failure_risk=failure_risk,
        subject_predictions=subject_preds,
        key_concerns=concerns,
        strengths=strengths,
        generated_at=_now(),
    )
