import asyncio
import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.api.realtime import broadcast_event_sync

def test_broadcast():
    print("Testing WebSocket broadcast...")
    event = {
        "type": "event",
        "event_type": "WORKFLOW_NODE_ENTER",
        "user_id": "test-user-id",
        "user_email": "test@example.com",
        "workflow_id": "test-workflow-id",
        "node_id": "test-node-id",
        "timestamp": "2024-01-01T00:00:00Z"
    }
    broadcast_event_sync(event)
    print("Broadcast sent. Check your browser/WorkflowBuilder.")

if __name__ == "__main__":
    test_broadcast()
