"""
load_test_seeder.py
-------------------
Seeds 150 realistic lead records across all CRM pipeline stages for Phase 5
load testing and latency auditing.

Run inside the backend container:
  docker exec marketing-automation-backend-1 python -m backend.load_test_seeder
"""
import asyncio
import random
import uuid
from datetime import datetime, timedelta, timezone

from .db import init_db
from .models import Lead, User, CRMLeadStage, LeadStatusEnum

# ─── Realistic data pools ────────────────────────────────────────────────────

COMPANY_NAMES = [
    "TechNova Solutions", "FinEdge Capital", "MedCore Health", "RetailStream",
    "CloudNexus", "InnoVentures", "DataPulse Ltd", "GreenWave Energy",
    "UrbanLogistics", "PrimeSoftware", "BlueSky Analytics", "NexGen Robotics",
    "AlphaMedia Group", "SwiftCommerce", "BrightPath Consulting",
    "IronBridge Finance", "SolarGrid Co", "HarbourTech", "ZenithAI",
    "FrostPoint Retail", "Vanguard Systems", "EcoSense Ltd", "AgileMind",
    "Skyline Partners", "Pinnacle Ventures", "ClearScope Analytics",
    "VelocityWorks", "DeepRoot Labs", "LuminaTech", "StellarCRM",
]

SOURCES = [
    "LinkedIn", "Cold Email", "Referral", "Website Form",
    "Demo Request", "Conference", "Partner", "Organic Search",
]

def utcnow():
    return datetime.now(timezone.utc)

def rand_date(days_back: int = 180) -> datetime:
    return utcnow() - timedelta(days=random.randint(0, days_back))

# ─── Seeder ──────────────────────────────────────────────────────────────────

async def seed_load_test_data():
    await init_db()

    # ── Drop the bad non-sparse unique index on contact_id if it exists ──────
    # This index rejects multiple null contact_ids, which we intentionally allow.
    try:
        collection = Lead.get_motor_collection()
        index_info = await collection.index_information()
        if 'contact_id_1' in index_info:
            await collection.drop_index('contact_id_1')
            print("⚙️  Dropped legacy unique index 'contact_id_1' from leads collection")
    except Exception as e:
        print(f"⚠️  Could not drop contact_id index: {e}")

    # Fetch any existing admin user to use as assignee
    admin_user = await User.find_one()
    assignee_id = admin_user.id if admin_user else None

    stages = list(CRMLeadStage)
    statuses = list(LeadStatusEnum)

    leads_to_insert = []

    for i in range(150):
        company = random.choice(COMPANY_NAMES) + f" #{i+1}"
        stage = random.choice(stages)
        lead_score = random.randint(10, 100)

        lead = Lead(
            id=uuid.uuid4(),
            company_name=company,
            source=random.choice(SOURCES),
            stage=stage,
            assigned_to_id=assignee_id,
            assigned_by_id=assignee_id,
            lead_status=random.choice(statuses),
            lead_score=lead_score,
            deal_value=round(random.uniform(5_000, 250_000), 2),
            last_activity_at=rand_date(60),
            created_at=rand_date(180),
            updated_at=rand_date(10),
        )
        leads_to_insert.append(lead)

    # Insert in batches of 50
    batch_size = 50
    inserted = 0
    for start in range(0, len(leads_to_insert), batch_size):
        batch = leads_to_insert[start:start + batch_size]
        await Lead.insert_many(batch)
        inserted += len(batch)
        print(f"  Inserted {inserted}/{len(leads_to_insert)} leads...")

    print(f"\n✅ Done — seeded {inserted} load-test leads across {len(stages)} pipeline stages.")

    # Print stage distribution
    print("\n📊 Stage distribution:")
    for stage in stages:
        count = sum(1 for l in leads_to_insert if l.stage == stage)
        print(f"  {stage.value:15s} → {count} leads")


if __name__ == "__main__":
    asyncio.run(seed_load_test_data())
