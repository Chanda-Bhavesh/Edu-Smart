"""
Notification service.

Used internally by other services to push in-app notifications.
Also handles listing, reading, and counting for the API layer.
"""
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import (
    Announcement, AnnouncementRead, Notification, NotificationType,
)
from app.schemas.notification import UnreadCount


# ── Internal helpers (called by other services) ────────────────────────────────

async def push(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    title: str,
    message: str,
    notification_type: NotificationType = NotificationType.general,
    reference_id: Optional[str] = None,
    reference_type: Optional[str] = None,
) -> Notification:
    """
    Create one in-app notification for a user.
    Call this from assignment, fee, attendance, leave services to notify users.
    """
    notif = Notification(
        user_id=user_id,
        title=title,
        message=message,
        notification_type=notification_type,
        reference_id=reference_id,
        reference_type=reference_type,
    )
    db.add(notif)
    await db.flush()  # don't commit — caller owns the transaction
    return notif


async def push_bulk(
    db: AsyncSession,
    *,
    user_ids: list[uuid.UUID],
    title: str,
    message: str,
    notification_type: NotificationType = NotificationType.general,
    reference_id: Optional[str] = None,
    reference_type: Optional[str] = None,
) -> int:
    """Push the same notification to multiple users at once. Returns count created."""
    for uid in user_ids:
        db.add(Notification(
            user_id=uid,
            title=title,
            message=message,
            notification_type=notification_type,
            reference_id=reference_id,
            reference_type=reference_type,
        ))
    await db.flush()
    return len(user_ids)


# ── API-facing functions ───────────────────────────────────────────────────────

async def get_my_notifications(
    db: AsyncSession,
    user_id: uuid.UUID,
    unread_only: bool = False,
    limit: int = 50,
    offset: int = 0,
) -> list[Notification]:
    q = select(Notification).where(Notification.user_id == user_id)
    if unread_only:
        q = q.where(Notification.is_read == False)
    q = q.order_by(Notification.created_at.desc()).offset(offset).limit(limit)
    result = await db.execute(q)
    return list(result.scalars().all())


async def mark_read(
    db: AsyncSession,
    notification_id: uuid.UUID,
    user_id: uuid.UUID,
) -> Notification:
    from fastapi import HTTPException
    result = await db.execute(
        select(Notification).where(
            Notification.id == notification_id,
            Notification.user_id == user_id,
        )
    )
    notif = result.scalar_one_or_none()
    if not notif:
        raise HTTPException(status_code=404, detail="Notification not found")

    if not notif.is_read:
        notif.is_read = True
        notif.read_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(notif)
    return notif


async def mark_all_read(
    db: AsyncSession,
    user_id: uuid.UUID,
) -> int:
    result = await db.execute(
        select(Notification).where(
            Notification.user_id == user_id,
            Notification.is_read == False,
        )
    )
    unread = result.scalars().all()
    now = datetime.now(timezone.utc)
    for notif in unread:
        notif.is_read = True
        notif.read_at = now
    await db.commit()
    return len(unread)


async def get_unread_count(
    db: AsyncSession,
    user_id: uuid.UUID,
) -> UnreadCount:
    # Unread in-app notifications
    notif_result = await db.execute(
        select(func.count(Notification.id)).where(
            Notification.user_id == user_id,
            Notification.is_read == False,
        )
    )
    unread_notifs = notif_result.scalar() or 0

    # Unread announcements: visible announcements minus ones user has read
    read_result = await db.execute(
        select(func.count(AnnouncementRead.id)).where(
            AnnouncementRead.user_id == user_id
        )
    )
    read_count = read_result.scalar() or 0

    # Total visible announcements for this user
    total_ann_result = await db.execute(
        select(func.count(Announcement.id)).where(Announcement.is_active == True)
    )
    total_visible = total_ann_result.scalar() or 0
    unread_anns = max(total_visible - read_count, 0)

    total = unread_notifs + unread_anns
    return UnreadCount(
        unread_notifications=unread_notifs,
        unread_announcements=unread_anns,
        total=total,
    )


async def delete_notification(
    db: AsyncSession,
    notification_id: uuid.UUID,
    user_id: uuid.UUID,
) -> None:
    from fastapi import HTTPException
    result = await db.execute(
        select(Notification).where(
            Notification.id == notification_id,
            Notification.user_id == user_id,
        )
    )
    notif = result.scalar_one_or_none()
    if not notif:
        raise HTTPException(status_code=404, detail="Notification not found")
    await db.delete(notif)
    await db.commit()
