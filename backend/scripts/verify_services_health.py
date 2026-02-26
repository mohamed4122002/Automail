import importlib
import sys
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def verify_modules():
    modules_to_verify = [
        "backend.services.workflow_engine",
        "backend.services.users",
        "backend.services.settings",
        "backend.services.email_rate_limit",
        "backend.services.contacts",
        "backend.services.campaign_analytics",
        "backend.services.ab_testing",
        "backend.services.analytics",
        "backend.services.campaigns",
        "backend.services.spam_shield",
        "backend.services.reputation",
        "backend.services.campaign_manager",
        "backend.tasks",
        "backend.tasks_lead_status"
    ]
    
    success_count = 0
    failed_modules = []

    print("-" * 50)
    print("Verifying Backend Modules Systematization")
    print("-" * 50)

    for module_name in modules_to_verify:
        try:
            importlib.import_module(module_name)
            print(f"OK: {module_name}")
            success_count += 1
        except Exception as e:
            print(f"FAILED: {module_name}")
            print(f"Error: {e}")
            failed_modules.append((module_name, str(e)))

    print("-" * 50)
    print(f"Verification Summary: {success_count}/{len(modules_to_verify)} modules passed.")
    
    if failed_modules:
        print("\nFailed Modules Details:")
        for mod, err in failed_modules:
            print(f"- {mod}: {err}")
        return False
    
    return True

if __name__ == "__main__":
    if verify_modules():
        sys.exit(0)
    else:
        sys.exit(1)
