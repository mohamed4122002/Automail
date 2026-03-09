import asyncio
import sys
import os
from uuid import uuid4
from unittest.mock import MagicMock, AsyncMock, patch

# Ensure backend matches the path structure
sys.path.append(os.getcwd())

from backend.conditions import evaluate_condition, ConditionResult

async def test_condition_robustness():
    print("\n=== Testing Condition Logic Robustness (Beanie Signature) ===")
    
    user_id = str(uuid4())
    ctx = {}
    cond = {"type": "event_check", "event": "opened", "within_hours": 24}
    
    # Since evaluate_condition now uses Event.find(...), we need to patch it
    with patch("backend.conditions.Event.find") as mock_find:
        mock_query = AsyncMock()
        mock_query.count.return_value = 1
        mock_find.return_value = mock_query
        
        result = await evaluate_condition(user_id, cond, ctx)
        print(f"Result for 'opened': {result}")
        assert result.passed == True
    
    # Test invalid type
    cond_invalid = {"type": "non_existent_type"}
    result_invalid = await evaluate_condition(user_id, cond_invalid, ctx)
    print(f"Result for invalid type: {result_invalid}")
    assert result_invalid.passed == False
    assert result_invalid.details["reason"] == "unknown_condition_type"

if __name__ == "__main__":
    try:
        asyncio.run(test_condition_robustness())
        print("✅ Condition Logic Tests Passed")
    except Exception as e:
        print(f"❌ Tests Failed: {e}")
        import traceback
        traceback.print_exc()
