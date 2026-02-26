"""
Comprehensive verification script for campaign execution system.
Tests all components: database, Redis, Celery workers, and campaign activation.
"""
import asyncio
import sys
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db import AsyncSessionLocal
from backend.models import (
    Campaign, Workflow, WorkflowNode, WorkflowEdge, WorkflowInstance,
    Contact, ContactList, User, EmailTemplate, EmailSend
)
from backend.services.campaign_manager import CampaignManagerService
from backend.celery_app import celery_app
from backend.logging_config import get_logger

logger = get_logger(__name__)


async def check_database():
    """Verify database connectivity and schema."""
    logger.info("=" * 60)
    logger.info("1. CHECKING DATABASE")
    logger.info("=" * 60)
    
    try:
        async with AsyncSessionLocal() as db:
            # Test connection
            result = await db.execute(select(func.count(Campaign.id)))
            campaign_count = result.scalar_one()
            
            result = await db.execute(select(func.count(Workflow.id)))
            workflow_count = result.scalar_one()
            
            result = await db.execute(select(func.count(Contact.id)))
            contact_count = result.scalar_one()
            
            logger.info(f"✓ Database connected successfully")
            logger.info(f"  - Campaigns: {campaign_count}")
            logger.info(f"  - Workflows: {workflow_count}")
            logger.info(f"  - Contacts: {contact_count}")
            
            return True
    except Exception as e:
        logger.error(f"✗ Database check failed: {e}")
        return False


def check_redis():
    """Verify Redis connectivity."""
    logger.info("\n" + "=" * 60)
    logger.info("2. CHECKING REDIS")
    logger.info("=" * 60)
    
    try:
        from redis import Redis
        from backend.config import settings
        
        redis_client = Redis.from_url(settings.REDIS_URL)
        redis_client.ping()
        
        logger.info(f"✓ Redis connected successfully")
        logger.info(f"  - URL: {settings.REDIS_URL}")
        
        return True
    except Exception as e:
        logger.error(f"✗ Redis check failed: {e}")
        return False


def check_celery_workers():
    """Verify Celery workers are running."""
    logger.info("\n" + "=" * 60)
    logger.info("3. CHECKING CELERY WORKERS")
    logger.info("=" * 60)
    
    try:
        inspect = celery_app.control.inspect()
        stats = inspect.stats()
        active = inspect.active()
        
        if not stats:
            logger.error("✗ No Celery workers detected!")
            logger.error("  Please start workers with:")
            logger.error("    docker-compose up -d worker beat")
            logger.error("  OR manually:")
            logger.error("    celery -A backend.celery_app worker --loglevel=info --pool=solo")
            return False
        
        worker_count = len(stats.keys())
        logger.info(f"✓ {worker_count} Celery worker(s) running")
        
        for worker_name, worker_stats in stats.items():
            active_tasks = len(active.get(worker_name, [])) if active else 0
            logger.info(f"  - {worker_name}: {active_tasks} active tasks")
        
        return True
    except Exception as e:
        logger.error(f"✗ Celery check failed: {e}")
        return False


async def check_test_data():
    """Verify test data exists for campaign activation."""
    logger.info("\n" + "=" * 60)
    logger.info("4. CHECKING TEST DATA")
    logger.info("=" * 60)
    
    try:
        async with AsyncSessionLocal() as db:
            # Check for campaigns
            result = await db.execute(select(Campaign).limit(1))
            campaign = result.scalar_one_or_none()
            
            if not campaign:
                logger.warning("⚠ No campaigns found. Please create a campaign first.")
                return False
            
            logger.info(f"✓ Found campaign: {campaign.name}")
            
            # Check if campaign has contact list
            if not campaign.contact_list_id:
                logger.warning(f"⚠ Campaign '{campaign.name}' has no contact list assigned")
                return False
            
            # Check for contacts
            result = await db.execute(
                select(func.count(Contact.id)).where(Contact.contact_list_id == campaign.contact_list_id)
            )
            contact_count = result.scalar_one()
            
            if contact_count == 0:
                logger.warning(f"⚠ Contact list has no contacts")
                return False
            
            logger.info(f"✓ Contact list has {contact_count} contact(s)")
            
            # Check for workflow
            result = await db.execute(
                select(Workflow).where(Workflow.campaign_id == campaign.id)
            )
            workflow = result.scalar_one_or_none()
            
            if not workflow:
                logger.warning(f"⚠ Campaign '{campaign.name}' has no workflow")
                return False
            
            logger.info(f"✓ Found workflow: {workflow.name}")
            
            # Check workflow nodes
            result = await db.execute(
                select(func.count(WorkflowNode.id)).where(WorkflowNode.workflow_id == workflow.id)
            )
            node_count = result.scalar_one()
            
            logger.info(f"✓ Workflow has {node_count} node(s)")
            
            # Check for email template
            result = await db.execute(select(EmailTemplate).limit(1))
            template = result.scalar_one_or_none()
            
            if not template:
                logger.warning("⚠ No email templates found")
                return False
            
            logger.info(f"✓ Found email template: {template.name}")
            
            return True
            
    except Exception as e:
        logger.error(f"✗ Test data check failed: {e}")
        return False


async def test_campaign_activation():
    """Test campaign activation end-to-end."""
    logger.info("\n" + "=" * 60)
    logger.info("5. TESTING CAMPAIGN ACTIVATION")
    logger.info("=" * 60)
    
    try:
        async with AsyncSessionLocal() as db:
            # Get first campaign
            result = await db.execute(select(Campaign).limit(1))
            campaign = result.scalar_one_or_none()
            
            if not campaign:
                logger.error("✗ No campaign available for testing")
                return False
            
            logger.info(f"Testing activation of campaign: {campaign.name}")
            
            # Activate campaign
            manager = CampaignManagerService(db)
            result = await manager.activate_campaign(campaign.id, campaign.owner_id)
            
            logger.info(f"✓ Campaign activation result:")
            logger.info(f"  - Message: {result['message']}")
            logger.info(f"  - Contacts processed: {result['contacts_processed']}")
            logger.info(f"  - Instances started: {result['instances_started']}")
            logger.info(f"  - Tasks dispatched: {result['tasks_dispatched']}")
            
            # Verify workflow instances were created
            await db.commit()
            
            result_check = await db.execute(
                select(func.count(WorkflowInstance.id))
            )
            instance_count = result_check.scalar_one()
            
            logger.info(f"✓ Total workflow instances in database: {instance_count}")
            
            return True
            
    except Exception as e:
        logger.error(f"✗ Campaign activation test failed: {e}", exc_info=True)
        return False


async def main():
    """Run all verification checks."""
    logger.info("\n")
    logger.info("🚀 CAMPAIGN EXECUTION SYSTEM VERIFICATION")
    logger.info("=" * 60)
    
    results = {
        "Database": await check_database(),
        "Redis": check_redis(),
        "Celery Workers": check_celery_workers(),
        "Test Data": await check_test_data(),
    }
    
    # Only test activation if all prerequisites pass
    if all(results.values()):
        results["Campaign Activation"] = await test_campaign_activation()
    else:
        logger.warning("\n⚠ Skipping campaign activation test due to failed prerequisites")
    
    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("VERIFICATION SUMMARY")
    logger.info("=" * 60)
    
    for check, passed in results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        logger.info(f"{status}: {check}")
    
    all_passed = all(results.values())
    
    if all_passed:
        logger.info("\n🎉 ALL CHECKS PASSED! Campaign execution system is ready.")
        return 0
    else:
        logger.error("\n❌ SOME CHECKS FAILED. Please review the errors above.")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
