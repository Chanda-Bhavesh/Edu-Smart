"""
Announcements & Notifications endpoints.

Announcements (Admin: org_admin / dept_admin):
  POST   /announcements                    → create
  GET    /announcements                    → list all (admin view)
  PUT    /announcements/{id}               → edit
  DELETE /announcements/{id}               → delete
  PUT    /announcements/{id}/pin           → toggle pin
  POST   /announcements/{id}/file          → attach file

All users:
  GET    /announcements/feed               → my personalised announcement feed
  GET    /announcements/{id}               → view one announcement
  POST   /announcements/{id}/read          → mark as read

Notifications (all users):
  GET    /notifications                    → my notifications
  GET    /notifications/unread-count       → badge number
  PUT    /notifications/{id}/read          → mark one as read
  PUT    /notifications/read-all           → mark all as read
  DELETE /notifications/{id}               → delete one
"""
import uuid
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, File, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies.auth import get_current_admin, get_current_user
from app.models.user import User
from app.schemas.notification import (
    AnnouncementCreate, AnnouncementFeedItem,
    AnnouncementResponse, AnnouncementUpdate,
    NotificationResponse, UnreadCount,
)
from app.services import announcement as ann_service
from app.services import notification_service as notif_service

# ── Announcements ──────────────────────────────────────────────────────────────
ann_router = APIRouter(prefix="/announcements", tags=["Announcements"])


@ann_router.post("", response_model=AnnouncementResponse, status_code=status.HTTP_201_CREATED)
async def create_announcement(
    payload: AnnouncementCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    """
    Admin: create an announcement.
    Set target_type to control who sees it (all / students / faculty / department / etc.)
    Set send_email=true to also email all targeted users in the background.
    """
    return await ann_service.create_announcement(db, payload, current_user.id, background_tasks)


@ann_router.get("", response_model=list[AnnouncementResponse])
async def list_announcements(
    active_only: bool = Query(default=False),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    """Admin: list all announcements (admin view — no targeting filter)."""
    return await ann_service.list_all_announcements(db, active_only)


@ann_router.get("/feed", response_model=list[AnnouncementFeedItem])
async def announcement_feed(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    All users: personalised announcement feed.
    Returns only announcements relevant to the current user's role, department, and semester.
    Pinned announcements appear at the top.
    """
    return await ann_service.get_announcement_feed(db, current_user)


@ann_router.get("/{announcement_id}", response_model=AnnouncementResponse)
async def get_announcement(
    announcement_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """All users: view full details of one announcement."""
    from sqlalchemy import select
    from app.models.notification import Announcement
    result = await db.execute(select(Announcement).where(Announcement.id == announcement_id))
    ann = result.scalar_one_or_none()
    if not ann:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Announcement not found")
    return ann


@ann_router.put("/{announcement_id}", response_model=AnnouncementResponse)
async def update_announcement(
    announcement_id: uuid.UUID,
    payload: AnnouncementUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    """Admin: edit announcement title, content, priority, or active status."""
    return await ann_service.update_announcement(db, announcement_id, payload, current_user.id)


@ann_router.delete("/{announcement_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_announcement(
    announcement_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    """Admin: delete an announcement."""
    await ann_service.delete_announcement(db, announcement_id, current_user.id)


@ann_router.put("/{announcement_id}/pin", response_model=AnnouncementResponse)
async def toggle_pin(
    announcement_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    """Admin: pin or unpin an announcement (pinned announcements appear first in the feed)."""
    return await ann_service.toggle_pin(db, announcement_id, current_user.id)


@ann_router.post("/{announcement_id}/file", response_model=AnnouncementResponse)
async def upload_file(
    announcement_id: uuid.UUID,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    """Admin: attach a file (PDF, image, etc.) to an announcement."""
    return await ann_service.upload_announcement_file(db, announcement_id, file, current_user.id)


@ann_router.post("/{announcement_id}/read", status_code=status.HTTP_204_NO_CONTENT)
async def mark_read(
    announcement_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """User: mark an announcement as read (clears the unread badge)."""
    await ann_service.mark_announcement_read(db, announcement_id, current_user.id)


# ── Notifications ──────────────────────────────────────────────────────────────
notif_router = APIRouter(prefix="/notifications", tags=["Notifications"])


@notif_router.get("/unread-count", response_model=UnreadCount)
async def unread_count(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    All users: get unread badge count.
    Returns separate counts for in-app notifications and unread announcements.
    The frontend can show this number on the notification bell icon.
    """
    return await notif_service.get_unread_count(db, current_user.id)


@notif_router.get("", response_model=list[NotificationResponse])
async def my_notifications(
    unread_only: bool = Query(default=False),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """All users: list my in-app notifications (newest first, paginated)."""
    return await notif_service.get_my_notifications(
        db, current_user.id, unread_only, limit, offset
    )


@notif_router.put("/read-all", status_code=status.HTTP_200_OK)
async def mark_all_read(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """All users: mark all my notifications as read."""
    count = await notif_service.mark_all_read(db, current_user.id)
    return {"marked_read": count}


@notif_router.put("/{notification_id}/read", response_model=NotificationResponse)
async def mark_one_read(
    notification_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """All users: mark one notification as read."""
    return await notif_service.mark_read(db, notification_id, current_user.id)


@notif_router.delete("/{notification_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_notification(
    notification_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """All users: delete a notification from my list."""
    await notif_service.delete_notification(db, notification_id, current_user.id)
