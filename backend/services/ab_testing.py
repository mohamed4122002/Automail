import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from typing import Optional, Dict, Any, List
from datetime import datetime

from ..models import EmailVariant, EmailSend, Event, EventTypeEnum

class ABTestingService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_test(
        self,
        subject_a: str,
        subject_b: str,
        campaign_id: Optional[UUID] = None,
        workflow_step_id: Optional[UUID] = None,
        test_limit: int = 100,
        html_body: str = "<p>Default Body</p>" # Placeholder as body is required
    ) -> Dict[str, Any]:
        """Create a new A/B test (creates two variants)."""
        
        # Variant A
        variant_a = EmailVariant(
            campaign_id=campaign_id,
            workflow_step_id=workflow_step_id,
            subject=subject_a,
            html_body=html_body,
            weight=0.5
        )
        self.db.add(variant_a)
        
        # Variant B
        variant_b = EmailVariant(
            campaign_id=campaign_id,
            workflow_step_id=workflow_step_id,
            subject=subject_b,
            html_body=html_body,
            weight=0.5
        )
        self.db.add(variant_b)
        
        await self.db.commit()
        
        # Return a synthetic test object
        return {
            "id": variant_a.id, # Use one ID as the reference
            "campaign_id": campaign_id,
            "status": "active",
            "variants": [variant_a, variant_b]
        }

    async def get_active_test(
        self,
        campaign_id: Optional[UUID] = None,
        workflow_step_id: Optional[UUID] = None
    ) -> Optional[EmailVariant]:
        """
        Find if an A/B test is active.
        Returns the first variant if multiple exist (implying a test).
        """
        query = sa.select(EmailVariant).where(
            (EmailVariant.campaign_id == campaign_id) if campaign_id else (EmailVariant.workflow_step_id == workflow_step_id)
        )
        result = await self.db.execute(query)
        variants = result.scalars().all()
        
        if len(variants) >= 2:
            return variants[0] # Return first variant as a handle
            
        return None

    async def get_stats(self, variant_id_handle: UUID) -> Dict[str, Any]:
        """Calculate stats for an A/B test (all variants in the group)."""
        
        # Get the reference variant to find the group
        ref_query = sa.select(EmailVariant).where(EmailVariant.id == variant_id_handle)
        ref_result = await self.db.execute(ref_query)
        ref_variant = ref_result.scalar_one_or_none()
        
        if not ref_variant:
            return {}
            
        # Find all variants in this group
        group_query = sa.select(EmailVariant).where(
            (EmailVariant.campaign_id == ref_variant.campaign_id) if ref_variant.campaign_id else 
            (EmailVariant.workflow_step_id == ref_variant.workflow_step_id)
        )
        group_result = await self.db.execute(group_query)
        variants = group_result.scalars().all()
        
        stats = {}
        total_sent = 0
        
        labels = ["a", "b"]
        labeled_stats = {}
        subjects = {}
        
        for i, variant in enumerate(variants):
            label = labels[i] if i < len(labels) else f"var_{i}"
            
            # Sent count (from EmailSend)
            sent_query = sa.select(sa.func.count(EmailSend.id)).where(
                EmailSend.variant_id == variant.id
            )
            sent_res = await self.db.execute(sent_query)
            sent_count = sent_res.scalar_one() or 0
            total_sent += sent_count

            # Opened count
            opened_query = sa.select(sa.func.count(Event.id)).join(EmailSend).where(
                sa.and_(
                    EmailSend.variant_id == variant.id,
                    Event.type == EventTypeEnum.OPENED
                )
            )
            opened_res = await self.db.execute(opened_query)
            opened_count = opened_res.scalar_one() or 0
            
            rate = round((opened_count / sent_count) * 100, 2) if sent_count > 0 else 0
            
            labeled_stats[label] = {
                "id": str(variant.id),
                "subject": variant.subject,
                "sent": sent_count,
                "opened": opened_count,
                "rate": rate,
                "weight": variant.weight
            }
            subjects[label] = variant.subject

        # Determine status
        # If any variant has weight 1.0, it's completed (winner selected)
        status = "active"
        winner = None
        for label, data in labeled_stats.items():
            if data["weight"] >= 0.99:
                status = "completed"
                winner = label
        
        return {
            "id": str(ref_variant.id),
            "status": status,
            "winner": winner,
            "total_sent": total_sent,
            "stats": labeled_stats,
            "subjects": subjects
        }

    async def select_winner(self, variant_id_handle: UUID) -> Optional[str]:
        """Determine winner based on stats and set weights."""
        stats_data = await self.get_stats(variant_id_handle)
        stats = stats_data.get("stats", {})
        
        if "a" not in stats or "b" not in stats:
            return None
            
        rate_a = stats["a"]["rate"]
        rate_b = stats["b"]["rate"]
        
        winner_label = "a" if rate_a >= rate_b else "b"
        winner_id = UUID(stats[winner_label]["id"])
        
        # Get reference
        ref_result = await self.db.execute(sa.select(EmailVariant).where(EmailVariant.id == variant_id_handle))
        ref_variant = ref_result.scalar_one()
        
        # Update all in group
        group_query = sa.select(EmailVariant).where(
            (EmailVariant.campaign_id == ref_variant.campaign_id) if ref_variant.campaign_id else 
            (EmailVariant.workflow_step_id == ref_variant.workflow_step_id)
        )
        group_res = await self.db.execute(group_query)
        variants = group_res.scalars().all()
        
        for v in variants:
            if v.id == winner_id:
                v.weight = 1.0
            else:
                v.weight = 0.0
            self.db.add(v)
            
        await self.db.commit()
        
        return winner_label
