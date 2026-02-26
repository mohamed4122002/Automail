import argparse
import asyncio
import sys
import subprocess
from pathlib import Path
from .logging_config import setup_logging, get_logger

# Initialize logging
setup_logging()

logger = get_logger(__name__)

async def init_db_cmd():
    logger.info("🔧 Running database migrations (Alembic)...")
    try:
        # Run alembic upgrade head
        result = subprocess.run(["alembic", "upgrade", "head"], capture_output=True, text=True)
        if result.returncode != 0:
            logger.error(f"Migration failed: {result.stderr}")
            raise Exception("Alembic migration failed")
        logger.info("✅ Database migrations applied.")
    except Exception as e:
        logger.error(f"Error running migrations: {e}")
        raise

async def seed_base_cmd():
    logger.info("🌱 Seeding base data...")
    from .seed import seed
    await seed()
    logger.info("✅ Base data seeded.")

async def seed_production_templates_cmd():
    logger.info("📦 Seeding all production workflow templates...")
    from .seed_email_templates import seed_templates
    from .seed_path1_workflow import seed_cold_outreach_workflow
    from .seed_path2_workflow import seed_path2_workflow
    from .seed_path3_workflow import seed_path3_workflow
    from .seed_default_email_provider import seed_default_email_provider
    
    await seed_default_email_provider()
    await seed_templates()
    await seed_cold_outreach_workflow()
    await seed_path2_workflow()
    await seed_path3_workflow()
    logger.info("✅ All production templates seeded successfully")

async def main():
    parser = argparse.ArgumentParser(description="Marketing Automation CLI")
    parser.add_argument("command", choices=["init-all", "migrate", "seed", "health-check"], help="Command to run")
    
    args = parser.parse_args()

    if args.command == "init-all":
        logger.info("🚀 Starting full system initialization...")
        await init_db_cmd()
        await seed_base_cmd()
        await seed_production_templates_cmd()
        logger.info("✅ System fully initialized.")
    elif args.command == "migrate":
        await init_db_cmd()
    elif args.command == "seed":
        await seed_base_cmd()
        await seed_production_templates_cmd()
    elif args.command == "health-check":
        from .scripts.check_health import main as health_main
        await health_main()
    else:
        parser.print_help()

if __name__ == "__main__":
    asyncio.run(main())
