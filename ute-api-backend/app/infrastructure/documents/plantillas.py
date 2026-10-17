"""Archivos de la plantilla común del reporte (C09, RN-26): pareja Word (.docx) + PDF.

Almacenamiento privado fuera de la raíz pública, con claves generadas por el servidor (nunca el nombre del
cliente) y validación real del contenido: el PDF con el mismo inspector de C05 y el DOCX como contenedor
ZIP (OOXML) con límites contra bombas de descompresión, sin macros ni rutas peligrosas.
"""
from __future__ import annotations

import asyncio
import hashlib
import io
import os
import re
import uuid
import zipfile
from pathlib import Path

from loguru import logger

from app.application.errors import ApplicationError
from app.infrastructure.config.settings import settings
from app.infrastructure.documents.dual_reports import inspeccionar_pdf

MAX_PLANTILLA_BYTES = 10 * 1024 * 1024
MAX_DOCX_ENTRADAS = 500
MAX_DOCX_DESCOMPRIMIDO = 100 * 1024 * 1024
MAX_DOCX_RAZON = 200  # relación descomprimido/comprimido por entrada
TIPO_DOCX_PRINCIPAL = "application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"
EXTENSIONES = ("docx", "pdf")
_CLAVE = re.compile(r"^[0-9a-f]{32}\.(docx|pdf)$")
_BLOQUE = 64 * 1024


def _raiz() -> Path:
    return Path(settings.dual_upload_dir) / "plantillas"


def ruta_plantilla(clave: str) -> Path:
    # Solo claves con el formato generado por el servidor: evita cualquier recorrido de rutas.
    if not _CLAVE.fullmatch(clave or ""):
        raise ApplicationError(status_code=404, detail="Plantilla no disponible")
    return _raiz() / clave[:2] / clave


async def leer_limitado(archivo, extension: str) -> bytes:
    """Lee la carga en bloques y corta al superar el límite; la extensión del cliente solo se contrasta."""
    if not (archivo.filename or "").lower().endswith("." + extension):
        raise ApplicationError(status_code=422, detail=f"Se esperaba un archivo .{extension}.")
    partes, total = [], 0
    while True:
        bloque = await archivo.read(_BLOQUE)
        if not bloque:
            break
        total += len(bloque)
        if total > MAX_PLANTILLA_BYTES:
            raise ApplicationError(status_code=413, detail=f"El archivo .{extension} excede el límite de 10 MB.")
        partes.append(bloque)
    return b"".join(partes)


def inspeccionar_docx(contenido: bytes) -> None:
    """Comprueba que sea un DOCX real (ZIP OOXML) sin macros ni entradas peligrosas."""
    if not contenido:
        raise ApplicationError(status_code=422, detail="El archivo Word está vacío.")
    if not contenido.startswith(b"PK\x03\x04"):
        raise ApplicationError(status_code=422, detail="El archivo no es un documento de Word (.docx) válido.")
    try:
        paquete = zipfile.ZipFile(io.BytesIO(contenido))
    except zipfile.BadZipFile as exc:
        raise ApplicationError(status_code=422, detail="El archivo Word está dañado.") from exc
    with paquete:
        entradas = paquete.infolist()
        if len(entradas) > MAX_DOCX_ENTRADAS:
            raise ApplicationError(status_code=422, detail="El archivo Word tiene demasiadas partes.")
        descomprimido = 0
        for entrada in entradas:
            nombre = entrada.filename
            if nombre.startswith("/") or "\\" in nombre or ".." in nombre.split("/"):
                raise ApplicationError(status_code=422, detail="El archivo Word contiene rutas no permitidas.")
            descomprimido += entrada.file_size
            if entrada.compress_size and entrada.file_size / entrada.compress_size > MAX_DOCX_RAZON:
                raise ApplicationError(status_code=422, detail="El archivo Word excede la compresión permitida.")
        if descomprimido > MAX_DOCX_DESCOMPRIMIDO:
            raise ApplicationError(status_code=422, detail="El archivo Word excede el tamaño descomprimido permitido.")
        nombres = {e.filename.lower() for e in entradas}
        if "[content_types].xml" not in nombres or "word/document.xml" not in nombres:
            raise ApplicationError(status_code=422, detail="El archivo no tiene la estructura de un documento de Word.")
        if any(n.endswith("vbaproject.bin") for n in nombres):
            raise ApplicationError(status_code=422, detail="El documento de Word no puede contener macros.")
        try:
            tipos = paquete.read("[Content_Types].xml").decode("utf-8", "replace")
        except (KeyError, RuntimeError, zipfile.BadZipFile) as exc:
            raise ApplicationError(status_code=422, detail="El archivo Word está dañado.") from exc
        if "macroEnabled" in tipos or TIPO_DOCX_PRINCIPAL not in tipos:
            raise ApplicationError(
                status_code=422, detail="El documento de Word no es un .docx sin macros (formato no permitido).")


def inspeccionar(contenido: bytes, extension: str) -> int:
    """Valida el contenido y devuelve las páginas del PDF (1 para el DOCX, que no las tiene)."""
    if extension == "pdf":
        return inspeccionar_pdf(contenido)
    inspeccionar_docx(contenido)
    return 1


def _escribir(contenido: bytes, ruta: Path) -> None:
    ruta.parent.mkdir(parents=True, exist_ok=True)
    temporal = ruta.with_name(ruta.name + ".part")
    with open(temporal, "xb") as destino:
        destino.write(contenido)
        destino.flush()
        os.fsync(destino.fileno())
    os.replace(temporal, ruta)


async def guardar_plantilla(contenido: bytes, extension: str) -> dict:
    """Guarda un archivo con clave nueva y única; nunca sobrescribe."""
    if extension not in EXTENSIONES:
        raise ApplicationError(status_code=422, detail="Tipo de archivo no permitido.")
    clave = f"{uuid.uuid4().hex}.{extension}"
    await asyncio.to_thread(_escribir, contenido, ruta_plantilla(clave))
    return {"clave": clave, "tamano": len(contenido), "sha256": hashlib.sha256(contenido).hexdigest()}


async def leer_plantilla(clave: str) -> bytes:
    ruta = ruta_plantilla(clave)
    if not ruta.is_file():
        raise ApplicationError(status_code=404, detail="Archivo de plantilla no encontrado en el servidor")
    return await asyncio.to_thread(ruta.read_bytes)


async def eliminar_plantilla(clave: str) -> None:
    """Limpia un archivo recién guardado cuya versión no llegó a publicarse."""
    try:
        ruta_plantilla(clave).unlink(missing_ok=True)
    except (OSError, ApplicationError) as exc:
        logger.warning(f"No se pudo eliminar el archivo de plantilla no publicado {clave}: {exc}")
