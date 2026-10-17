"""PDF de reportes semanales: validación real y almacenamiento privado (C05, C10A).

El original se conserva byte a byte (sin recompresión). Las claves de almacenamiento las genera el servidor; el
cliente nunca aporta rutas ni nombres de archivo. Los documentos viven en el almacenamiento privado del
contrato de C10A (Drive en el piloto): estas funciones solo traducen sus errores y verifican el SHA-256.
"""
import asyncio
import hashlib
import re
import time
import uuid

import fitz  # pymupdf
from loguru import logger

from app.application.errors import ApplicationError
from app.domain.reports import MAX_PDF_BYTES
from app.infrastructure.storage.base import (
    AlmacenamientoNoDisponible, ArchivoNoEncontrado, ArchivoYaExiste)
from app.infrastructure.storage.registro import get_storage

PDF_MAGIC = b"%PDF-"
_CLAVE = re.compile(r"^[0-9a-f]{32}\.pdf$")
_BLOQUE = 64 * 1024
ESPACIO = "documentos"


def validar_clave(clave: str) -> str:
    # Solo claves con el formato generado por el servidor: evita cualquier clave ajena.
    if not _CLAVE.fullmatch(clave or ""):
        raise ApplicationError(status_code=404, detail="Documento no disponible")
    return clave


def no_disponible(error: AlmacenamientoNoDisponible) -> ApplicationError:
    return ApplicationError(
        status_code=503,
        detail="El almacenamiento de archivos no está disponible en este momento; vuelve a intentarlo más tarde.")

# Lee el archivo recibido en bloques y corta al superar el límite, sin cargarlo completo antes.
async def leer_pdf_limitado(archivo) -> bytes:
    if not (archivo.filename or "").lower().endswith(".pdf"):
        raise ApplicationError(status_code=422, detail="Solo se aceptan archivos PDF.")
    partes, total = [], 0
    while True:
        bloque = await archivo.read(_BLOQUE)
        if not bloque:
            break
        total += len(bloque)
        if total > MAX_PDF_BYTES:
            raise ApplicationError(status_code=413, detail="El PDF excede el límite de 10 MB.")
        partes.append(bloque)
    return b"".join(partes)


# Comprueba que el contenido sea un PDF legible; devuelve su número de páginas.
def inspeccionar_pdf(contenido: bytes) -> int:
    if not contenido:
        raise ApplicationError(status_code=422, detail="El archivo está vacío.")
    if not contenido.startswith(PDF_MAGIC):
        raise ApplicationError(status_code=422, detail="El archivo no es un PDF válido.")
    try:
        documento = fitz.open(stream=contenido, filetype="pdf")
    except Exception as exc:
        raise ApplicationError(status_code=422, detail="El PDF está dañado y no se puede abrir.") from exc
    try:
        if documento.needs_pass or documento.is_encrypted:
            raise ApplicationError(
                status_code=422,
                detail="El PDF está protegido; entrega una copia sin contraseña ni cifrado.")
        if documento.is_repaired:
            raise ApplicationError(
                status_code=422, detail="El PDF está dañado o incompleto; genera el archivo de nuevo.")
        paginas = documento.page_count
        if paginas < 1:
            raise ApplicationError(status_code=422, detail="El PDF no tiene páginas.")
        # Renderizar la primera página a baja resolución confirma que el contenido es legible.
        documento.load_page(0).get_pixmap(matrix=fitz.Matrix(0.2, 0.2))
        return paginas
    except ApplicationError:
        raise
    except Exception as exc:
        raise ApplicationError(status_code=422, detail="No se pudo leer el contenido del PDF.") from exc
    finally:
        documento.close()


# Guarda el original con una clave nueva y única; nunca sobrescribe un documento existente.
async def guardar_documento(contenido: bytes) -> dict:
    clave = uuid.uuid4().hex + ".pdf"
    try:
        guardado = await asyncio.to_thread(get_storage().guardar, ESPACIO, clave, contenido)
    except AlmacenamientoNoDisponible as error:
        logger.error("No se pudo guardar un documento: {} ({})", error.motivo, error.codigo)
        raise no_disponible(error) from error
    except ArchivoYaExiste as error:
        raise ApplicationError(status_code=500, detail="No se pudo guardar el documento.") from error
    return {"clave": clave, "tamano": guardado["tamano"], "sha256": guardado["sha256"]}


async def leer_documento(clave: str, sha256: str | None = None) -> bytes:
    """Lee un documento; si se indica el SHA-256 registrado, un contenido distinto nunca se entrega."""
    validar_clave(clave)
    try:
        contenido = await asyncio.to_thread(get_storage().leer, ESPACIO, clave)
    except ArchivoNoEncontrado as error:
        raise ApplicationError(status_code=404, detail="Archivo PDF no encontrado en el servidor") from error
    except AlmacenamientoNoDisponible as error:
        logger.error("No se pudo leer un documento: {} ({})", error.motivo, error.codigo)
        raise no_disponible(error) from error
    if sha256 and hashlib.sha256(contenido).hexdigest() != sha256:
        logger.error("El documento {} no coincide con su huella registrada", clave)
        raise ApplicationError(
            status_code=502,
            detail="El archivo almacenado no coincide con su huella registrada; no se entrega.")
    return contenido


# Elimina solo un documento recién guardado cuyo registro no llegó a confirmarse.
async def eliminar_documento(clave: str) -> None:
    try:
        await asyncio.to_thread(get_storage().eliminar, ESPACIO, validar_clave(clave))
    except (AlmacenamientoNoDisponible, ApplicationError, OSError) as exc:
        logger.warning(f"No se pudo eliminar el documento no confirmado {clave}: {exc}")


# C08B: eliminación definitiva de un documento depurado. A diferencia de `eliminar_documento`, un fallo
# real (Drive, red, cuota) se propaga para que la purga quede pendiente y se reintente; un archivo que ya
# no existe cuenta como eliminado (idempotente).
async def purgar_documento(clave: str) -> bool:
    try:
        return await asyncio.to_thread(get_storage().eliminar, ESPACIO, validar_clave(clave))
    except AlmacenamientoNoDisponible as error:
        raise OSError(f"Almacenamiento no disponible ({error.codigo})") from error


# Limpia por referencia los archivos que ninguna fila de `documentos` apunta (fallos a mitad de una
# entrega). Solo toca claves con la forma del servidor y con antigüedad suficiente.
def limpiar_huerfanos(claves_referenciadas: set, antiguedad_segundos: int = 3600) -> list:
    almacenamiento = get_storage()
    limite = time.time() - antiguedad_segundos
    eliminados = []
    for archivo in almacenamiento.listar(ESPACIO):
        nombre = archivo["clave"][:-5] if archivo["clave"].endswith(".part") else archivo["clave"]
        if archivo["creado"] > limite or not _CLAVE.fullmatch(nombre):
            continue
        if archivo["clave"].endswith(".part") or nombre not in claves_referenciadas:
            almacenamiento.eliminar(ESPACIO, archivo["clave"])
            eliminados.append(archivo["clave"])
    return eliminados