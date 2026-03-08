from beanie.operators import In
from uuid import UUID
from typing import Optional, Dict, Any, List
from datetime import datetime

from ..models import EmailVariant, EmailSend, Event, EventTypeEnum

class ABTestingService:
    def __init__(self):
        pass

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
        await variant_a.insert()
        
        # Variant B
        variant_b = EmailVariant(
            campaign_id=campaign_id,
            workflow_step_id=workflow_step_id,
            subject=subject_b,
            html_body=html_body,
            weight=0.5
        )
        await variant_b.insert()
        
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
        filters = []
        if campaign_id:
            filters.append(EmailVariant.campaign_id == campaign_id)
        if workflow_step_id:
            filters.append(EmailVariant.workflow_step_id == workflow_step_id)
            
        variants = await EmailVariant.find(*filters).to_list()
        
        if len(variants) >= 2:
            return variants[0] # Return first variant as a handle
            
        return None

    async def get_stats(self, variant_id_handle: UUID) -> Dict[str, Any]:
        """Calculate stats for an A/B test (all variants in the group)."""
        
        # Get the reference variant to find the group
        ref_variant = await EmailVariant.find_one(EmailVariant.id == variant_id_handle)
        
        if not ref_variant:
            return {}
            
        # Find all variants in this group
        filters = []
        if ref_variant.campaign_id:
            filters.append(EmailVariant.campaign_id == ref_variant.campaign_id)
        if ref_variant.workflow_step_id:
            filters.append(EmailVariant.workflow_step_id == ref_variant.workflow_step_id)
            
        variants = await EmailVariant.find(*filters).to_list()
        
        stats = {}
        total_sent = 0
        
        labels = ["a", "b"]
        labeled_stats = {}
        subjects = {}
        
        for i, variant in enumerate(variants):
            label = labels[i] if i < len(labels) else f"var_{i}"
            
            # Sent count (from EmailSend)
            sent_count = await EmailSend.find(EmailSend.variant_id == variant.id).count()
            total_sent += sent_count

            # Opened count
            sends = await EmailSend.find(EmailSend.variant_id == variant.id).to_list()
            send_ids = [s.id for s in sends]
            
            opened_count = 0
            if send_ids:
                opened_count = await Event.find(
                    In(Event.email_send_id, send_ids),
                    Event.type == EventTypeEnum.OPENED
                ).count()
            
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
        ref_variant = await EmailVariant.find_one(EmailVariant.id == variant_id_handle)
        
        # Update all in group
        filters = []
        if ref_variant.campaign_id:
            filters.append(EmailVariant.campaign_id == ref_variant.campaign_id)
        if ref_variant.workflow_step_id:
            filters.append(EmailVariant.workflow_step_id == ref_variant.workflow_step_id)
            
        variants = await EmailVariant.find(*filters).to_list()
        
        for v in variants:
            if v.id == winner_id:
                v.weight = 1.0
            else:
                v.weight = 0.0
            await v.save()
            
        return winner_label
