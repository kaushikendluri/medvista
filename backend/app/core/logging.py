import logging
import sys
import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

logger = logging.getLogger("medvista")
logger.setLevel(logging.INFO)
_handler = logging.StreamHandler(sys.stdout)
_handler.setFormatter(
    logging.Formatter('{"time":"%(asctime)s","level":"%(levelname)s","message":%(message)s}')
)
if not logger.handlers:
    logger.addHandler(_handler)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Structured request logging. Never logs request/response bodies, which
    may contain patient information."""

    async def dispatch(self, request: Request, call_next):
        request_id = str(uuid.uuid4())
        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = round((time.perf_counter() - start) * 1000, 2)
        logger.info(
            '{"request_id":"%s","method":"%s","path":"%s","status":%d,"duration_ms":%s}'
            % (request_id, request.method, request.url.path, response.status_code, duration_ms)
        )
        response.headers["X-Request-ID"] = request_id
        return response
