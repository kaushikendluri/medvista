"""AI worker process entrypoint: python -m app.worker

Polls the Redis analysis queue and processes jobs one at a time. Runs as
its own container (see docker-compose.yml's ai-worker service) sharing
the same codebase and database as the API, deliberately kept separate
from the request/response path so analysis never blocks an HTTP request.
"""
import logging
import uuid

from app.core.logging import logger
from app.db.session import SessionLocal
from app.services.ai_service import process_analysis_job
from app.services.queue import dequeue_analysis_job

logging.getLogger().setLevel(logging.INFO)


def run() -> None:
    logger.info('"ai-worker started, polling the analysis queue"')
    while True:
        job = dequeue_analysis_job(timeout_seconds=5)
        if job is None:
            continue
        try:
            analysis_id = uuid.UUID(job)
        except ValueError:
            logger.info('"ai-worker discarded malformed job payload"')
            continue

        db = SessionLocal()
        try:
            logger.info('"ai-worker processing analysis %s"' % analysis_id)
            process_analysis_job(db, analysis_id)
            logger.info('"ai-worker finished analysis %s"' % analysis_id)
        finally:
            db.close()


if __name__ == "__main__":
    run()
