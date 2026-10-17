from __future__ import annotations

from app.application.errors import ApplicationError
from app.domain import calendar


# La columna heredada `archivo_pdf_local` ya no apunta a ninguna ruta: los documentos viven en el almacenamiento
# privado (C10A) y se identifican por la clave de `documentos`. Se escribe NULL y nadie la lee.
PUNTERO_HEREDADO = None


def exigir_vigente(datos: dict, documento: str) -> None:
    """Un documento depurado (C08B) ya no existe en el almacenamiento: 410 con la fecha, no 404 ni 500.

    La fila, la clave, el tamaño y el hash se conservan como evidencia; lo que se perdió es el archivo.
    """
    archivado = datos.get("firmado_archivado" if documento == "firmado" else "original_archivado")
    if archivado:
        raise ApplicationError(
            status_code=410,
            detail=f"Este archivo se depuró el {calendar.fecha_de_cierre(archivado).isoformat()}; "
                   "las notas, el promedio y el historial se conservan.")