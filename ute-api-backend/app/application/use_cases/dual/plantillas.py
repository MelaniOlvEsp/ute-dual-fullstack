"""Plantilla común del reporte: pareja Word + PDF versionada (C09, RN-26, MP-12 y MP-13).

Publicar es atómico: se validan y guardan los dos archivos y, en una sola transacción, se inserta la versión
y se pasa la vigencia. Si algo falla no queda pareja incompleta ni archivos sueltos. Las versiones son
inmutables y publicar una nueva no altera reportes ni documentos ya entregados.
"""
from __future__ import annotations

from app.application.errors import ApplicationError
from app.application.responses import FileResult

TIPOS = {
    "word": ("docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
    "pdf": ("pdf", "application/pdf"),
}


def presentar(fila: dict) -> dict:
    return {
        "numero": fila["numero"], "vigente": fila["vigente"], "publicada_en": fila["publicada_en"],
        "publicada_por": fila["publicada_por_nombre"], "nota": fila["nota"],
        "word": {"tamano": fila["word_tamano"], "sha256": fila["word_sha256"]},
        "pdf": {"tamano": fila["pdf_tamano"], "sha256": fila["pdf_sha256"], "paginas": fila["pdf_paginas"]},
    }


async def vigente(user, *, runtime):
    """Metadatos de la versión vigente, o `{"vigente": null}` si el coordinador aún no publicó ninguna."""
    async with runtime.database.read() as cur:
        await cur.execute("dual.plantillas.vigente")
        fila = await cur.fetchone()
    return {"vigente": presentar(dict(fila)) if fila else None}


async def listar(user, *, runtime):
    async with runtime.database.read() as cur:
        await cur.execute("dual.plantillas.listar")
        return [presentar(dict(f)) for f in await cur.fetchall()]


async def descargar(numero, tipo, user, *, runtime):
    """Un archivo de una versión por número; cualquier rol autenticado (MP-13)."""
    if tipo not in TIPOS:
        raise ApplicationError(status_code=404, detail="Archivo de plantilla no encontrado")
    extension, media_type = TIPOS[tipo]
    async with runtime.database.read() as cur:
        await cur.execute("dual.plantillas.por_numero", (numero,))
        fila = await cur.fetchone()
    if not fila:
        raise ApplicationError(status_code=404, detail="Versión de plantilla no encontrada")
    contenido = await runtime.services.leer_plantilla(dict(fila)["word_clave" if tipo == "word" else "pdf_clave"])
    return FileResult(
        iter([contenido]), media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="Plantilla_Reporte_Dual_v{int(numero)}.{extension}"'})


async def publicar(word, pdf, nota, user, *, runtime):
    """Publica una pareja Word + PDF nueva; todo o nada."""
    servicios = runtime.services
    nota = (nota or "").strip() or None
    if nota and len(nota) > 200:
        raise ApplicationError(status_code=422, detail="La nota no puede exceder 200 caracteres.")
    contenido_word = await servicios.leer_limitado_plantilla(word, "docx")
    contenido_pdf = await servicios.leer_limitado_plantilla(pdf, "pdf")
    servicios.inspeccionar_plantilla(contenido_word, "docx")
    paginas = servicios.inspeccionar_plantilla(contenido_pdf, "pdf")

    guardados = []
    try:
        guardado_word = await servicios.guardar_plantilla(contenido_word, "docx")
        guardados.append(guardado_word["clave"])
        guardado_pdf = await servicios.guardar_plantilla(contenido_pdf, "pdf")
        guardados.append(guardado_pdf["clave"])
        async with runtime.database.transaction() as cur:
            await cur.execute("dual.plantillas.bloquear")
            await cur.execute("dual.plantillas.siguiente_numero")
            numero = dict(await cur.fetchone())["numero"]
            await cur.execute("dual.plantillas.retirar_vigente")
            await cur.execute("dual.plantillas.insertar", (
                numero, user["id"], nota,
                guardado_word["clave"], guardado_word["tamano"], guardado_word["sha256"],
                guardado_pdf["clave"], guardado_pdf["tamano"], guardado_pdf["sha256"], paginas))
            nueva = dict(await cur.fetchone())
    except BaseException:
        for clave in guardados:
            await servicios.eliminar_plantilla(clave)
        raise
    return {"numero": nueva["numero"], "publicada_en": nueva["publicada_en"], "vigente": True,
            "word": {"tamano": guardado_word["tamano"], "sha256": guardado_word["sha256"]},
            "pdf": {"tamano": guardado_pdf["tamano"], "sha256": guardado_pdf["sha256"], "paginas": paginas}}
