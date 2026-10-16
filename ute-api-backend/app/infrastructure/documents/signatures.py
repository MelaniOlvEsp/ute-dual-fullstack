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


ANCLA_FILA = 'Tutor académico'
ENCABEZADO_COLUMNA = 'Firma'
_MARGEN = 2.0
_GROSOR_LINEA = 2.5


def _lineas(page):
    # Los bordes de la tabla pueden ser trazos o rectángulos delgados; ambos tienen una
    # dimensión casi nula.
    verticales, horizontales = [], []
    for dibujo in page.get_drawings():
        r = dibujo['rect']
        if r.width <= _GROSOR_LINEA and r.height > 3:
            verticales.append(r)
        elif r.height <= _GROSOR_LINEA and r.width > 3:
            horizontales.append(r)
    return verticales, horizontales


def localizar_celda_firma(page):
    """Rectángulo vacío de la columna "Firma" en la fila "Tutor académico", o None.

    Se ancla en el texto de la fila y en el encabezado de la columna, y toma los límites de las
    líneas dibujadas de la tabla. Si la fila, la columna o los bordes no se identifican, o la
    celda tiene contenido, devuelve None para que la firma no se estampe a ciegas (DP-07).
    """
    if page.rotation:
        return None
    anclas = page.search_for(ANCLA_FILA)
    if not anclas:
        return None
    ancla = anclas[-1]
    cabeceras = [fitz.Rect(w[:4]) for w in page.get_text('words')
                 if w[4] == ENCABEZADO_COLUMNA and w[3] <= ancla.y0 + 1]
    if not cabeceras:
        return None
    cabecera = max(cabeceras, key=lambda r: r.y0)
    centro_x = (cabecera.x0 + cabecera.x1) / 2
    verticales, horizontales = _lineas(page)
    cubren = [r for r in horizontales if r.x0 <= ancla.x0 and r.x1 >= ancla.x1]
    arriba = [(r.y0 + r.y1) / 2 for r in cubren if (r.y0 + r.y1) / 2 <= ancla.y0]
    abajo = [(r.y0 + r.y1) / 2 for r in cubren if (r.y0 + r.y1) / 2 >= ancla.y1]
    if not arriba or not abajo:
        return None
    y0, y1 = max(arriba), min(abajo)
    en_fila = [r for r in verticales if r.y0 <= y0 + 3 and r.y1 >= y1 - 3]
    izquierda = [(r.x0 + r.x1) / 2 for r in en_fila if (r.x0 + r.x1) / 2 <= centro_x]
    derecha = [(r.x0 + r.x1) / 2 for r in en_fila if (r.x0 + r.x1) / 2 >= centro_x]
    if not izquierda or not derecha:
        return None
    celda = fitz.Rect(max(izquierda) + _MARGEN, y0 + _MARGEN, min(derecha) - _MARGEN, y1 - _MARGEN)
    if celda.width < 40 or celda.height < 15:
        return None
    # La celda debe estar libre: sin texto, imágenes ni relleno de color.
    if any(fitz.Rect(w[:4]).intersects(celda) for w in page.get_text('words')):
        return None
    if any(fitz.Rect(i['bbox']).intersects(celda) for i in page.get_image_info()):
        return None
    for dibujo in page.get_drawings():
        relleno, r = dibujo.get('fill'), dibujo['rect']
        if relleno and tuple(relleno) != (1.0, 1.0, 1.0) and (r & celda).get_area() > celda.get_area() / 2:
            return None
    return celda


def estampar_firma(pdf_bytes: bytes, signature: bytes, tutor_name: str):
    """Devuelve (pdf, modo): firma en la celda del tutor ("celda") o, si no se reconoce el
    formato, en una hoja adicional ("hoja_adicional"). El original no se modifica."""
    validate_signature(signature, 'image/png' if signature[:8] ==
                       b'\x89PNG\r\n\x1a\n' else 'image/jpeg')
    try:
        with fitz.open(stream=pdf_bytes, filetype='pdf') as documento:
            paginas = documento.page_count
            for numero in range(paginas - 1, -1, -1):
                pagina = documento[numero]
                celda = localizar_celda_firma(pagina)
                if celda is None:
                    continue
                antes = len(pagina.get_image_info())
                pagina.insert_image(celda, stream=signature, keep_proportion=True, overlay=True)
                if len(pagina.get_image_info()) != antes + 1:
                    break  # no quedó estampada: se usa el respaldo
                resultado = documento.tobytes(deflate=True)
                if _paginas(resultado) == paginas:
                    return resultado, 'celda'
                break
    except ApplicationError:
        raise
    except Exception:
        pass  # cualquier falla del estampado en celda se resuelve con el respaldo
    return sign_pdf(pdf_bytes, signature, tutor_name), 'hoja_adicional'


def _paginas(pdf_bytes: bytes) -> int:
    with fitz.open(stream=pdf_bytes, filetype='pdf') as documento:
        return documento.page_count


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
