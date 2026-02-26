import time
import asyncio
import sys
import os

# Ensure backend matches the path structure
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from backend.core.async_runner import run_async
from backend.tasks import send_email_task

def trace_task():
    print("=== Task Execution Tracer ===")
    
    start_time = time.time()
    try:
        # Simulate a task call (this won't actually trigger Celery worker unless we use apply_async)
        # But here we want to test the async runner overhead if we could import the inner logic
        # Since logic is inside the task, we can't easily import it.
        # Instead, we will simulate a dummy async workload using run_async
        
        async def dummy_workload():
            await asyncio.sleep(0.05) # 50ms work
            return "done"
            
        print("Running dummy workload (50ms sleep)...")
        res = run_async(dummy_workload())
        print(f"Result: {res}")
        
    except Exception as e:
        print(f"❌ Trace failed: {e}")
    
    duration = (time.time() - start_time) * 1000
    print(f"Total Execution Time (including overhead): {duration:.2f}ms")
    
    if duration > 100:
        print("⚠️ Overhead is high (>100ms)")
    else:
        print("✅ Performance is acceptable (<100ms)")

if __name__ == "__main__":
    trace_task()
