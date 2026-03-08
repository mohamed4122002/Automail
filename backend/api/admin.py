from fastapi import APIRouter, Depends, HTTPException
from uuid import UUID
from typing import List
from ..models import User, UserRole
from ..auth import get_current_admin
from ..schemas.users import UserProfile, UserRoleUpdate
from ..schemas.utils import orm_list_to_pydantic, orm_to_pydantic

router = APIRouter(prefix="/admin", tags=["admin"])

@router.get("/users", response_model=List[UserProfile])
async def list_all_users(admin: User = Depends(get_current_admin)):
    """Admin-only: List all users in the system."""
    users = await User.find_all().to_list()
    return orm_list_to_pydantic(users, UserProfile)

@router.patch("/users/{user_id}/role", response_model=UserProfile)
async def update_user_role(
    user_id: UUID, 
    update: UserRoleUpdate, 
    admin: User = Depends(get_current_admin)
):
    """Admin-only: Update a user's role."""
    user = await User.find_one(User.id == user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    try:
        # Validate the role against our enum
        new_role = UserRole(update.role)
        user.role = new_role
        
        # Also update the roles list for backward compatibility
        if update.roles is not None:
            user.roles = update.roles
        else:
            # Sync roles list if not provided
            if update.role not in user.roles:
                user.roles.append(update.role)
                
        await user.save()
        return orm_to_pydantic(user, UserProfile)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid role: {update.role}")

@router.get("/stats")
async def get_system_stats(admin: User = Depends(get_current_admin)):
    """Admin-only: Get high-level system statistics."""
    from ..models import Lead, Campaign, EmailSend
    
    user_count = await User.count()
    lead_count = await Lead.count()
    campaign_count = await Campaign.count()
    email_count = await EmailSend.count()
    
    return {
        "users": user_count,
        "leads": lead_count,
        "campaigns": campaign_count,
        "emails_sent": email_count,
    }
