# app/modulos/dual/services/reporte_services.py
import os

import fitz  # pymupdf
from app.application.errors import ApplicationError
from app.application.ports.uploads import FileUpload
from loguru import logger

from app.infrastructure.config.settings import settings
from app.infrastructure.integrations.drive import (
    upload_file_async,
    get_file_bytes_async,
)

MAX_PDF_SIZE = 10 * 1024 * 1024  # 10 MB
PDF_MAGIC = b"%PDF"


# Comprime PDF con PyMuPDF
def comprimir_pdf(file_bytes: bytes) -> bytes:
    try:
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        for page in doc:
            for img in page.get_images():
                xref = img[0]
                pix = fitz.Pixmap(doc, xref)
                if pix.width > 1200:
                    data = pix.tobytes("jpeg", jpg_quality=75)
                    doc.update_stream(xref, data)
        return doc.tobytes(garbage=4, deflate=True, clean=True)
    except Exception as e:
        logger.warning(f"Compresion PDF fallo, subiendo original: {e}")
        return file_bytes


# Ejecuta la responsabilidad especificada para este módulo.
def _dual_upload_path(matricula: str, cuatrimestre: str, semana: int) -> str:
    return os.path.join(
        settings.dual_upload_dir,
        matricula,
        cuatrimestre,
        f"semana_{semana}.pdf",
    )


# Ejecuta la responsabilidad especificada para este módulo.
async def guardar_pdf_local(
    archivo: FileUpload,
    matricula: str,
    cuatrimestre: str,
    semana: int,
) -> str:
    # Comprime y guarda PDF en sistema de archivos local.
    # Retorna ruta absoluta del archivo guardado.
    if not (archivo.filename or "").lower().endswith(".pdf"):
        raise ApplicationError(
            status_code=400,
            detail="Solo se aceptan archivos PDF",
        )

    contenido = await archivo.read()

    if len(contenido) > MAX_PDF_SIZE:
        raise ApplicationError(
            status_code=413,
            detail="El archivo excede el límite de 10 MB",
        )

    if contenido[:4] != PDF_MAGIC:
        raise ApplicationError(
            status_code=400,
            detail="El archivo no es un PDF válido",
        )

    contenido = comprimir_pdf(contenido)
    logger.info(
        f"PDF comprimido: {len(contenido)} bytes "
        f"({matricula}/semana_{semana})"
    )

    ruta = _dual_upload_path(matricula, cuatrimestre, semana)
    os.makedirs(os.path.dirname(ruta), exist_ok=True)

    with open(ruta, "wb") as f:
        f.write(contenido)

    logger.info(f"PDF guardado localmente: {ruta}")
    return ruta


# Ejecuta la responsabilidad especificada para este módulo.
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


# Valida, comprime y sube el PDF de un reporte semanal directo a Drive
async def procesar_y_subir_pdf_reporte(
    archivo: FileUpload,
    matricula: str,
    cuatrimestre: str,
    semana: int,
) -> str:
    if not (archivo.filename or "").lower().endswith(".pdf"):
        raise ApplicationError(
            status_code=400,
            detail="Solo se aceptan archivos PDF",
        )

    contenido = await archivo.read()

    if len(contenido) > MAX_PDF_SIZE:
        raise ApplicationError(
            status_code=413,
            detail="El archivo excede el límite de 10 MB",
        )

    if contenido[:4] != PDF_MAGIC:
        raise ApplicationError(
            status_code=400,
            detail="El archivo no es un PDF válido",
        )

    contenido = comprimir_pdf(contenido)
    logger.info(
        f"PDF comprimido: {len(contenido)} bytes "
        f"({matricula}/semana_{semana})"
    )

    nombre = f"{matricula}-S{semana}-{cuatrimestre}.pdf"
    file_id = await upload_file_async(
        contenido, nombre, "application/pdf", settings.drive_folder_dual
    )
    logger.info(f"PDF subido a Drive: {nombre} → {file_id}")
    return file_id


# Ejecuta la responsabilidad especificada para este módulo.
async def leer_pdf_local(ruta_local: str) -> bytes:
    # Lee archivo PDF local y retorna sus bytes. Lanza 404 si no existe.
    if not ruta_local or not os.path.exists(ruta_local):
        raise ApplicationError(
            status_code=404,
            detail="Archivo PDF no encontrado en el servidor",
        )
    with open(ruta_local, "rb") as f:
        return f.read()


# Lee archivo local y lo sube a Google Drive.
async def subir_pdf_a_drive_desde_local(
    ruta_local: str,
    matricula: str,
    cuatrimestre: str,
    semana: int,
) -> str:

    if not ruta_local or not os.path.exists(ruta_local):
        raise ApplicationError(
            status_code=404,
            detail="Archivo PDF local no encontrado. Ya fue procesado?",
        )

    with open(ruta_local, "rb") as f:
        contenido = f.read()

    nombre = f"{matricula}-S{semana}-{cuatrimestre}.pdf"
    file_id = await upload_file_async(
        contenido, nombre, "application/pdf", settings.drive_folder_dual
    )
    logger.info(f"PDF subido a Drive: {nombre} → {file_id}")
    return file_id


# RetornaPDF desde almacenamiento local o Drive, segun el estado del reporte
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
