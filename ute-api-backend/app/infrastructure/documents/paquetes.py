"""Construcción del ZIP del paquete de archivo (C08, DP-14).

Escribe el ZIP en un archivo temporal leyendo cada documento privado por su clave (nunca por un nombre
del cliente), verificando su tamaño y su SHA-256 contra lo registrado y fallando completo si falta o no
coincide alguno: no se entregan paquetes incompletos ni archivos de error dentro del ZIP.
"""
from __future__ import annotations

import hashlib
import os
import tempfile
import time
import zipfile
from pathlib import Path

from app.application.errors import ApplicationError
from app.infrastructure.storage.base import AlmacenamientoNoDisponible, ArchivoNoEncontrado
from app.infrastructure.storage.registro import get_storage

_BLOQUE = 64 * 1024
_ANTIGUEDAD_TEMPORALES = 3600


def _directorio() -> Path:
    ruta = Path(tempfile.gettempdir()) / "paquetes-dual"
    ruta.mkdir(parents=True, exist_ok=True)
    return ruta


def limpiar_temporales(antiguedad_segundos: int = _ANTIGUEDAD_TEMPORALES) -> int:
    """Elimina paquetes temporales que quedaron de descargas interrumpidas."""
    limite = time.time() - antiguedad_segundos
    eliminados = 0
    for ruta in _directorio().glob("*.zip"):
        try:
            if ruta.stat().st_mtime < limite:
                ruta.unlink()
                eliminados += 1
        except OSError:
            continue
    return eliminados


def nuevo_temporal() -> Path:
    limpiar_temporales()
    descriptor, nombre = tempfile.mkstemp(suffix=".zip", dir=_directorio())
    os.close(descriptor)
    return Path(nombre)


def construir_zip(entradas: list[dict], manifiesto: bytes, resumen_csv: bytes, destino: Path) -> dict:
    """Escribe `manifiesto.json`, `resumen.csv` y los documentos; devuelve archivos, bytes y tamaño.

    Cada entrada: {"ruta", "clave", "sha256", "tamano", "etiqueta"}. Falla con 409 si falta un
    documento o su contenido no coincide con el hash registrado.
    """
    rutas = [e["ruta"] for e in entradas]
    if len(set(rutas)) != len(rutas):
        raise ApplicationError(status_code=500, detail="Nombres duplicados en el paquete")
    total = 0
    with zipfile.ZipFile(destino, "w", zipfile.ZIP_DEFLATED) as paquete:
        paquete.writestr("manifiesto.json", manifiesto)
        paquete.writestr("resumen.csv", resumen_csv)
        for entrada in entradas:
            try:
                contenido = get_storage().leer("documentos", entrada["clave"])
            except ArchivoNoEncontrado as exc:
                raise ApplicationError(status_code=409, detail=_falta(entrada)) from exc
            except AlmacenamientoNoDisponible as exc:
                raise ApplicationError(
                    status_code=503,
                    detail="El almacenamiento de archivos no está disponible; el paquete no se generó.") from exc
            if hashlib.sha256(contenido).hexdigest() != entrada["sha256"] or len(contenido) != entrada["tamano"]:
                raise ApplicationError(
                    status_code=409,
                    detail=f"El documento {entrada['etiqueta']} no coincide con su hash registrado; "
                           "el paquete no se generó.")
            with paquete.open(entrada["ruta"], "w", force_zip64=True) as destino_zip:
                for inicio in range(0, len(contenido), _BLOQUE):
                    destino_zip.write(contenido[inicio:inicio + _BLOQUE])
            total += len(contenido)
    return {"archivos": len(entradas), "bytes": total, "tamano_zip": destino.stat().st_size}


def _falta(entrada: dict) -> str:
    return (f"Falta el documento {entrada['etiqueta']} en el almacenamiento; el paquete no se generó "
            "para no entregar un archivo incompleto.")
