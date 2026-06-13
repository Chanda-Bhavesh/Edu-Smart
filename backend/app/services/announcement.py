"""
Announcement service.

Admin creates announcements with a targeting rule.
The feed endpoint filters to show only announcements relevant to the current user.
Email dispatch runs in the background (FastAPI BackgroundTasks).
"""
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import BackgroundTasks, HTTPException, UploadFile
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.notification import (
    Announcement, AnnouncementRead, AnnouncementTarget,
    Notification, NotificationType,
)
from app.models.student import Student
from app.models.faculty import Faculty
from app.models.user import User, UserRole
from app.schemas.notification import (
    AnnouncementCreate, AnnouncementFeedItem, AnnouncementUpdate,
)
from app.utils.files import save_assignment_file  # reuse file saver
from pathlib import Path


def _now() -> datetime:
    return datetime.now(timezone.utc)


# ── Targeting helper ───────────────────────────────────────────────────────────

def _announcement_visible_to_user(a: Announcement, user: User, student: Optional[Student], faculty: Optional[Faculty]) -> bool:
    """Return True if the announcement should appear in this user's feed."""
    if not a.is_active:
        return False
    if a.expires_at and _now() > a.expires_at.replace(tzinfo=timezone.utc):
        return False

    t = a.target_type

    if t == AnnouncementTarget.all:
        return True

    if t == AnnouncementTarget.students:
        return user.role == UserRole.student

    if t == AnnouncementTarget.faculty:
        return user.role == UserRole.faculty

    if t == AnnouncementTarget.department:
        if user.role == UserRole.student and student:
            return student.department_id == a.department_id
        if user.role == UserRole.faculty and faculty:
            return faculty.department_id == a.department_id
        return False

    if t == AnnouncementTarget.department_students:
        return (user.role == UserRole.student and student is not None
                and student.department_id == a.department_id)

    if t == AnnouncementTarget.department_faculty:
        return (user.role == UserRole.faculty and faculty is not None
                and faculty.department_id == a.department_id)

    if t == AnnouncementTarget.semester_section:
        if user.role == UserRole.student and student:
            sem_match = student.semester_id == a.semester_id
            sec_match = (a.section is None) or (student.section == a.section)
            return sem_match and sec_match
        return False

    return False


# ── CRUD ───────────────────────────────────────────────────────────────────────

async def create_announcement(
    db: AsyncSession,
    payload: AnnouncementCreate,
    user_id: uuid.UUID,
    background_tasks: Optional[BackgroundTasks] = None,
) -> Announcement:
    ann = Announcement(
        title=payload.title,
        content=payload.content,
        target_type=payload.target_type,
        department_id=payload.department_id,
        semester_id=payload.semester_id,
        section=payload.section,
        target_role=payload.target_role,
        priority=payload.priority,
        send_email=payload.send_email,
        expires_at=payload.expires_at,
        created_by_id=user_id,
        published_at=_now(),
    )
    db.add(ann)
    await db.commit()
    await db.refresh(ann)

    # Auto-create in-app notifications for targeted users in the background
    if background_tasks:
        background_tasks.add_task(_create_announcement_notifications, ann.id)

    # Send emails if requested
    if payload.send_email and background_tasks:
        background_tasks.add_task(_send_announcement_emails, ann.id)

    return ann


async def _create_announcement_notifications(announcement_id: uuid.UUID) -> None:
    """
    Background task: create a Notification record for every targeted user.
    Runs after the HTTP response is returned to avoid blocking.
    """
    from app.database import AsyncSessionLocal
    from app.models.notification import Announcement, Notification, NotificationType

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Announcement).where(Announcement.id == announcement_id)
            .options(selectinload(Announcement.created_by))
        )
        ann = result.scalar_one_or_none()
        if not ann:
            return

        users_result = await db.execute(
            select(User).where(User.is_verified == True, User.is_active == True)
        )
        users = users_result.scalars().all()

        students_result = await db.execute(select(Student))
        students = {s.user_id: s for s in students_result.scalars().all()}

        faculty_result = await db.execute(select(Faculty))
        faculties = {f.user_id: f for f in faculty_result.scalars().all()}

        for user in users:
            student = students.get(user.id)
            faculty = faculties.get(user.id)
            if _announcement_visible_to_user(ann, user, student, faculty):
                notif = Notification(
                    user_id=user.id,
                    title=f"New Announcement: {ann.title}",
                    message=ann.content[:200],
                    notification_type=NotificationType.announcement,
                    reference_id=str(ann.id),
                    reference_type="announcement",
                )
                db.add(notif)

        await db.commit()


async def _send_announcement_emails(announcement_id: uuid.UUID) -> None:
    """Background task: email all targeted users."""
    import logging
    from app.database import AsyncSessionLocal
    from app.utils.email import send_welcome_email  # reuse SMTP connection

    logger = logging.getLogger("scms.email")

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Announcement).where(Announcement.id == announcement_id)
        )
        ann = result.scalar_one_or_none()
        if not ann:
            return

        users_result = await db.execute(
            select(User).where(User.is_verified == True, User.is_active == True)
        )
        users = users_result.scalars().all()
        students_map = {s.user_id: s for s in (await db.execute(select(Student))).scalars()}
        faculty_map = {f.user_id: f for f in (await db.execute(select(Faculty))).scalars()}

        for user in users:
            student = students_map.get(user.id)
            faculty = faculty_map.get(user.id)
            if _announcement_visible_to_user(ann, user, student, faculty):
                try:
                    import smtplib
                    from email.mime.multipart import MIMEMultipart
                    from email.mime.text import MIMEText
                    from app.config import settings

                    msg = MIMEMultipart("alternative")
                    msg["Subject"] = f"[{ann.priority.value.upper()}] {ann.title}"
                    msg["From"] = settings.mail_from
                    msg["To"] = user.email

                    html = f"""
                    <html><body>
                    <h2>{ann.title}</h2>
                    <p>{ann.content}</p>
                    <hr/>
                    <small>Smart Campus Management System</small>
                    </body></html>
                    """
                    msg.attach(MIMEText(html, "html"))

                    with smtplib.SMTP(settings.mail_host, settings.mail_port) as server:
                        if settings.mail_tls:
                            server.starttls()
                        if settings.mail_username:
                            server.login(settings.mail_username, settings.mail_password)
                        server.sendmail(settings.mail_from, user.email, msg.as_string())

                except Exception as exc:
                    logger.warning(f"Email failed for {user.email}: {exc}")


async def update_announcement(
    db: AsyncSession,
    announcement_id: uuid.UUID,
    payload: AnnouncementUpdate,
    user_id: uuid.UUID,
) -> Announcement:
    result = await db.execute(
        select(Announcement).where(Announcement.id == announcement_id)
    )
    ann = result.scalar_one_or_none()
    if not ann:
        raise HTTPException(status_code=404, detail="Announcement not found")
    if ann.created_by_id != user_id:
        raise HTTPException(status_code=403, detail="Not your announcement")

    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(ann, field, value)

    await db.commit()
    await db.refresh(ann)
    return ann


async def delete_announcement(
    db: AsyncSession,
    announcement_id: uuid.UUID,
    user_id: uuid.UUID,
) -> None:
    result = await db.execute(
        select(Announcement).where(Announcement.id == announcement_id)
    )
    ann = result.scalar_one_or_none()
    if not ann:
        raise HTTPException(status_code=404, detail="Announcement not found")
    if ann.created_by_id != user_id:
        raise HTTPException(status_code=403, detail="Not your announcement")

    await db.delete(ann)
    await db.commit()


async def toggle_pin(
    db: AsyncSession,
    announcement_id: uuid.UUID,
    user_id: uuid.UUID,
) -> Announcement:
    result = await db.execute(
        select(Announcement).where(Announcement.id == announcement_id)
    )
    ann = result.scalar_one_or_none()
    if not ann:
        raise HTTPException(status_code=404, detail="Announcement not found")

    ann.is_pinned = not ann.is_pinned
    await db.commit()
    await db.refresh(ann)
    return ann


async def upload_announcement_file(
    db: AsyncSession,
    announcement_id: uuid.UUID,
    file: UploadFile,
    user_id: uuid.UUID,
) -> Announcement:
    result = await db.execute(
        select(Announcement).where(Announcement.id == announcement_id)
    )
    ann = result.scalar_one_or_none()
    if not ann:
        raise HTTPException(status_code=404, detail="Announcement not found")
    if ann.created_by_id != user_id:
        raise HTTPException(status_code=403, detail="Not your announcement")

    # Reuse assignment file saver (same local upload logic)
    from app.utils.files import delete_file
    if ann.file_url:
        delete_file(ann.file_url)

    # Save to uploads/announcements/
    from pathlib import Path
    import uuid as _uuid
    from app.utils.files import UPLOAD_ROOT, ALLOWED_EXTENSIONS, MAX_FILE_SIZE
    from fastapi import HTTPException as FH

    ext = Path(file.filename or "file.bin").suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise FH(status_code=400, detail=f"File type '{ext}' not allowed")

    data = await file.read()
    if len(data) > MAX_FILE_SIZE:
        raise FH(status_code=413, detail="File exceeds 10 MB limit")

    dest_dir = UPLOAD_ROOT / "announcements" / str(announcement_id)
    dest_dir.mkdir(parents=True, exist_ok=True)
    unique_name = f"{_uuid.uuid4().hex}{ext}"
    (dest_dir / unique_name).write_bytes(data)

    ann.file_url = f"/uploads/announcements/{announcement_id}/{unique_name}"
    ann.file_name = file.filename or unique_name
    await db.commit()
    await db.refresh(ann)
    return ann


# ── Admin: list all ────────────────────────────────────────────────────────────

async def list_all_announcements(
    db: AsyncSession,
    active_only: bool = False,
) -> list[Announcement]:
    q = select(Announcement).options(selectinload(Announcement.created_by))
    if active_only:
        q = q.where(Announcement.is_active == True)
    q = q.order_by(Announcement.is_pinned.desc(), Announcement.published_at.desc())
    result = await db.execute(q)
    return list(result.scalars().all())


# ── Feed: user-specific ────────────────────────────────────────────────────────

async def get_announcement_feed(
    db: AsyncSession,
    current_user: User,
) -> list[AnnouncementFeedItem]:
    """Return active, non-expired announcements visible to this user, newest first, pinned on top."""

    # Load user's profile (student or faculty)
    student: Optional[Student] = None
    faculty: Optional[Faculty] = None

    if current_user.role == UserRole.student:
        s_result = await db.execute(select(Student).where(Student.user_id == current_user.id))
        student = s_result.scalar_one_or_none()
    elif current_user.role == UserRole.faculty:
        f_result = await db.execute(select(Faculty).where(Faculty.user_id == current_user.id))
        faculty = f_result.scalar_one_or_none()

    all_result = await db.execute(
        select(Announcement)
        .where(Announcement.is_active == True)
        .order_by(Announcement.is_pinned.desc(), Announcement.published_at.desc())
    )
    all_anns = all_result.scalars().all()

    # Load which ones this user has read
    reads_result = await db.execute(
        select(AnnouncementRead.announcement_id)
        .where(AnnouncementRead.user_id == current_user.id)
    )
    read_ids = {row[0] for row in reads_result.all()}

    items: list[AnnouncementFeedItem] = []
    for ann in all_anns:
        if not _announcement_visible_to_user(ann, current_user, student, faculty):
            continue
        items.append(
            AnnouncementFeedItem(
                id=ann.id,
                title=ann.title,
                content=ann.content,
                priority=ann.priority,
                is_pinned=ann.is_pinned,
                file_url=ann.file_url,
                published_at=ann.published_at,
                expires_at=ann.expires_at,
                is_read=ann.id in read_ids,
            )
        )
    return items


async def mark_announcement_read(
    db: AsyncSession,
    announcement_id: uuid.UUID,
    user_id: uuid.UUID,
) -> None:
    existing = await db.execute(
        select(AnnouncementRead).where(
            AnnouncementRead.announcement_id == announcement_id,
            AnnouncementRead.user_id == user_id,
        )
    )
    if not existing.scalar_one_or_none():
        db.add(AnnouncementRead(announcement_id=announcement_id, user_id=user_id))
        await db.commit()
