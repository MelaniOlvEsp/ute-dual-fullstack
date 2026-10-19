import ipaddress
import time
from collections import defaultdict, deque

from fastapi import Request, status
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


# Limitador de solicitudes (C14, D1): por usuario con un límite generoso y por IP solo para lo que no trae una sesión
# válida, más un tope alto por IP como respaldo. Al pasar el límite responde un 429 real con `Retry-After` (antes lanzaba
# una excepción dentro del middleware, que el cliente veía como 500). Va dentro de CORS y de las cabeceras de seguridad.
class RateLimitMiddleware(BaseHTTPMiddleware):
    EXENTAS = {"/health"}

    def __init__(self, app, limite_usuario: int | None = None, limite_ip_anonima: int | None = None,
                 limite_ip_total: int | None = None, proxies: str | None = None, ventana_seg: int = 60, reloj=time.monotonic):
        super().__init__(app)
        from app.infrastructure.config.settings import settings
        self.limite_usuario = settings.rate_limit_usuario if limite_usuario is None else limite_usuario
        self.limite_ip_anonima = settings.rate_limit_ip_anonima if limite_ip_anonima is None else limite_ip_anonima
        self.limite_ip_total = settings.rate_limit_ip_total if limite_ip_total is None else limite_ip_total
        self.redes = redes_de_confianza(settings.rate_limit_proxies if proxies is None else proxies)
        self.ventana = ventana_seg
        self.reloj = reloj
        self._cubos: dict[str, deque[float]] = defaultdict(deque)
        self._avisos: dict[str, float] = {}
        self._contador = 0

    def _consumir(self, clave: str, limite: int, ahora: float) -> int | None:
        """Cuenta una solicitud en la clave; devuelve los segundos de espera si se pasó el límite, o None."""
        cubo = self._cubos[clave]
        while cubo and ahora - cubo[0] >= self.ventana:
            cubo.popleft()
        if len(cubo) >= limite:
            return max(1, int(self.ventana - (ahora - cubo[0])) + 1)
        cubo.append(ahora)
        return None

    def _limpiar(self, ahora: float) -> None:
        self._contador += 1
        if self._contador % 500:
            return
        for clave in [k for k, v in self._cubos.items() if not v or ahora - v[-1] >= self.ventana]:
            del self._cubos[clave]
        for clave in [k for k, t in self._avisos.items() if ahora - t >= self.ventana]:
            del self._avisos[clave]

    async def dispatch(self, request: Request, call_next):
        if request.method == "OPTIONS" or request.url.path in self.EXENTAS:
            return await call_next(request)
        ahora = self.reloj()
        ip = ip_del_cliente(request, self.redes)
        usuario = usuario_del_token(request.headers.get("authorization", ""))
        clave = f"ip-total:{ip}"
        espera = self._consumir(clave, self.limite_ip_total, ahora)
        if espera is None:
            if usuario:
                clave = f"usuario:{usuario}"
                espera = self._consumir(clave, self.limite_usuario, ahora)
            else:
                clave = f"ip:{ip}"
                espera = self._consumir(clave, self.limite_ip_anonima, ahora)
        self._limpiar(ahora)
        if espera is None:
            return await call_next(request)
        if clave not in self._avisos:       # un aviso por clave y ventana, sin traza
            self._avisos[clave] = ahora
            logger.warning("Límite de solicitudes superado ({}).", clave.split(":", 1)[0])
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={"detail": "Demasiadas solicitudes. Intenta de nuevo en unos segundos."},
            headers={"Retry-After": str(espera)},
        )


def redes_de_confianza(texto: str):
    redes = []
    for parte in (texto or "").split(","):
        parte = parte.strip()
        if parte:
            redes.append(ipaddress.ip_network(parte, strict=False))
    return redes


# IP del cliente: la del socket, salvo que venga de un proxy configurado como de confianza; entonces se toma la dirección
# más a la derecha de `X-Forwarded-For` que no sea de un proxy de confianza (las anteriores las puede escribir cualquiera).
def ip_del_cliente(request: Request, redes) -> str:
    ip = request.client.host if request.client else "desconocida"
    if not redes or ip == "desconocida":
        return ip

    def confiable(valor: str) -> bool:
        try:
            return any(ipaddress.ip_address(valor) in red for red in redes)
        except ValueError:
            return False

    if not confiable(ip):
        return ip
    reenviadas = [p.strip() for p in request.headers.get("x-forwarded-for", "").split(",") if p.strip()]
    for candidata in reversed(reenviadas):
        if not confiable(candidata):
            return candidata
    return ip


# Identificador del usuario del token (solo si es válido y no ha expirado); None si no hay sesión válida.
def usuario_del_token(cabecera: str) -> str | None:
    if not cabecera.lower().startswith("bearer "):
        return None
    try:
        from app.infrastructure.security.jwt_passwords import verificar_token
        datos = verificar_token(cabecera[7:].strip())
    except ValueError:
        return None
    return str(datos.get("id") or datos.get("sub") or "") or None


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
