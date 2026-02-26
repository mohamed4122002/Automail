import asyncio
import pytest
import sys
import os

# Ensure backend matches the path structure
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from backend.core.async_runner import run_async

def test_run_async_execution():
    async def sample_coro():
        await asyncio.sleep(0.01)
        return "success"
    
    result = run_async(sample_coro())
    assert result == "success"

def test_run_async_isolation():
    """Ensure loops are unique per call."""
    
    async def get_loop_id():
        return id(asyncio.get_running_loop())
    
    loop1_id = run_async(get_loop_id())
    loop2_id = run_async(get_loop_id())
    
    assert loop1_id != loop2_id
    print(f"Loop 1: {loop1_id}, Loop 2: {loop2_id} (Validated Unique)")

if __name__ == "__main__":
    # Manually run if executed as script
    try:
        test_run_async_execution()
        test_run_async_isolation()
        print("✅ AsyncRunner Unit Tests Passed")
    except AssertionError as e:
        print(f"❌ Test Failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ unexpected error: {e}")
        sys.exit(1)
