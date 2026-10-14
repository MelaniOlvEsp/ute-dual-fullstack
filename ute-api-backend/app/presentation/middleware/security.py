import time
from collections import defaultdict

from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from loguru import logger


# Inyecta cabeceras de seguridad en cada respuesta
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    # inject security headers into every response
    # Agrega las cabeceras de seguridad a la respuesta
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "0"
        response.headers["Strict-Transport-Security"] = (
            "max-age=63072000; includeSubDomains; preload"
        )
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = (
            "camera=(), microphone=(), geolocation=()"
        )
        response.headers["Cache-Control"] = "no-store, max-age=0"
        return response


# Limitador de tasa global por IP (ventana deslizante)
class RateLimitMiddleware(BaseHTTPMiddleware):
    # (ver app/core/utils/rate_limit.py)

    # Inicializa los parametros del limitador de tasa
    def __init__(self, app, max_requests: int = 120, window_sec: int = 60):
        super().__init__(app)
        self.max_requests = max_requests
        self.window_sec = window_sec
        self._buckets: dict[str, list[float]] = defaultdict(list)

    # Aplica el limite de tasa antes de continuar con la request
    async def dispatch(self, request: Request, call_next):
        ip = request.client.host if request.client else "unknown"
        now = time.monotonic()
        bucket = self._buckets[ip]
        bucket[:] = [t for t in bucket if now - t < self.window_sec]
        if len(bucket) >= self.max_requests:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many requests. Slow down.",
            )
        bucket.append(now)

        if len(self._buckets) > 1000:
            stale = [k for k, v in self._buckets.items()
                     if not [t for t in v if now - t < self.window_sec]]
            for k in stale:
                del self._buckets[k]

        return await call_next(request)


# Captura excepciones no manejadas y responde un mensaje seguro
async def generic_error_handler(
    request: Request, exc: Exception
) -> JSONResponse:
    logger.exception(
        f"Unhandled error on {request.method} {request.url.path}"
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error"},
    )


# Configura el formato y nivel de logging de loguru
def configure_logging(json_format: bool = False):
    logger.remove()
    if json_format:
        logger.add(
            lambda msg: print(msg, flush=True),
            format=(
                '{{"time":"{time:YYYY-MM-DDTHH:mm:ssZ}","level":"{level}",'
                '"name":"{name}","message":"{message}","extra":{extra}}}'
            ),
            level="INFO",
            serialize=False,
        )
    else:
        logger.add(
            lambda msg: print(msg, flush=True),
            format=(
                "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
                "<level>{level: <8}</level> | "
                "<cyan>{name}</cyan> | "
                "<level>{message}</level>"
            ),
            level="DEBUG",
            colorize=True,
        )
