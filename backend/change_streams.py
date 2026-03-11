"""
change_streams.py — MongoDB Change Stream listener for real-time fallback sync.

When the API layer emits a CRMSignal, the frontend receives a WebSocket push.
However, if a change reaches the database without going through the API
(e.g. admin CLI, data migration, Celery worker) the Change Stream catches it
and triggers the same WebSocket broadcast.

This listener runs as a background asyncio task started in `lifespan`.
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)

# Watched collections and the corresponding WebSocket entity name
WATCHED = {
    "leads": "lead",
    "crmtasks": "task",      # beanie collection names are lowercase
    "crmactivities": "activity",
}

# Operations we care about
WATCHED_OPS = {"insert", "update", "replace", "delete"}

_task: Optional[asyncio.Task] = None  # holds our running background task


async def _watch_collection(db, collection_name: str, entity: str) -> None:
    """Open a change stream on *collection_name* and broadcast updates."""
    # Import here to avoid circular imports at module load
    from .api.realtime import broadcast_event_sync

    pipeline = [{"$match": {"operationType": {"$in": list(WATCHED_OPS)}}}]

    logger.info("Change stream started → collection=%s", collection_name)

    while True:  # restart on transient errors
        try:
            collection = db[collection_name]
            async with collection.watch(pipeline, max_await_time_ms=1000) as stream:
                async for change in stream:
                    op = change.get("operationType", "unknown")
                    doc_key = change.get("documentKey", {})
                    full_doc = change.get("fullDocument") or {}
                    doc_id = str(doc_key.get("_id", ""))

                    event = {
                        "type": "change_stream",
                        "entity": entity,
                        "action": op,
                        "entity_id": doc_id,
                        "lead_id": str(full_doc.get("lead_id", doc_id)),
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    }

                    broadcast_event_sync(event)
                    logger.debug("ChangeStream → %s.%s entity_id=%s", entity, op, doc_id)

        except asyncio.CancelledError:
            logger.info("Change stream cancelled for %s", collection_name)
            return
        except Exception as exc:
            err_msg = str(exc)
            # If the error is specifically about replica sets, log it and back off longer
            if "replica set" in err_msg.lower() or "40573" in err_msg:
                logger.warning(
                    "MongoDB Change Streams requires a replica set. To fix, start mongo with --replSet. collection=%s",
                    collection_name
                )
                await asyncio.sleep(60)  # Wait longer if it's a structural config issue
            else:
                logger.warning(
                    "Change stream error on %s: %s — reconnecting in 5 s",
                    collection_name, exc
                )
                await asyncio.sleep(5)  # back-off before reconnecting


async def start_change_streams(db) -> None:
    """
    Launch one watcher task per collection.
    Call this from the FastAPI lifespan AFTER init_db().
    """
    global _task

    tasks = [
        asyncio.create_task(
            _watch_collection(db, col, entity),
            name=f"change_stream_{col}",
        )
        for col, entity in WATCHED.items()
    ]
    # Bundle them so callers can cancel all at once
    _task = asyncio.gather(*tasks, return_exceptions=True)
    logger.info("MongoDB Change Streams started for: %s", list(WATCHED.keys()))


async def stop_change_streams() -> None:
    """Cancel the watcher tasks gracefully on shutdown."""
    global _task
    if _task:
        _task.cancel()
        try:
            await _task
        except (asyncio.CancelledError, Exception):
            pass
        _task = None
        logger.info("MongoDB Change Streams stopped.")
