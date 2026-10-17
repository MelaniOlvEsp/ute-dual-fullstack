"""PDF de reportes semanales: validación real y almacenamiento privado (C05).

El original se conserva byte a byte (sin recompresión). Las claves de almacenamiento las genera
el servidor; el cliente nunca aporta rutas ni nombres de archivo. Drive solo se usa para leer
documentos heredados y queda NO_VERIFICADO (DP-08).
"""
import asyncio
import hashlib
import os
import re
import time
import uuid
from pathlib import Path

import fitz  # pymupdf
from loguru import logger

from app.application.errors import ApplicationError
from app.domain.reports import MAX_PDF_BYTES
from app.infrastructure.config.settings import settings
from app.infrastructure.integrations.drive import get_file_bytes_async

PDF_MAGIC = b"%PDF-"
_CLAVE = re.compile(r"^[0-9a-f]{32}\.pdf$")
_BLOQUE = 64 * 1024


def _raiz() -> Path:
    return Path(settings.dual_upload_dir) / "documentos"


def ruta_documento(clave: str) -> Path:
    # Solo claves con el formato generado por el servidor: evita cualquier recorrido de rutas.
    if not _CLAVE.fullmatch(clave or ""):
        raise ApplicationError(status_code=404, detail="Documento no disponible")
    return _raiz() / clave[:2] / clave


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


def _escribir(contenido: bytes, ruta: Path) -> None:
    ruta.parent.mkdir(parents=True, exist_ok=True)
    temporal = ruta.with_name(ruta.name + ".part")
    with open(temporal, "xb") as destino:
        destino.write(contenido)
        destino.flush()
        os.fsync(destino.fileno())
    os.replace(temporal, ruta)


# Guarda el original con una clave nueva y única; nunca sobrescribe un documento existente.
async def guardar_documento(contenido: bytes) -> dict:
    clave = uuid.uuid4().hex + ".pdf"
    ruta = ruta_documento(clave)
    await asyncio.to_thread(_escribir, contenido, ruta)
    return {
        "clave": clave, "ruta": str(ruta), "tamano": len(contenido),
        "sha256": hashlib.sha256(contenido).hexdigest(),
    }


async def leer_documento(clave: str) -> bytes:
    ruta = ruta_documento(clave)
    if not ruta.is_file():
        raise ApplicationError(status_code=404, detail="Archivo PDF no encontrado en el servidor")
    return await asyncio.to_thread(ruta.read_bytes)


# Elimina solo un documento recién guardado cuyo registro no llegó a confirmarse.
async def eliminar_documento(clave: str) -> None:
    try:
        ruta_documento(clave).unlink(missing_ok=True)
    except (OSError, ApplicationError) as exc:
        logger.warning(f"No se pudo eliminar el documento no confirmado {clave}: {exc}")


# C08B: eliminación definitiva de un documento depurado. A diferencia de `eliminar_documento`, un fallo
# real (permisos, disco) se propaga para que la purga quede pendiente y se reintente; un archivo que
# ya no existe cuenta como eliminado (idempotente).
async def purgar_documento(clave: str) -> bool:
    ruta = ruta_documento(clave)
    existia = ruta.is_file()
    await asyncio.to_thread(ruta.unlink, True)
    return existia


# Limpia por referencia los archivos que ninguna fila de `documentos` apunta (fallos a mitad de
# una entrega). Solo toca archivos con la forma de clave del servidor y con antigüedad suficiente.
def limpiar_huerfanos(claves_referenciadas: set, antiguedad_segundos: int = 3600) -> list:
    eliminados = []
    raiz = _raiz()
    if not raiz.is_dir():
        return eliminados
    limite = time.time() - antiguedad_segundos
    for ruta in raiz.rglob("*"):
        if not ruta.is_file() or ruta.stat().st_mtime > limite:
            continue
        nombre = ruta.name[:-5] if ruta.name.endswith(".part") else ruta.name
        if not _CLAVE.fullmatch(nombre):
            continue
        if ruta.name.endswith(".part") or nombre not in claves_referenciadas:
            ruta.unlink(missing_ok=True)
            eliminados.append(ruta.name)
    return eliminados


# --- Lectura de documentos heredados (ruta local o Drive) ---------------------------------

async def eliminar_pdf_local(ruta_local: str | None) -> None:
    # Elimina archivo PDF local. No-op si ruta es None o archivo no existe.
    if not ruta_local:
        return
    try:
        if os.path.exists(ruta_local):
            os.remove(ruta_local)
            logger.info(f"PDF local eliminado: {ruta_local}")
    except OSError as e:
        logger.warning(f"Error eliminando PDF local {ruta_local}: {e}")


async def leer_pdf_local(ruta_local: str) -> bytes:
    # Lee archivo PDF local y retorna sus bytes. Lanza 404 si no existe.
    if not ruta_local or not os.path.exists(ruta_local):
        raise ApplicationError(
            status_code=404,
            detail="Archivo PDF no encontrado en el servidor",
        )
    with open(ruta_local, "rb") as f:
        return f.read()


# Retorna PDF desde almacenamiento local o Drive, segun el estado del reporte
async def obtener_pdf_bytes(reporte: dict) -> bytes:
    local_path = reporte.get("archivo_pdf_local")
    drive_id = reporte.get("archivo_pdf_url")

    if local_path:
        return await leer_pdf_local(local_path)

    if drive_id:
        try:
            return await get_file_bytes_async(drive_id)
        except Exception as e:
            logger.error(f"Error descargando PDF de Drive ({drive_id}): {e}")
            raise ApplicationError(
                status_code=500,
                detail="Error al obtener el archivo desde Drive",
            )

    raise ApplicationError(
        status_code=404,
        detail="Archivo PDF no disponible para este reporte",
    )
