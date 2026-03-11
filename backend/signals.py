"""
CRM Signal Utility for real-time WebSocket broadcasts.
"""
from typing import Any, Dict, Optional
from uuid import UUID
import logging
from .api.realtime import broadcast_event_sync

logger = logging.getLogger(__name__)

class CRMSignals:
    """Standardized signals for CRM events."""
    
    @staticmethod
    def broadcast_lead_update(lead_id: UUID, user_id: UUID, change_type: str, data: Optional[Dict[str, Any]] = None):
        """Broadcast lead-related changes (stage, status, assignment)."""
        event = {
            "type": "crm_event",
            "entity": "lead",
            "action": change_type,
            "entity_id": str(lead_id),
            "lead_id": str(lead_id),
            "user_id": str(user_id),
            "data": data or {},
            "timestamp": None # Will be set by receiver if needed
        }
        broadcast_event_sync(event)
        logger.info(f"Broadcasted lead signal: {change_type} for {lead_id}")

    @staticmethod
    def broadcast_task_update(lead_id: UUID, task_id: UUID, user_id: UUID, action: str):
        """Broadcast task-related changes (created, completed)."""
        event = {
            "type": "crm_event",
            "entity": "task",
            "action": action,
            "entity_id": str(task_id),
            "lead_id": str(lead_id),
            "user_id": str(user_id)
        }
        broadcast_event_sync(event)
        logger.info(f"Broadcasted task signal: {action} for {task_id}")

    @staticmethod
    def broadcast_activity_update(lead_id: UUID, user_id: UUID, activity_type: str):
        """Broadcast when a new activity (note, meeting, call) is logged."""
        event = {
            "type": "crm_event",
            "entity": "activity",
            "action": "created",
            "entity_id": str(lead_id),
            "lead_id": str(lead_id),
            "user_id": str(user_id),
            "activity_type": activity_type
        }
        broadcast_event_sync(event)
        logger.info(f"Broadcasted activity signal for lead {lead_id}")
