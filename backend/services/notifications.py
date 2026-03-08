from typing import List, Optional
from uuid import UUID
from datetime import datetime
from ..models import CRMNotification

class NotificationService:
    @staticmethod
    async def create_notification(
        user_id: UUID,
        title: str,
        message: str,
        type: str = "info",
        link: Optional[str] = None
    ) -> CRMNotification:
        notification = CRMNotification(
            user_id=user_id,
            title=title,
            message=message,
            type=type,
            link=link
        )
        await notification.insert()
        return notification

    @staticmethod
    async def get_user_notifications(user_id: UUID, limit: int = 20) -> List[CRMNotification]:
        return await CRMNotification.find(
            CRMNotification.user_id == user_id
        ).sort(-CRMNotification.created_at).limit(limit).to_list()

    @staticmethod
    async def mark_as_read(notification_id: UUID):
        notification = await CRMNotification.get(notification_id)
        if notification:
            notification.is_read = True
            await notification.save()

    @staticmethod
    async def mark_all_as_read(user_id: UUID):
        await CRMNotification.find(
            CRMNotification.user_id == user_id,
            CRMNotification.is_read == False
        ).update({"$set": {"is_read": True}})
