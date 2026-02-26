import asyncio
import sys
import os
from uuid import uuid4
from unittest.mock import MagicMock, AsyncMock

# Ensure backend matches the path structure
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from backend.core.async_runner import run_async
from backend.services.campaign_manager import CampaignManagerService
from backend.conditions import evaluate_condition, ConditionResult

async def test_campaign_activation_optimization():
    print("\n=== Testing Campaign Activation Optimization ===")
    
    # Mock DB Session
    mock_db = AsyncMock()
    service = CampaignManagerService(mock_db)
    
    # Mock DB executions to simulate scenario
    # We need to mock the sequence of queries in activate_campaign
    pass

async def test_condition_robustness():
    print("\n=== Testing Condition Logic Robustness ===")
    
    # FAIL FIX: Ensure execute returns a MagicMock (synchronous), not an AsyncMock
    mock_result = MagicMock()
    mock_result.scalar_one.return_value = 1
    
    mock_db = AsyncMock()
    mock_db.execute.return_value = mock_result
    
    user_id = str(uuid4())
    
    # Test Case 1: Case-insensitive string match (conceptually, though logic is in tasks.py, 
    # evaluate_condition just returns data. The robust handler was added to tasks.py earlier.
    # But we added robust handlers in backend/conditions.py too? 
    # Wait, I added logging to backend/conditions.py, but the logic fix was in tasks.py!
    # Ah, I should verify backend/conditions.py handlers are good.
    
    # Test valid event check
    ctx = {}
    cond = {"type": "event_check", "event": "opened", "within_hours": 24}
    
    # Mock _event_check handler result
    # calling evaluate_condition will call _event_check
    # We need to mock the DB response to _event_check query
    
    mock_db.execute.return_value.scalar_one.return_value = 1 # count > 0
    
    result = await evaluate_condition(mock_db, user_id, cond, ctx)
    print(f"Result for 'opened': {result}")
    assert result.passed == True
    
    # Test invalid type
    cond_invalid = {"type": "non_existent_type"}
    result_invalid = await evaluate_condition(mock_db, user_id, cond_invalid, ctx)
    print(f"Result for invalid type: {result_invalid}")
    assert result_invalid.passed == False
    assert result_invalid.details["reason"] == "unknown_condition_type"

if __name__ == "__main__":
    try:
        run_async(test_condition_robustness())
        print("✅ Condition Logic Tests Passed")
    except Exception as e:
        print(f"❌ Tests Failed: {e}")
        import traceback
        traceback.print_exc()
