"""Redis-backed job queue for asynchronous AI analysis jobs.

A plain list used as a queue (RPUSH/BLPOP) is deliberately simple —
this project doesn't need Celery/RQ's scheduling or retry machinery yet,
just a real durable handoff between the API process and the worker
process. Job payload is just the analysis ID; the worker re-reads
everything else from the database.
"""
import redis

from app.core.config import get_settings

settings = get_settings()

ANALYSIS_QUEUE_KEY = "medvista:ai_analysis_queue"

_redis_client: redis.Redis | None = None


def get_redis_client() -> redis.Redis:
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)
    return _redis_client


def enqueue_analysis_job(analysis_id: str) -> None:
    get_redis_client().rpush(ANALYSIS_QUEUE_KEY, analysis_id)


def dequeue_analysis_job(timeout_seconds: int = 5) -> str | None:
    result = get_redis_client().blpop([ANALYSIS_QUEUE_KEY], timeout=timeout_seconds)
    if result is None:
        return None
    _, analysis_id = result
    return analysis_id


def queue_length() -> int:
    return get_redis_client().llen(ANALYSIS_QUEUE_KEY)
