from redis import Redis
from rq import Queue
from app.config import settings
import logging

logger = logging.getLogger("truvia.queue")

# Initialize Redis connection synchronously for RQ
redis_conn = Redis.from_url(settings.REDIS_URL)

# Define task queue
task_queue = Queue("truvia-tasks", connection=redis_conn)

def enqueue_job(func, *args, **kwargs):
    """
    Enqueue a background job with RQ.
    """
    try:
        job = task_queue.enqueue(func, *args, **kwargs)
        logger.info(f"Enqueued job {job.id} for function {func.__name__}")
        return job.id
    except Exception as e:
        logger.error(f"Failed to enqueue job: {str(e)}")
        # In case Redis is down, we can run synchronous fallback depending on configuration
        raise
