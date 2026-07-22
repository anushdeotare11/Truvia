import logging

logger = logging.getLogger("truvia.queue")

# Lazy Redis connection — only connect when actually needed.
# If Redis is unavailable (e.g. Railway free tier without Redis add-on),
# fall back to running the task synchronously in-process.

_redis_conn = None
_task_queue = None
_redis_available = None  # None = not yet checked


def _ensure_redis():
    """Try to connect to Redis once. Cache the result."""
    global _redis_conn, _task_queue, _redis_available
    if _redis_available is not None:
        return _redis_available
    try:
        from redis import Redis
        from rq import Queue
        from app.config import settings

        conn = Redis.from_url(settings.REDIS_URL)
        conn.ping()  # Verify connectivity
        _redis_conn = conn
        _task_queue = Queue("truvia-tasks", connection=conn)
        _redis_available = True
        logger.info("Redis connection established for task queue")
    except Exception as e:
        _redis_available = False
        logger.warning(f"Redis unavailable — tasks will run inline (sync): {e}")
    return _redis_available


def enqueue_job(func, *args, **kwargs):
    """
    Enqueue a background job with RQ.
    Falls back to synchronous in-process execution when Redis is unavailable.
    """
    if _ensure_redis() and _task_queue is not None:
        try:
            job = _task_queue.enqueue(func, *args, **kwargs)
            logger.info(f"Enqueued job {job.id} for function {func.__name__}")
            return job.id
        except Exception as e:
            logger.error(f"Failed to enqueue job, running inline: {str(e)}")

    # Synchronous fallback — run the function directly in-process
    import asyncio

    if asyncio.iscoroutinefunction(func):
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.ensure_future(func(*args, **kwargs))
        else:
            asyncio.run(func(*args, **kwargs))
    else:
        func(*args, **kwargs)
    return "inline"
