import asyncio
import random
import uuid
from datetime import datetime, timedelta
import sqlalchemy as sa
from .auth import get_password_hash
from .db import AsyncSessionLocal
from .models import (
    Campaign,
    EmailTemplate,
    Event,
    LeadScore,
    Pipeline,
    PipelineItem,
    Role,
    User,
    UserRole,
    Workflow,
    WorkflowNode,
    WorkflowEdge,
    ContactList,
    Contact,
    LeadStatusEnum,
)
from .logging_config import get_logger

logger = get_logger(__name__)

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
  <style>
    {{% raw %}}
    @media only screen and (max-width: 600px) {{
      .container {{ width: 100% !important; padding: 10px !important; }}
      .header {{ font-size: 24px !important; }}
      .content {{ font-size: 16px !important; }}
      .button {{ width: 100% !important; padding: 15px 0 !important; }}
    }}
    {{% endraw %}}
  </style>
</head>
<body style="margin: 0; padding: 0; background-color: #0f172a; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; color: #f8fafc;">
  <table border="0" cellpadding="0" cellspacing="0" width="100%" style="background-color: #0f172a;">
    <tr>
      <td align="center" style="padding: 40px 0;">
        <table class="container" border="0" cellpadding="0" cellspacing="0" width="600" style="background-color: #1e293b; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);">
          <tr>
            <td class="header" style="padding: 40px 40px 20px 40px; font-size: 28px; font-weight: bold; color: #ffffff; text-align: left;">
              {title}
            </td>
          </tr>
          <tr>
            <td class="content" style="padding: 0 40px 30px 40px; font-size: 18px; line-height: 1.6; color: #cbd5e1;">
              {content}
            </td>
          </tr>
          <tr>
            <td style="padding: 0 40px 40px 40px;">
              <a href="{cta_link}" class="button" style="display: inline-block; padding: 12px 24px; background-color: #6366f1; color: #ffffff; text-decoration: none; font-weight: 600; border-radius: 8px; text-align: center;">
                {cta_text}
              </a>
            </td>
          </tr>
          <tr>
            <td style="padding: 20px 40px; background-color: #0f172a; font-size: 12px; color: #64748b; text-align: center;">
              &copy; 2026 Antigravity Platforms. All rights reserved.<br>
              You're receiving this because you're a valued contact.
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>
"""

async def seed_real_data():
    try:
        logger.info("Starting real data seeding...")
        async with AsyncSessionLocal() as db:
            # 1. Clean up existing data (optional but recommended for a clean "real" start)
            # await db.execute(sa.text("TRUNCATE TABLE events, workflow_instances, contacts, campaigns RESTART IDENTITY CASCADE"))
            
            # 2. Roles
            logger.info("Seeding Roles...")
            existing_roles = await db.execute(sa.select(Role))
            roles_dict = {r.name: r for r in existing_roles.scalars().all()}
            for rname in ["admin", "marketing", "sales", "viewer"]:
                if rname not in roles_dict:
                    new_role = Role(name=rname)
                    db.add(new_role)
                    roles_dict[rname] = new_role
            await db.flush()

            # 2.5. Default Settings
            logger.info("Seeding Default Settings...")
            from .models import Setting
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
                },
                {
                    "key": "workflow_preferences",
                    "value": {"max_parallel_workflows": 5, "default_delay_seconds": 3600},
                    "category": "workflow",
                    "description": "Workflow execution preferences"
                }
            ]
            for s_data in default_settings:
                res = await db.execute(sa.select(Setting).where(Setting.key == s_data["key"]))
                if not res.scalar_one_or_none():
                    s = Setting(
                        key=s_data["key"],
                        value=s_data["value"],
                        category=s_data["category"],
                        description=s_data["description"]
                    )
                    db.add(s)
            await db.flush()

            # 3. Users (Team Members)
            logger.info("Seeding Team Members...")
            team_members = [
                ("admin@antigravity.ai", "Admin", "User", "admin"),
                ("sarah.mkt@antigravity.ai", "Sarah", "Market", "marketing"),
                ("david.sales@antigravity.ai", "David", "Sales", "sales"),
            ]
            user_entities = {}
            for email, fname, lname, rname in team_members:
                user = await db.execute(sa.select(User).where(User.email == email))
                u = user.scalar_one_or_none()
                if not u:
                    u = User(
                        email=email,
                        hashed_password=get_password_hash("password123"),
                        first_name=fname,
                        last_name=lname,
                        is_active=True
                    )
                    db.add(u)
                    await db.flush()
                    db.add(UserRole(user_id=u.id, role_id=roles_dict[rname].id))
                user_entities[rname] = u
            
            # 4. Email Templates
            logger.info("Seeding Email Templates...")
            templates_data = [
                {
                    "name": "saas_intro",
                    "subject": "Stop wasting time on manual outreach",
                    "title": "Welcome to Antigravity",
                    "content": "Hi {{ first_name | default: 'there' }},\n\nScaling your team's outreach is hard. We've built tools to make it feel like you have 10 extra people. Want to see how?",
                    "cta_text": "View Dashboard"
                },
                {
                    "name": "webinar_invite",
                    "subject": "Invitation: Scaling in 2026",
                    "title": "Exclusive Webinar",
                    "content": "We're hosting a small group session on how to leverage AI orchestration for B2B sales. Spots are limited.",
                    "cta_text": "Register Now"
                },
                {
                    "name": "discount_offer",
                    "subject": "Small gift from the team",
                    "title": "Exclusive Offer",
                    "content": "Since you've been following our journey, we want to offer you 20% off our Premium plan for the first year.",
                    "cta_text": "Claim Now"
                }
            ]
            templates_dict = {}
            for t_data in templates_data:
                res = await db.execute(sa.select(EmailTemplate).where(EmailTemplate.name == t_data["name"]))
                t = res.scalar_one_or_none()
                if not t:
                    t = EmailTemplate(
                        name=t_data["name"],
                        subject=t_data["subject"],
                        html_body=get_html_body(t_data["title"], t_data["content"], t_data["cta_text"])
                    )
                    db.add(t)
                else:
                    # Update existing template
                    t.subject = t_data["subject"]
                    t.html_body = get_html_body(t_data["title"], t_data["content"], t_data["cta_text"])
                templates_dict[t_data["name"]] = t
            await db.flush()

            # 5. Campaigns
            logger.info("Seeding Campaigns...")
            campaigns_dict = {}
            campaign_names = ["SaaS Outreach 2026", "Webinar Lifecycle"]
            for cname in campaign_names:
                res = await db.execute(sa.select(Campaign).where(Campaign.name == cname))
                c = res.scalar_one_or_none()
                if not c:
                    c = Campaign(
                        name=cname,
                        description=f"Realistic marketing flow for {cname}",
                        owner_id=user_entities["marketing"].id,
                        is_active=True
                    )
                    db.add(c)
                campaigns_dict[cname] = c
            await db.flush()

            # 6. Workflows
            logger.info("Seeding Workflows...")
            # SaaS Outreach Workflow
            wf_res = await db.execute(sa.select(Workflow).where(Workflow.name == "SaaS Outreach Sequence"))
            saas_wf = wf_res.scalar_one_or_none()
            if not saas_wf:
                saas_wf = Workflow(name="SaaS Outreach Sequence", campaign_id=campaigns_dict["SaaS Outreach 2026"].id)
                db.add(saas_wf)
                await db.flush()
                # Nodes
                start = WorkflowNode(workflow_id=saas_wf.id, type="start", config={})
                email1 = WorkflowNode(workflow_id=saas_wf.id, type="email", config={"template_id": str(templates_dict["saas_intro"].id)})
                delay = WorkflowNode(workflow_id=saas_wf.id, type="delay", config={"seconds": 172800}) # 2 days
                cond = WorkflowNode(workflow_id=saas_wf.id, type="condition", config={"type": "event_check", "event": "opened", "within_hours": 48})
                action = WorkflowNode(workflow_id=saas_wf.id, type="action", config={"action": "update_lead_status", "status": "hot"})
                end = WorkflowNode(workflow_id=saas_wf.id, type="end", config={})
                db.add_all([start, email1, delay, cond, action, end])
                await db.flush()
                # Edges
                db.add(WorkflowEdge(workflow_id=saas_wf.id, from_node_id=start.id, to_node_id=email1.id))
                db.add(WorkflowEdge(workflow_id=saas_wf.id, from_node_id=email1.id, to_node_id=delay.id))
                db.add(WorkflowEdge(workflow_id=saas_wf.id, from_node_id=delay.id, to_node_id=cond.id))
                db.add(WorkflowEdge(workflow_id=saas_wf.id, from_node_id=cond.id, to_node_id=action.id, condition={"branch": "true"}))
                db.add(WorkflowEdge(workflow_id=saas_wf.id, from_node_id=cond.id, to_node_id=end.id, condition={"branch": "false"}))
                db.add(WorkflowEdge(workflow_id=saas_wf.id, from_node_id=action.id, to_node_id=end.id))

            # Webinar Lifecycle Workflow
            wf_res2 = await db.execute(sa.select(Workflow).where(Workflow.name == "Webinar Nurture Flow"))
            webinar_wf = wf_res2.scalar_one_or_none()
            if not webinar_wf:
                webinar_wf = Workflow(name="Webinar Nurture Flow", campaign_id=campaigns_dict["Webinar Lifecycle"].id)
                db.add(webinar_wf)
                await db.flush()
                # Nodes
                start = WorkflowNode(workflow_id=webinar_wf.id, type="start", config={})
                delay = WorkflowNode(workflow_id=webinar_wf.id, type="delay", config={"seconds": 86400}) # 1 day
                email = WorkflowNode(workflow_id=webinar_wf.id, type="email", config={"template_id": str(templates_dict["webinar_invite"].id)})
                cond = WorkflowNode(workflow_id=webinar_wf.id, type="condition", config={"type": "event_check", "event": "clicked", "within_hours": 24})
                offer = WorkflowNode(workflow_id=webinar_wf.id, type="email", config={"template_id": str(templates_dict["discount_offer"].id)})
                end = WorkflowNode(workflow_id=webinar_wf.id, type="end", config={})
                db.add_all([start, delay, email, cond, offer, end])
                await db.flush()
                # Edges
                db.add(WorkflowEdge(workflow_id=webinar_wf.id, from_node_id=start.id, to_node_id=delay.id))
                db.add(WorkflowEdge(workflow_id=webinar_wf.id, from_node_id=delay.id, to_node_id=email.id))
                db.add(WorkflowEdge(workflow_id=webinar_wf.id, from_node_id=email.id, to_node_id=cond.id))
                db.add(WorkflowEdge(workflow_id=webinar_wf.id, from_node_id=cond.id, to_node_id=offer.id, condition={"branch": "true"}))
                db.add(WorkflowEdge(workflow_id=webinar_wf.id, from_node_id=cond.id, to_node_id=end.id, condition={"branch": "false"}))
                db.add(WorkflowEdge(workflow_id=webinar_wf.id, from_node_id=offer.id, to_node_id=end.id))

            # 7. Contacts (50 Leads)
            logger.info("Seeding 50 Realistic Contacts...")
            contact_list_res = await db.execute(sa.select(ContactList).where(ContactList.name == "Sales Qualified Leads"))
            contact_list = contact_list_res.scalar_one_or_none()
            if not contact_list:
                contact_list = ContactList(name="Sales Qualified Leads", owner_id=user_entities["marketing"].id)
                db.add(contact_list)
                await db.flush()

            contacts = []
            for i in range(50):
                fname = random.choice(FIRST_NAMES)
                lname = random.choice(LAST_NAMES)
                domain = random.choice(DOMAINS)
                email = f"{fname.lower()}.{lname.lower()}{i}@{domain}"
                
                # Check if exists
                res = await db.execute(sa.select(Contact).where(Contact.email == email))
                if not res.scalar_one_or_none():
                    c = Contact(
                        contact_list_id=contact_list.id,
                        email=email,
                        first_name=fname,
                        last_name=lname,
                        attributes={
                            "company": domain.split(".")[0].capitalize(),
                            "industry": random.choice(INDUSTRIES),
                            "title": random.choice(["VP of Ops", "CEO", "Marketing Director", "Product Lead"])
                        }
                    )
                    db.add(c)
                    contacts.append(c)
            await db.flush()

            # 8. Historical Events (Analytics Data)
            logger.info("Simulating historical events for analytics...")
            # We also need these contacts as "Users" if they are active leads in the system tracking
            # In this model, events link to user_id.
            for c in contacts:
                # Check if shadow user already exists
                shadow_user_res = await db.execute(sa.select(User).where(User.email == c.email))
                u = shadow_user_res.scalar_one_or_none()
                
                if not u:
                    u = User(
                        email=c.email,
                        hashed_password="N/A",
                        first_name=c.first_name,
                        last_name=c.last_name,
                        is_active=False # Not a system user
                    )
                    db.add(u)
                    await db.flush()
                
                # Create the Lead object for this contact
                from .models import Lead
                # Check if lead already exists
                lead_res = await db.execute(sa.select(Lead).where(Lead.contact_id == c.id))
                lead = lead_res.scalar_one_or_none()
                
                if not lead:
                    lead_status_val = random.choice([LeadStatusEnum.new, LeadStatusEnum.warm, LeadStatusEnum.hot]).value
                    lead = Lead(
                        contact_id=c.id,
                        lead_status=lead_status_val,
                        lead_score=random.randint(0, 100),
                        assigned_to_id=user_entities["marketing"].id if lead_status_val in ["hot", "warm"] else None
                    )
                    db.add(lead)
                    await db.flush()
                
                # Check if lead score already exists
                score_res = await db.execute(sa.select(LeadScore).where(LeadScore.user_id == u.id))
                if not score_res.scalar_one_or_none():
                    db.add(LeadScore(user_id=u.id, score=random.randint(0, 100)))

                # Events over the last 30 days
                events_check = await db.execute(sa.select(sa.func.count(Event.id)).where(Event.user_id == u.id))
                if events_check.scalar_one() == 0:
                    num_events = random.randint(1, 5)
                    for _ in range(num_events):
                        days_ago = random.randint(0, 30)
                        etype = random.choice(["sent", "opened", "clicked", "bounced"])
                        event = Event(
                            type=etype,
                            user_id=u.id,
                            campaign_id=campaigns_dict["SaaS Outreach 2026"].id,
                            created_at=datetime.utcnow() - timedelta(days=days_ago)
                        )
                        db.add(event)
            
            await db.commit()
            logger.info("Successfully seeded real data pack.")

    except Exception as e:
        import traceback
        logger.error(f"Real data seeding failed: {e}")
        logger.error(traceback.format_exc())
        raise

if __name__ == "__main__":
    asyncio.run(seed_real_data())
