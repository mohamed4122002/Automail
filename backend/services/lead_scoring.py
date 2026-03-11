"""
LeadScoringService — Phase 1 Foundation
Automatically calculates and updates a lead's score based on CRM activity events.

Score points per event type:
- email_sent       : +2
- email_opened     : +5
- link_clicked     : +10
- email_replied    : +20
- call             : +15
- meeting          : +40
- proposal         : +30
- note             : +3
- form             : +25
"""
from datetime import datetime
from uuid import UUID
from typing import Optional

from ..models import Lead, LeadScoreLog, CRMActivity, ActivityType

# Scoring weights per activity type
SCORE_WEIGHTS: dict[str, int] = {
    "email_sent":    2,
    "email_opened":  5,
    "link_clicked":  10,
    "email_replied": 20,
    "reply":         20,
    "call":          15,
    "meeting":       40,
    "proposal":      30,
    "note":          3,
    "form":          25,
    "system":        0,   # System events don't add points
}

# Hard cap for a lead score
MAX_SCORE = 100


class LeadScoringService:

    @staticmethod
    async def score_event(
        lead_id: UUID,
        event_type: str,
        note: Optional[str] = None
    ) -> int:
        """
        Award points for a single event, persist a log entry,
        recalculate the total score from all logs, and save it on the Lead.
        Returns the new total score.
        """
        raw_type = str(event_type).lower()
        # Strip enum prefix (e.g. "ActivityType.MEETING" → "meeting")
        if "." in raw_type:
            raw_type = raw_type.split(".")[-1]

        points = SCORE_WEIGHTS.get(raw_type, 0)
        if points == 0:
            return await LeadScoringService._get_current_score(lead_id)

        # Persist log
        log_entry = LeadScoreLog(
            lead_id=lead_id,
            event_type=raw_type,
            points=points,
            note=note,
        )
        await log_entry.insert()

        # Recalculate total from all logs
        return await LeadScoringService._recalculate_and_save(lead_id)

    @staticmethod
    async def _recalculate_and_save(lead_id: UUID) -> int:
        """Sum all LeadScoreLog entries and persist to Lead.lead_score."""
        logs = await LeadScoreLog.find(LeadScoreLog.lead_id == lead_id).to_list()
        total = min(sum(log.points for log in logs), MAX_SCORE)

        lead = await Lead.find_one(Lead.id == lead_id)
        if lead:
            lead.lead_score = total
            lead.updated_at = datetime.utcnow()
            await lead.save()

        return total

    @staticmethod
    async def _get_current_score(lead_id: UUID) -> int:
        lead = await Lead.find_one(Lead.id == lead_id)
        return lead.lead_score if lead else 0

    @staticmethod
    async def recalculate_all_for_lead(lead_id: UUID) -> int:
        """Full recalculation from scratch (useful for backfill)."""
        return await LeadScoringService._recalculate_and_save(lead_id)
