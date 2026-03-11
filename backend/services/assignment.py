from uuid import UUID
from typing import Optional, List
from .leads import LeadService
from ..models import Lead, User, UserRole, CRMLeadStage
import logging

logger = logging.getLogger(__name__)

class LeadAssignmentService:
    @staticmethod
    async def get_least_loaded_member() -> Optional[User]:
        """
        Finds the Team Member with the fewest open leads.
        Open leads are those not in 'won' or 'lost' stages.
        """
        # 1. Get all potential assignees (Team Members)
        # In a real scenario, we might want to filter by active status or specific teams
        members = await User.find(User.role == UserRole.TEAM_MEMBER, User.is_active == True).to_list()
        
        if not members:
            logger.warning("No active Team Members found for lead assignment.")
            return None
            
        # 2. Count open leads for each member
        # Open stages = everything except won/lost
        open_stages = [s.value for s in CRMLeadStage if s.value not in ["won", "lost"]]
        
        member_loads = []
        for member in members:
            count = await Lead.find(
                Lead.assigned_to_id == member.id,
                Lead.stage != CRMLeadStage.WON,
                Lead.stage != CRMLeadStage.LOST
            ).count()
            member_loads.append((member, count))
            
        # 3. Sort by count and return the one with the minimum
        member_loads.sort(key=lambda x: x[1])
        
        selected_member = member_loads[0][0]
        logger.info(f"Selected least loaded member: {selected_member.email} with {member_loads[0][1]} open leads.")
        return selected_member

    @staticmethod
    async def auto_assign_lead(lead_id: UUID, assigned_by_id: Optional[UUID] = None) -> Optional[User]:
        """
        Automatically assigns a lead to the least loaded member.
        """
        member = await LeadAssignmentService.get_least_loaded_member()
        if member:
            await LeadService.assign_lead(
                lead_id=lead_id,
                assigned_to_id=member.id,
                assigned_by_id=assigned_by_id or member.id, # If no assigner, use self or system logic
                assignment_type="auto"
            )
            return member
        return None
