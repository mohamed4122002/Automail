import asyncio
import os
import sys
from datetime import datetime, timezone, timedelta

# Add parent directory to path to import backend modules
sys.path.append(os.path.abspath(os.path.join(os.getcwd(), ".")))

from backend.db import init_db
from backend.models import User, Lead, Campaign, Event, UserRole

async def diagnostic():
    await init_db()
    print("DB Initialized")
    
    # Check users
    users = await User.find_all().to_list()
    print(f"Total users: {len(users)}")
    for u in users:
        print(f" - {u.email}: {u.role} (roles: {u.roles})")
    
    # Lead Funnel
    total_leads = await Lead.count()
    hot_leads = await Lead.find(Lead.lead_status == "hot").count()
    warm_leads = await Lead.find(Lead.lead_status == "warm").count()
    opps = await Lead.find({"lead_status": {"$in": ["hot", "warm"]}}).count()
    
    print(f"\nLead Funnel:")
    print(f" - Total: {total_leads}")
    print(f" - Hot: {hot_leads}")
    print(f" - Warm: {warm_leads}")
    print(f" - Conversion Opps: {opps}")
    
    # Engagement
    total_sent = await Event.find(Event.type == "sent").count()
    total_opened = await Event.find(Event.type == "opened").count()
    total_clicked = await Event.find(Event.type == "clicked").count()
    
    open_rate = (total_opened / total_sent * 100) if total_sent > 0 else 0
    click_rate = (total_clicked / total_sent * 100) if total_sent > 0 else 0
    
    print(f"\nEngagement Pulse:")
    print(f" - Sent: {total_sent}")
    print(f" - Open Rate: {open_rate:.2f}%")
    print(f" - Click Rate: {click_rate:.2f}%")
    
    # Team Productivity
    thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
    print(f"\nProductivity since: {thirty_days_ago}")
    
    user_activity = []
    for u in users:
        activity_count = await Event.find(
            Event.user_id == u.id,
            Event.created_at >= thirty_days_ago
        ).count()
        user_activity.append({
            "email": u.email,
            "activity": activity_count
        })
    
    user_activity.sort(key=lambda x: x["activity"], reverse=True)
    print("\nTeam Leaderboard:")
    for i, active in enumerate(user_activity[:5]):
        print(f" {i+1}. {active['email']}: {active['activity']} activities")

if __name__ == "__main__":
    asyncio.run(diagnostic())
