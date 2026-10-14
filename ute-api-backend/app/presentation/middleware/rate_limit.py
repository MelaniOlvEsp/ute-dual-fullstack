# app/core/utils/rate_limit.py
import time
from collections import defaultdict

from fastapi import HTTPException, Request, status

_intentos: dict[str, list[float]] = defaultdict(list)


# Limita la cantidad de intentos de una acción por IP en un periodo de tiempo.
def limitar_intentos(
    clave_prefijo: str, max_intentos: int, ventana_segundos: int
):
    async def dependencia(request: Request):
        ip = request.client.host if request.client else "desconocida"
        clave = f"{clave_prefijo}:{ip}"
        ahora = time.monotonic()

        intentos = _intentos[clave]
        intentos[:] = [t for t in intentos if ahora - t < ventana_segundos]

        if len(intentos) >= max_intentos:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=(
                    "Demasiados intentos. Intenta de nuevo en unos minutos."
                ),
            )

        intentos.append(ahora)

    return dependencia
