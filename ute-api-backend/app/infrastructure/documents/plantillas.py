"""Archivos de la plantilla común del reporte (C09, RN-26): pareja Word (.docx) + PDF.

Almacenamiento privado del contrato de C10A (Drive en el piloto), con claves generadas por el servidor (nunca el
nombre del cliente) y validación real del contenido: el PDF con el mismo inspector de C05 y el DOCX como contenedor
ZIP (OOXML) con límites contra bombas de descompresión, sin macros ni rutas peligrosas.
"""
from __future__ import annotations

import asyncio
import hashlib
import io
import re
import uuid
import zipfile

from loguru import logger

from app.application.errors import ApplicationError
from app.infrastructure.documents.dual_reports import inspeccionar_pdf, no_disponible
from app.infrastructure.storage.base import AlmacenamientoNoDisponible, ArchivoNoEncontrado, ArchivoYaExiste
from app.infrastructure.storage.registro import get_storage

MAX_PLANTILLA_BYTES = 10 * 1024 * 1024
MAX_DOCX_ENTRADAS = 500
MAX_DOCX_DESCOMPRIMIDO = 100 * 1024 * 1024
MAX_DOCX_RAZON = 200  # relación descomprimido/comprimido por entrada
TIPO_DOCX_PRINCIPAL = "application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"
EXTENSIONES = ("docx", "pdf")
_CLAVE = re.compile(r"^[0-9a-f]{32}\.(docx|pdf)$")
_BLOQUE = 64 * 1024


ESPACIO = "plantillas"


def validar_clave(clave: str) -> str:
    # Solo claves con el formato generado por el servidor: evita cualquier clave ajena.
    if not _CLAVE.fullmatch(clave or ""):
        raise ApplicationError(status_code=404, detail="Plantilla no disponible")
    return clave

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


async def guardar_plantilla(contenido: bytes, extension: str) -> dict:
    """Guarda un archivo con clave nueva y única; nunca sobrescribe."""
    if extension not in EXTENSIONES:
        raise ApplicationError(status_code=422, detail="Tipo de archivo no permitido.")
    clave = f"{uuid.uuid4().hex}.{extension}"
    try:
        guardado = await asyncio.to_thread(get_storage().guardar, ESPACIO, clave, contenido)
    except AlmacenamientoNoDisponible as error:
        logger.error("No se pudo guardar un archivo de plantilla: {} ({})", error.motivo, error.codigo)
        raise no_disponible(error) from error
    except ArchivoYaExiste as error:
        raise ApplicationError(status_code=500, detail="No se pudo guardar el archivo de plantilla.") from error
    return {"clave": clave, "tamano": guardado["tamano"], "sha256": guardado["sha256"]}


async def leer_plantilla(clave: str, sha256: str | None = None) -> bytes:
    """Lee un archivo de plantilla; con el SHA-256 registrado, un contenido distinto nunca se entrega."""
    validar_clave(clave)
    try:
        contenido = await asyncio.to_thread(get_storage().leer, ESPACIO, clave)
    except ArchivoNoEncontrado as error:
        raise ApplicationError(status_code=404, detail="Archivo de plantilla no encontrado en el servidor") from error
    except AlmacenamientoNoDisponible as error:
        logger.error("No se pudo leer un archivo de plantilla: {} ({})", error.motivo, error.codigo)
        raise no_disponible(error) from error
    if sha256 and hashlib.sha256(contenido).hexdigest() != sha256:
        logger.error("El archivo de plantilla {} no coincide con su huella registrada", clave)
        raise ApplicationError(
            status_code=502, detail="El archivo almacenado no coincide con su huella registrada; no se entrega.")
    return contenido


async def eliminar_plantilla(clave: str) -> None:
    """Limpia un archivo recién guardado cuya versión no llegó a publicarse."""
    try:
        await asyncio.to_thread(get_storage().eliminar, ESPACIO, validar_clave(clave))
    except (AlmacenamientoNoDisponible, ApplicationError, OSError) as exc:
        logger.warning(f"No se pudo eliminar el archivo de plantilla no publicado {clave}: {exc}")