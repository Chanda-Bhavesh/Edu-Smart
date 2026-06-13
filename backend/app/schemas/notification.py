import uuid
from datetime import datetime
from typing import Optional, Any

from pydantic import BaseModel, Field, model_validator

from app.models.notification import (
    AnnouncementPriority, AnnouncementTarget, NotificationType,
)


# ── Announcement schemas ───────────────────────────────────────────────────────

class AnnouncementCreate(BaseModel):
    title: str = Field(..., min_length=3, max_length=255)
    content: str = Field(..., min_length=10)
    target_type: AnnouncementTarget = AnnouncementTarget.all
    department_id: Optional[uuid.UUID] = None
    semester_id: Optional[uuid.UUID] = None
    section: Optional[str] = None
    target_role: Optional[str] = None
    priority: AnnouncementPriority = AnnouncementPriority.normal
    send_email: bool = False
    expires_at: Optional[datetime] = None


class AnnouncementUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=3, max_length=255)
    content: Optional[str] = Field(default=None, min_length=10)
    priority: Optional[AnnouncementPriority] = None
    is_active: Optional[bool] = None
    expires_at: Optional[datetime] = None


class AnnouncementAuthorInfo(BaseModel):
    full_name: str

    model_config = {"from_attributes": True}


class AnnouncementResponse(BaseModel):
    id: uuid.UUID
    title: str
    content: str
    target_type: AnnouncementTarget
    department_id: Optional[uuid.UUID]
    semester_id: Optional[uuid.UUID]
    section: Optional[str]
    target_role: Optional[str]
    is_pinned: bool
    is_active: bool
    priority: AnnouncementPriority
    file_url: Optional[str]
    file_name: Optional[str]
    send_email: bool
    created_by_id: Optional[uuid.UUID]
    published_at: datetime
    expires_at: Optional[datetime]
    created_at: datetime
    is_read: Optional[bool] = False
    author: Optional[AnnouncementAuthorInfo] = None

    model_config = {"from_attributes": True}

    @model_validator(mode="before")
    @classmethod
    def inject_author(cls, data: Any) -> Any:
        if hasattr(data, "created_by") and data.created_by is not None:
            object.__setattr__(data, "_author_injected", True)
            # We can't mutate the ORM object — return a dict instead
            d = {c.key: getattr(data, c.key) for c in data.__table__.columns}
            d["author"] = {"full_name": data.created_by.full_name}
            d["is_read"] = getattr(data, "is_read", False)
            return d
        return data


class AnnouncementFeedItem(BaseModel):
    """Lightweight card for the announcement feed."""
    id: uuid.UUID
    title: str
    content: str               # first 200 chars shown in feed
    priority: AnnouncementPriority
    is_pinned: bool
    file_url: Optional[str]
    published_at: datetime
    expires_at: Optional[datetime]
    is_read: bool

    model_config = {"from_attributes": True}


# ── Notification schemas ───────────────────────────────────────────────────────

class NotificationResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    title: str
    message: str
    notification_type: NotificationType
    reference_id: Optional[str]
    reference_type: Optional[str]
    is_read: bool
    read_at: Optional[datetime]
    created_at: datetime

    model_config = {"from_attributes": True}


class UnreadCount(BaseModel):
    unread_notifications: int
    unread_announcements: int
    total: int
