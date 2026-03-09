import asyncio
import random
import uuid
from datetime import datetime, timedelta, timezone
from .auth import get_password_hash
from .models import (
    Campaign, EmailTemplate, Event, LeadScore, Pipeline, PipelineItem,
    Role, User, UserRole, Workflow, WorkflowNode, WorkflowEdge,
    ContactList, Contact, LeadStatusEnum, Setting, Lead, EventTypeEnum
)
from .logging_config import get_logger

logger = get_logger(__name__)

def utcnow() -> datetime:
    return datetime.now(timezone.utc)

# --- Realistic Data Pools ---
DOMAINS = ["techcorp.io", "finanziasolutions.com", "healthplus.org", "retailgiant.net", "cloudnexus.co", "innovate.ai"]
INDUSTRIES = ["Technology", "Finance", "Healthcare", "E-commerce", "SaaS", "Manufacturing"]
FIRST_NAMES = ["James", "Mary", "Robert", "Patricia", "John", "Jennifer", "Michael", "Linda", "William", "Elizabeth", "David", "Barbara", "Richard", "Susan", "Joseph", "Jessica", "Thomas", "Sarah", "Charles", "Karen"]
LAST_NAMES = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis", "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson", "Thomas", "Taylor", "Moore", "Jackson", "Martin"]

# --- Helper functions ---
def get_html_body(title, content, cta_text, cta_link="#"):
    return f"""
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="margin: 0; padding: 0; background-color: #0f172a; font-family: sans-serif; color: #f8fafc;">
  <div style="padding: 40px; background-color: #1e293b; max-width: 600px; margin: 0 auto; border-radius: 12px;">
    <h1 style="color: #ffffff;">{title}</h1>
    <p style="color: #cbd5e1; font-size: 18px; line-height: 1.6;">{content}</p>
    <a href="{cta_link}" style="display: inline-block; padding: 12px 24px; background-color: #6366f1; color: #ffffff; text-decoration: none; border-radius: 8px;">{cta_text}</a>
  </div>
</body>
</html>
"""

async def seed_real_data():
    try:
        logger.info("Starting real data seeding (MongoDB/Beanie)...")
        
        # 1. Roles
        logger.info("Seeding Roles...")
        role_names = ["admin", "sales_lead", "team_member"]
        for rname in role_names:
            if not await Role.find_one(Role.name == rname):
                await Role(name=rname).insert()

        # 2. Default Settings
        logger.info("Seeding Default Settings...")
        default_settings = [
            {
                "key": "email_provider",
                "value": {"provider": "console"},
                "category": "email",
                "description": "Email provider configuration"
            },
            {
                "key": "system_preferences",
                "value": {"maintenance_mode": False, "allow_registration": True},
                "category": "system",
                "description": "System wide preferences"
            }
        ]
        for s_data in default_settings:
            if not await Setting.find_one(Setting.key == s_data["key"]):
                await Setting(**s_data).insert()

        # 3. Users
        logger.info("Seeding Users...")
        team_members = [
            ("admin@antigravity.ai", "Admin", "User", UserRole.ADMIN),
            ("sarah.mkt@antigravity.ai", "Sarah", "Market", UserRole.TEAM_MEMBER),
            ("david.sales@antigravity.ai", "David", "Sales", UserRole.SALES_LEAD),
        ]
        user_entities = {}
        for email, fname, lname, role in team_members:
            u = await User.find_one(User.email == email)
            if not u:
                u = User(
                    email=email,
                    hashed_password=get_password_hash("password123"),
                    first_name=fname,
                    last_name=lname,
                    is_active=True,
                    role=role,
                    roles=[role.value]
                )
                await u.insert()
            user_entities[role.value] = u

        # 4. Email Templates
        logger.info("Seeding Email Templates...")
        templates_data = [
            {
                "name": "saas_intro",
                "subject": "Stop wasting time on manual outreach",
                "title": "Welcome to Antigravity",
                "content": "Hi there, scaling outreach is hard. We make it easy.",
                "cta_text": "View Dashboard"
            },
            {
                "name": "webinar_invite",
                "subject": "Invitation: Scaling in 2026",
                "title": "Exclusive Webinar",
                "content": "Hosting a session on AI orchestration.",
                "cta_text": "Register Now"
            }
        ]
        templates_dict = {}
        for t_data in templates_data:
            t = await EmailTemplate.find_one(EmailTemplate.name == t_data["name"])
            if not t:
                t = EmailTemplate(
                    name=t_data["name"],
                    subject=t_data["subject"],
                    html_body=get_html_body(t_data["title"], t_data["content"], t_data["cta_text"])
                )
                await t.insert()
            templates_dict[t_data["name"]] = t

        # 5. Campaigns
        logger.info("Seeding Campaigns...")
        c_names = ["SaaS Outreach 2026", "Webinar Lifecycle"]
        campaigns_dict = {}
        admin_user = user_entities[UserRole.ADMIN.value]
        for cname in c_names:
            c = await Campaign.find_one(Campaign.name == cname)
            if not c:
                c = Campaign(
                    name=cname,
                    description=f"Marketing flow for {cname}",
                    owner_id=admin_user.id,
                    is_active=True
                )
                await c.insert()
            campaigns_dict[cname] = c

        # 6. Workflows
        logger.info("Seeding Workflows...")
        for cname, c in campaigns_dict.items():
            wf_name = f"{cname} Workflow"
            wf = await Workflow.find_one(Workflow.name == wf_name)
            if not wf:
                wf = Workflow(name=wf_name, campaign_id=c.id, is_active=True)
                await wf.insert()
                
                # Simple Start -> Email -> End
                start = WorkflowNode(workflow_id=wf.id, type="start", config={})
                await start.insert()
                
                email_node = WorkflowNode(
                    workflow_id=wf.id, 
                    type="email", 
                    config={"template_id": str(templates_dict["saas_intro"].id)}
                )
                await email_node.insert()
                
                end = WorkflowNode(workflow_id=wf.id, type="end", config={})
                await end.insert()
                
                await WorkflowEdge(workflow_id=wf.id, from_node_id=start.id, to_node_id=email_node.id).insert()
                await WorkflowEdge(workflow_id=wf.id, from_node_id=email_node.id, to_node_id=end.id).insert()

        # 7. Contacts
        logger.info("Seeding Contacts...")
        clist = await ContactList.find_one(ContactList.name == "Main Leads")
        if not clist:
            clist = ContactList(name="Main Leads", owner_id=admin_user.id)
            await clist.insert()
            
        for i in range(10):
            email = f"lead{i}@example.com"
            if not await Contact.find_one(Contact.email == email):
                contact = Contact(
                    contact_list_id=clist.id,
                    email=email,
                    first_name=random.choice(FIRST_NAMES),
                    last_name=random.choice(LAST_NAMES),
                    attributes={"industry": random.choice(INDUSTRIES)}
                )
                await contact.insert()
                
                # Create a lead for each contact
                await Lead(
                    contact_id=contact.id,
                    company_name=random.choice(DOMAINS).split('.')[0].capitalize(),
                    lead_status=LeadStatusEnum.new,
                    lead_score=random.randint(10, 90)
                ).insert()

        logger.info("Successfully seeded real data pack (MongoDB).")

    except Exception as e:
        logger.error(f"Real data seeding failed: {e}", exc_info=True)
        raise

if __name__ == "__main__":
    asyncio.run(seed_real_data())
