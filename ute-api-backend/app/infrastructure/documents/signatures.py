"""Valida firmas manuscritas y estampa evidencia visible en PDF."""
from datetime import datetime, timezone
from io import BytesIO

import fitz
from PIL import Image, UnidentifiedImageError
from app.application.errors import ApplicationError

MAX_SIGNATURE_BYTES = 1024 * 1024


def validate_signature(raw: bytes, content_type: str) -> None:
    # Rechaza contenido arbitrario e imágenes excesivamente grandes.
    if not raw or len(raw) > MAX_SIGNATURE_BYTES:
        raise ApplicationError(413, 'La firma debe pesar menos de 1 MB')
    if content_type not in {'image/png', 'image/jpeg'}:
        raise ApplicationError(400, 'Firma permitida: PNG o JPEG')
    try:
        with Image.open(BytesIO(raw)) as image:
            if image.format != ('PNG' if content_type == 'image/png' else 'JPEG'):
                raise ApplicationError(400, 'El contenido no coincide con el tipo de firma')
            if image.width > 2400 or image.height > 2400:
                raise ApplicationError(400, 'Dimensiones de firma demasiado grandes')
            image.verify()
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as exc:
        raise ApplicationError(400, 'No se pudo leer la imagen de la firma') from exc


def sign_pdf(pdf_bytes: bytes, signature: bytes, tutor_name: str) -> bytes:
    # Incorpora firma gráfica y metadatos de revisión a la última hoja.
    validate_signature(signature, 'image/png' if signature[:8] ==
                       b'\x89PNG\r\n\x1a\n' else 'image/jpeg')
    try:
        with fitz.open(stream=pdf_bytes, filetype='pdf') as document:
            if document.page_count == 0:
                raise ApplicationError(400, 'El reporte PDF está vacío')
            # La hoja de firma preserva intacto el reporte del alumno.
            page = document.new_page(width=595, height=842)
            x, y, width, height = 56, 180, 230, 85
            page.insert_text((x, 95), 'Constancia de revisión académica',
                             fontsize=18, color=(0.12, 0.12, 0.12))
            page.insert_text((x, 135), 'Firma del tutor académico',
                             fontsize=11)
            page.insert_image(fitz.Rect(x, y, x + width, y + height),
                              stream=signature, keep_proportion=True,
                              overlay=True)
            detail = f'Tutor académico: {tutor_name[:55]}'
            when = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')
            page.insert_text((x, y + height + 35), detail, fontsize=10)
            page.insert_text((x, y + height + 55), f'Revisado: {when}',
                             fontsize=10)
            return document.tobytes(garbage=4, deflate=True)
    except ApplicationError:
        raise
    except Exception as exc:
        raise ApplicationError(400, 'No fue posible firmar el PDF') from exc
