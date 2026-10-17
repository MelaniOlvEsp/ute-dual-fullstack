"""Selección del adaptador de almacenamiento según la configuración (C10A)."""
from __future__ import annotations

import threading
import time
from contextlib import contextmanager
from pathlib import Path

from app.infrastructure.config.settings import settings
from app.infrastructure.storage.base import Almacenamiento

_actual: Almacenamiento | None = None
_estado: tuple[float, dict] | None = None
_cerrojo = threading.Lock()
TTL_ESTADO = 60.0


def _construir() -> Almacenamiento:
    tipo = settings.almacenamiento.strip().lower()
    if tipo == "drive":
        from app.infrastructure.storage import credenciales
        from app.infrastructure.storage.drive import DriveAlmacenamiento
        return DriveAlmacenamiento(credenciales.fabrica_servicio, credenciales.carpeta_raiz_id())
    if tipo == "local":  # solo desarrollo y regresión; el piloto no guarda archivos de forma local
        from app.infrastructure.storage.local import LocalAlmacenamiento
        return LocalAlmacenamiento(Path(settings.dual_upload_dir))
    if tipo == "memoria":
        from app.infrastructure.storage.memoria import MemoriaAlmacenamiento
        return MemoriaAlmacenamiento()
    raise RuntimeError("ALMACENAMIENTO debe ser drive, local o memoria")


def get_storage() -> Almacenamiento:
    global _actual
    with _cerrojo:
        if _actual is None:
            _actual = _construir()
        return _actual


def set_storage(adaptador: Almacenamiento | None) -> None:
    global _actual, _estado
    with _cerrojo:
        _actual, _estado = adaptador, None


@contextmanager
def usar(adaptador: Almacenamiento):
    """Sustituye el adaptador durante una prueba y lo restablece al salir."""
    global _actual, _estado
    anterior, estado = _actual, _estado
    set_storage(adaptador)
    try:
        yield adaptador
    finally:
        with _cerrojo:
            _actual, _estado = anterior, estado


def estado_cacheado() -> dict:
    """Estado del almacenamiento para `/health`, consultado como máximo una vez por minuto."""
    global _estado
    ahora = time.monotonic()
    if _estado and ahora - _estado[0] < TTL_ESTADO:
        return _estado[1]
    try:
        resultado = get_storage().estado()
    except Exception:
        resultado = {"tipo": settings.almacenamiento, "estado": "no_disponible"}
    _estado = (ahora, resultado)
    return resultado