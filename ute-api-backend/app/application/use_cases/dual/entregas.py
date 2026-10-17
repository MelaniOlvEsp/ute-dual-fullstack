from __future__ import annotations

from app.application.errors import ApplicationError
from app.application.use_cases.dual.archivado import exigir_vigente
from app.application.responses import FileResult
from app.domain import reports
from app.domain.reports import EntregaInvalida


def _verificar_recepcion(obligacion) -> None:
    """DP-13: solo se entrega o reenvía si el período de la obligación está abierto."""
    if obligacion["periodo_id"] is None:
        raise ApplicationError(
            status_code=409,
            detail="Esta semana aún no pertenece a un período; no se puede entregar.")
    if not obligacion["abierto"] or obligacion["cerrado"]:
        raise ApplicationError(
            status_code=409, detail="La recepción de este período no está abierta.")


async def _obligacion_propia(cur, obligacion_id, matricula):
    await cur.execute("dual.entregas.obligacion_propia", (obligacion_id, matricula))
    fila = await cur.fetchone()
    if not fila:
        # Ajena, inexistente o posterior a la baja: no se distingue.
        raise ApplicationError(status_code=404, detail="Obligación no encontrada")
    return dict(fila)


async def entregar(obligacion_id, fecha_inicio, fecha_fin, calificacion, archivo, user, *, runtime):
    """Entrega o reenvía el reporte de una obligación propia como una versión nueva e inmutable."""
    try:
        nota = reports.parse_nota(calificacion)
        reports.validar_fechas(fecha_inicio, fecha_fin)
    except EntregaInvalida as exc:
        raise ApplicationError(status_code=422, detail=str(exc)) from exc
    matricula = user["matricula"]

    # Rechazo barato antes de leer y guardar el archivo.
    async with runtime.database.read() as cur:
        _verificar_recepcion(await _obligacion_propia(cur, obligacion_id, matricula))

    servicios = runtime.services
    contenido = await servicios.leer_pdf_limitado(archivo)
    paginas = servicios.inspeccionar_pdf(contenido)
    documento = await servicios.guardar_documento(contenido)
    try:
        async with runtime.database.transaction() as cur:
            resultado = await _registrar(
                cur, obligacion_id, matricula, user["id"], nota,
                fecha_inicio, fecha_fin, documento, paginas)
    except BaseException:
        # Solo se descarta el archivo recién guardado; nunca uno anterior.
        await servicios.eliminar_documento(documento["clave"])
        raise
    if resultado["repetido"]:
        await servicios.eliminar_documento(documento["clave"])
    return resultado


async def _registrar(cur, obligacion_id, matricula, usuario_id, nota,
                     fecha_inicio, fecha_fin, documento, paginas):
    # Serializa por obligación: dos envíos simultáneos nunca crean dos reportes ni dos versiones.
    await cur.execute("dual.entregas.lock", (str(obligacion_id),))
    obligacion = await _obligacion_propia(cur, obligacion_id, matricula)
    if obligacion["periodo_id"] is not None:
        # C07 (AC-15): comparte el bloqueo de la fila del período con el cierre, que lo toma exclusivo.
        # Si el cierre confirma primero, la lectura siguiente ya ve el período cerrado (409); si la
        # entrega gana, el cierre espera a que termine y la entrega queda antes del cierre.
        await cur.execute("dual.cierres.bloquear_compartido", (obligacion["periodo_id"],))
        obligacion = await _obligacion_propia(cur, obligacion_id, matricula)
    _verificar_recepcion(obligacion)

    await cur.execute("dual.entregas.reporte_de_obligacion", (obligacion_id,))
    fila = await cur.fetchone()
    reporte = dict(fila) if fila else None

    if reporte and reporte["estado"] == "Aprobada":
        raise ApplicationError(status_code=409, detail="Este reporte ya fue aprobado.")
    if reporte and reporte["estado"] == "Pendiente":
        await cur.execute("dual.entregas.version_actual", (reporte["id"],))
        actual = await cur.fetchone()
        if actual and dict(actual)["sha256"] == documento["sha256"]:
            actual = dict(actual)
            if (actual["fecha_inicio"], actual["fecha_fin"], actual["nota"]) == (fecha_inicio, fecha_fin, nota):
                # Reintento idéntico: no duplica la versión.
                return {"mensaje": "La entrega ya estaba registrada", "reporte_id": reporte["id"],
                        "version": actual["numero"], "repetido": True}
        raise ApplicationError(
            status_code=409, detail="Tienes una versión pendiente de revisión; espera la decisión.")

    await cur.execute("dual.entregas.insert_documento", (
        documento["clave"], documento["tamano"], documento["sha256"], paginas, usuario_id))
    documento_id = dict(await cur.fetchone())["id"]

    if reporte is None:
        await cur.execute("dual.entregas.insert_reporte", (
            matricula, obligacion["periodo"], obligacion["ordinal"], nota,
            fecha_inicio, fecha_fin, documento["ruta"], obligacion_id))
        reporte_id = dict(await cur.fetchone())["id"]
        numero = 1
    else:
        # Reenvío tras rechazo: la decisión anterior se conserva en la versión que la recibió.
        reporte_id = reporte["id"]
        numero = (reporte["ultima"] or 0) + 1
        await cur.execute("dual.entregas.snapshot_decision", (
            "Rechazada", reporte["nota_agente"], reporte["revisado_por"],
            reporte["revisado_en"], reporte_id, reporte["ultima"]))
        await cur.execute("dual.entregas.reenviar", (
            nota, fecha_inicio, fecha_fin, documento["ruta"], reporte_id))

    await cur.execute("dual.entregas.insert_version", (
        reporte_id, numero, fecha_inicio, fecha_fin, nota, documento_id, usuario_id))
    version = dict(await cur.fetchone())
    return {"mensaje": "Reporte recibido", "reporte_id": reporte_id,
            "version": version["numero"], "repetido": False}


async def versiones_de_reporte(reporte_id, user, *, runtime):
    async with runtime.database.read() as cur:
        await cur.execute("dual.entregas.versiones", (reporte_id, user["matricula"]))
        filas = [dict(f) for f in await cur.fetchall()]
    if not filas:
        raise ApplicationError(status_code=404, detail="Reporte no encontrado")
    return filas


async def descargar_version(reporte_id, numero, user, *, runtime, documento="original"):
    """Descarga el original o, si la versión fue aprobada, el firmado de una versión propia."""
    async with runtime.database.read() as cur:
        await cur.execute("dual.entregas.version_documento", (reporte_id, user["matricula"], numero))
        fila = await cur.fetchone()
    if not fila:
        raise ApplicationError(status_code=404, detail="Versión no encontrada")
    datos_fila = dict(fila)
    exigir_vigente(datos_fila, documento)
    clave = datos_fila["firmado" if documento == "firmado" else "original"]
    if not clave:
        raise ApplicationError(status_code=404, detail="Esta versión no tiene documento firmado")
    contenido = await runtime.services.leer_documento(clave)
    sufijo = "-firmado" if documento == "firmado" else ""
    return FileResult(
        iter([contenido]),
        media_type="application/pdf",
        headers={"Content-Disposition":
                 f'attachment; filename="{user["matricula"]}-v{int(numero)}{sufijo}.pdf"'},
    )
