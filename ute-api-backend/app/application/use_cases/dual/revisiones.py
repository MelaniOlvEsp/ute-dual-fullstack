from __future__ import annotations

import asyncio

from app.application.errors import ApplicationError
from app.application.use_cases.dual.archivado import PUNTERO_HEREDADO, exigir_vigente
from app.application.responses import FileResult
from app.domain import reviews
from app.domain.reviews import RevisionInvalida

_NO_GENERADO = "No se pudo generar el documento firmado; la revisión no se registró."


async def detalle(reporte_id, user, *, runtime):
    """Reporte con su ficha, todas las versiones y las decisiones y correcciones de cada una."""
    async with runtime.database.read() as cur:
        await cur.execute("dual.revisiones.detalle", (reporte_id,))
        fila = await cur.fetchone()
        if not fila:
            raise ApplicationError(status_code=404, detail="Reporte no encontrado")
        reporte = dict(fila)
        await cur.execute("dual.revisiones.versiones", (reporte_id,))
        versiones = [dict(v) for v in await cur.fetchall()]
        await cur.execute("dual.tutor.signature_exists", (user["id"],))
        firma = await cur.fetchone()
    reporte["versiones"] = versiones
    reporte["puede_revisar"] = bool(
        versiones and reporte["estado"] == "Pendiente" and versiones[0]["decision"] is None)
    reporte["firma_registrada"] = bool(firma)
    return reporte


async def revisar(reporte_id, numero, decision, observacion, calificacion, fecha_inicio, fecha_fin,
                  user, *, runtime):
    """Decide la versión `numero` del reporte: aprueba con firma o rechaza con observación.

    La decisión recae sobre una versión concreta; si ya existe una más nueva o la versión ya fue
    decidida, nada cambia (409). Aprobar guarda un documento firmado nuevo y conserva el original;
    si algo falla no queda aprobada ni archivo referenciado (RN-16).
    """
    try:
        texto = reviews.validar_decision(decision, observacion)
    except RevisionInvalida as exc:
        raise ApplicationError(status_code=422, detail=str(exc)) from exc

    async with runtime.database.read() as cur:
        await cur.execute("dual.revisiones.reporte", (reporte_id,))
        fila = await cur.fetchone()
        if not fila:
            raise ApplicationError(status_code=404, detail="Reporte no encontrado")
        reporte = dict(fila)
        await cur.execute("dual.revisiones.version", (reporte_id, numero))
        fila = await cur.fetchone()
        if not fila:
            raise ApplicationError(status_code=404, detail="Versión no encontrada")
        version = dict(fila)
        imagen = nombre = None
        if decision == "Aprobada" and version["revision_id"] is None:
            await cur.execute("dual.tutor.get_signature", (user["id"],))
            firma = await cur.fetchone()
            if not firma:
                raise ApplicationError(status_code=409, detail="Primero adjunta tu firma académica.")
            imagen = bytes(dict(firma)["imagen"])
            await cur.execute("dual.tutor.identity", (user["id"],))
            identidad = await cur.fetchone()
            nombre = (dict(identidad).get("nombre") if identidad else None) or user["sub"]

    try:
        nota, inicio, fin = reviews.valores_validados(version, calificacion, fecha_inicio, fecha_fin)
    except RevisionInvalida as exc:
        raise ApplicationError(status_code=422, detail=str(exc)) from exc

    servicios = runtime.services
    firmado = None
    if imagen is not None and version["numero"] == reporte["ultima"]:
        original = await servicios.leer_documento(version["clave_original"], version.get("sha_original"))
        pdf, modo = await asyncio.to_thread(servicios.estampar_firma, original, imagen, nombre)
        try:
            paginas = servicios.inspeccionar_pdf(pdf)
        except ApplicationError as exc:
            raise ApplicationError(status_code=500, detail=_NO_GENERADO) from exc
        firmado = dict(await servicios.guardar_documento(pdf), paginas=paginas, modo=modo)

    try:
        async with runtime.database.transaction() as cur:
            resultado = await _registrar(
                cur, reporte, version["numero"], decision, texto, nota, inicio, fin, firmado, user)
    except BaseException:
        # Solo se descarta el firmado recién guardado; nunca el original ni uno anterior.
        if firmado:
            await servicios.eliminar_documento(firmado["clave"])
        raise
    if resultado["repetido"] and firmado:
        await servicios.eliminar_documento(firmado["clave"])
    return resultado


async def _registrar(cur, reporte, numero, decision, observacion, nota, inicio, fin, firmado, user):
    reporte_id = reporte["id"]
    # Misma clave que la entrega (C05): revisión y reenvío simultáneos se serializan.
    await cur.execute("dual.entregas.lock", (str(reporte["obligacion_id"] or reporte_id),))
    await cur.execute("dual.revisiones.reporte_bloqueado", (reporte_id,))
    fila = await cur.fetchone()
    if not fila:
        raise ApplicationError(status_code=404, detail="Reporte no encontrado")
    actual = dict(fila)
    await cur.execute("dual.revisiones.version", (reporte_id, numero))
    fila = await cur.fetchone()
    if not fila:
        raise ApplicationError(status_code=404, detail="Versión no encontrada")
    version = dict(fila)

    if version["revision_id"] is not None:
        misma = (str(version["tutor_id"]) == str(user["id"]) and version["decision"] == decision
                 and version["observacion"] == observacion
                 and (version["rev_inicio"], version["rev_fin"], version["rev_nota"]) == (inicio, fin, nota))
        if misma:  # reintento idéntico: no duplica la revisión
            return {"mensaje": "La revisión ya estaba registrada", "estado": decision,
                    "version": numero, "repetido": True, "firma": None}
        raise ApplicationError(status_code=409, detail="Esta versión ya fue revisada.")
    if actual["ultima"] != numero:
        raise ApplicationError(
            status_code=409,
            detail="El alumno envió una versión más reciente; recarga el reporte antes de decidir.")
    if actual["estado"] != "Pendiente":
        raise ApplicationError(status_code=409, detail="Este reporte ya fue decidido.")
    if decision == "Aprobada" and not firmado:
        raise ApplicationError(status_code=409, detail="Primero adjunta tu firma académica.")

    firmado_id = None
    if firmado:
        await cur.execute("dual.revisiones.insert_firmado", (
            firmado["clave"], firmado["tamano"], firmado["sha256"], firmado["paginas"],
            user["id"], firmado["modo"]))
        firmado_id = dict(await cur.fetchone())["id"]
    await cur.execute("dual.revisiones.insert_revision", (
        version["id"], user["id"], decision, observacion, inicio, fin, nota, firmado_id))
    revision = dict(await cur.fetchone())
    for campo, previo, nuevo in reviews.correcciones(version, nota, inicio, fin):
        await cur.execute("dual.revisiones.insert_correccion", (revision["id"], campo, previo, nuevo))
    await cur.execute("dual.revisiones.decidir_version", (
        decision, observacion, user["id"], revision["revisado_en"], version["id"]))
    ruta = PUNTERO_HEREDADO
    await cur.execute("dual.revisiones.actualizar_reporte", (
        decision, observacion, user["id"], revision["revisado_en"], nota, inicio, fin,
        ruta, ruta, reporte_id))
    return {"mensaje": "Reporte aprobado" if decision == "Aprobada" else "Reporte rechazado",
            "estado": decision, "version": numero, "repetido": False,
            "firma": firmado["modo"] if firmado else None}


async def descargar(reporte_id, numero, documento, user, *, runtime):
    """Original o firmado de una versión, para el tutor que revisa."""
    async with runtime.database.read() as cur:
        await cur.execute("dual.revisiones.documentos", (numero, reporte_id))
        fila = await cur.fetchone()
    if not fila:
        raise ApplicationError(status_code=404, detail="Versión no encontrada")
    datos = dict(fila)
    exigir_vigente(datos, documento)
    clave = datos["firmado" if documento == "firmado" else "original"]
    if not clave:
        raise ApplicationError(status_code=404, detail="Esta versión no tiene documento firmado")
    contenido = await runtime.services.leer_documento(clave, datos.get("firmado_sha" if documento == "firmado" else "original_sha"))
    sufijo = "-firmado" if documento == "firmado" else ""
    return FileResult(
        iter([contenido]),
        media_type="application/pdf",
        headers={"Content-Disposition":
                 f'inline; filename="{datos["matricula"]}-v{int(numero)}{sufijo}.pdf"'},
    )
