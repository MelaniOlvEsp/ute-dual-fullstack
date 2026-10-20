"""Depuración de los archivos PDF de un período tras guardar el paquete ZIP (C08B, DP-14).

Solo se eliminan archivos físicos: las filas de `documentos` se conservan con su clave, tamaño y hash,
marcadas como archivadas; notas, promedios, versiones, revisiones y resultados congelados no se tocan.
La depuración se programa con un período de gracia (D3) y la ejecuta una tarea de fondo al vencer, con
reintento idempotente; durante la gracia el tutor o el coordinador pueden cancelarla.
"""
from __future__ import annotations


from loguru import logger

from app.application.errors import ApplicationError
from app.application.use_cases.dual.expediente import presentar_periodo, validar_texto
from app.application.use_cases.dual.paquetes import _alumno_en_periodo, _periodo_finalizado
from app.domain.organization import CAREER_BY_CODE

GRACIA_DIAS = 7


def _presentar_purga(fila: dict) -> dict:
    return {k: fila.get(k) for k in (
        "id", "alcance", "matricula", "carrera", "estado", "solicitada_en", "ejecutar_en", "completada_en",
        "cancelada_en", "archivos", "bytes", "intentos", "ultimo_error", "solicitada_por_nombre")}


def frase_esperada(periodo: dict, sujeto: str) -> str:
    return f"DEPURAR {periodo['periodo_label'] or periodo['cuatrimestre']} {sujeto}"


async def _documentos_del_alcance(cur, periodo, carrera, matricula):
    """Los mismos documentos que el paquete de archivo de C08 (versión aprobada vigente de cada reporte)."""
    if matricula:
        alumnos = [await _alumno_en_periodo(cur, matricula, periodo["id"])]
    else:
        await cur.execute("dual.paquetes.alumnos_carrera", (periodo["id"], carrera))
        alumnos = [dict(f) for f in await cur.fetchall()]
        if not alumnos:
            raise ApplicationError(status_code=404,
                                   detail="No hay alumnos de esa carrera con semanas en este período.")
    documentos = []
    for alumno in alumnos:
        await cur.execute("dual.paquetes.documentos", (alumno["matricula"], periodo["id"]))
        for r in (dict(f) for f in await cur.fetchall()):
            for tipo in ("firmado", "original"):
                if r.get(f"{tipo}_clave"):
                    documentos.append({
                        "id": r[f"{tipo}_id"], "clave": r[f"{tipo}_clave"], "tamano": r[f"{tipo}_tamano"],
                        "archivado": r.get(f"{tipo}_archivado"), "purga": r.get(f"{tipo}_purga")})
    return documentos


async def resumen(periodo_id, user, *, runtime):
    """Por carrera: archivos y bytes vigentes, paquete vigente, estado de la depuración y frase a escribir."""
    async with runtime.database.read() as cur:
        await cur.execute("dual.cierres.periodo", (periodo_id,))
        fila = await cur.fetchone()
        if not fila:
            raise ApplicationError(status_code=404, detail="Período no encontrado")
        fila = dict(fila)
        periodo = presentar_periodo(fila)
        if fila["evaluacion_finalizada_en"] is None:
            return {"periodo": periodo, "finalizada": False, "carreras": [], "purgas": [],
                    "gracia_dias": GRACIA_DIAS,
                    "motivo": "La depuración se habilita cuando la evaluación del período está finalizada."}
        await cur.execute("dual.purgas.resumen_carreras", (periodo_id,))
        filas = [dict(f) for f in await cur.fetchall()]
        await cur.execute("dual.purgas.paquetes_vigentes", (periodo_id, fila["evaluacion_finalizada_en"]))
        paquetes = {p["carrera"]: dict(p) for p in await cur.fetchall()}
        await cur.execute("dual.purgas.listar_periodo", (periodo_id,))
        purgas = [dict(p) for p in await cur.fetchall()]
    programadas = {p["carrera"] for p in purgas if p["alcance"] == "carrera" and p["estado"] == "programada"}
    carreras = []
    for f in filas:
        codigo = f["carrera"]
        total, vigentes = f["archivos_total"], f["archivos_vigentes"]
        if codigo in programadas:
            estado = "programada"
        elif total and vigentes == 0:
            estado = "depurado"
        elif vigentes < total:
            estado = "parcial"
        else:
            estado = "sin_depurar"
        paquete = paquetes.get(codigo)
        carreras.append({
            "codigo": codigo, "nombre": CAREER_BY_CODE[codigo].name if codigo in CAREER_BY_CODE else "Sin carrera",
            "alumnos": f["alumnos"], "archivos_total": total, "archivos_vigentes": vigentes,
            "bytes_vigentes": int(f["bytes_vigentes"]), "estado": estado,
            "paquete": None if not paquete else {
                "id": paquete["id"], "generado_en": paquete["generado_en"], "archivos": paquete["archivos"]},
            "puede_depurar": bool(codigo in CAREER_BY_CODE and paquete and vigentes > 0
                                  and estado in ("sin_depurar", "parcial")),
            "frase_esperada": frase_esperada(fila, codigo or ""),
        })
    return {"periodo": periodo, "finalizada": True, "carreras": carreras, "gracia_dias": GRACIA_DIAS,
            "purgas": [_presentar_purga(p) for p in purgas]}


async def programar(periodo_id, carrera, matricula, confirmar, frase, user, *, runtime):
    """Programa la eliminación de los PDF del alcance; no elimina nada hasta que venza la gracia."""
    if confirmar is not True:
        raise ApplicationError(status_code=422, detail="Confirma que ya guardaste la copia del paquete.")
    if bool(carrera) == bool(matricula):
        raise ApplicationError(status_code=422, detail="Indica la carrera o la matrícula, no ambas.")
    validar_texto(carrera, matricula, frase, campo="El dato")
    codigo = (carrera or "").upper() or None
    if codigo and codigo not in CAREER_BY_CODE:
        raise ApplicationError(status_code=404, detail="Carrera no encontrada")
    async with runtime.database.transaction() as cur:
        periodo = await _periodo_finalizado(cur, periodo_id)
        sujeto = matricula or codigo
        if (frase or "").strip() != frase_esperada(periodo, sujeto):
            raise ApplicationError(status_code=422, detail="La frase escrita no coincide con la indicada.")
        alcance = "alumno" if matricula else "carrera"
        await cur.execute("dual.purgas.programada_de_alcance", (periodo_id, alcance, matricula, codigo))
        existente = await cur.fetchone()
        if existente:
            existente = dict(existente)
            return {"repetido": True, "purga": {**_presentar_purga(existente), "alcance": alcance}}
        documentos = await _documentos_del_alcance(cur, periodo, codigo, matricula)
        if not documentos:
            raise ApplicationError(status_code=409, detail="No hay archivos aprobados que depurar en este alcance.")
        await cur.execute("dual.purgas.paquete_vigente", (
            periodo_id, alcance, matricula, codigo, periodo["evaluacion_finalizada_en"]))
        paquete = await cur.fetchone()
        if not paquete:
            raise ApplicationError(
                status_code=409,
                detail="Genera y guarda primero el paquete de archivo de este alcance (después de finalizar el período).")
        paquete = dict(paquete)
        if paquete["archivos"] != len(documentos):
            raise ApplicationError(
                status_code=409,
                detail="El paquete generado no coincide con los archivos actuales; genéralo de nuevo.")
        pendientes = [d for d in documentos if not d["archivado"]]
        if not pendientes:
            raise ApplicationError(status_code=409, detail="Los archivos de este alcance ya están depurados.")
        if any(d["purga"] for d in pendientes):
            raise ApplicationError(
                status_code=409,
                detail="Otra depuración programada ya incluye algunos de estos archivos; cancélala primero.")
        await cur.execute("dual.purgas.insertar", (
            periodo_id, alcance, matricula, codigo, paquete["id"], paquete["manifiesto_sha256"], user["id"],
            GRACIA_DIAS, len(pendientes), sum(d["tamano"] for d in pendientes)))
        nueva = dict(await cur.fetchone())
        await cur.execute("dual.purgas.marcar_documentos", (nueva["id"], [d["id"] for d in pendientes]))
    return {"repetido": False, "purga": {
        "id": nueva["id"], "alcance": alcance, "matricula": matricula, "carrera": codigo, "estado": "programada",
        "solicitada_en": nueva["solicitada_en"], "ejecutar_en": nueva["ejecutar_en"],
        "archivos": len(pendientes), "bytes": sum(d["tamano"] for d in pendientes)}}


async def cancelar(periodo_id, purga_id, user, *, runtime):
    """Cancela solo durante la gracia y antes del primer intento (DP-14)."""
    async with runtime.database.transaction() as cur:
        await cur.execute("dual.purgas.obtener", (purga_id, periodo_id))
        fila = await cur.fetchone()
        if not fila:
            raise ApplicationError(status_code=404, detail="Depuración no encontrada")
        fila = dict(fila)
        if fila["estado"] == "completada":
            raise ApplicationError(status_code=409, detail="Los archivos ya se eliminaron; no se puede cancelar.")
        if fila["estado"] == "cancelada":
            return {"repetido": True, "purga": _presentar_purga(fila)}
        await cur.execute("dual.purgas.cancelar", (user["id"], purga_id))
        if not await cur.fetchone():
            raise ApplicationError(
                status_code=409,
                detail="La gracia de cancelación terminó o la eliminación ya comenzó; "
                       "no se puede cancelar. Los archivos pendientes se reintentarán automáticamente.")
        await cur.execute("dual.purgas.liberar_documentos", (purga_id,))
    return {"repetido": False, "purga": {**_presentar_purga(fila), "estado": "cancelada"}}


async def ejecutar_purga(runtime, purga_id):
    """Persiste el inicio y luego el progreso de cada archivo, sin transacción de lote.

    El bloqueo de la purga serializa cada borrado, incluso entre procesos. Si el proceso cae tras
    borrar pero antes del commit, se reintenta el archivo ausente. Una ejecución que pierde el
    bloqueo cede el trabajo. `programada` conserva la intención hasta completar todo el alcance.
    """
    try:
        async with runtime.database.transaction() as cur:
            await cur.execute("dual.purgas.bloquear_vencida", (purga_id,))
            if not await cur.fetchone():
                return None
            await cur.execute("dual.purgas.iniciar", (purga_id,))
        while True:
            async with runtime.database.transaction() as cur:
                await cur.execute("dual.purgas.bloquear_vencida", (purga_id,))
                fila = await cur.fetchone()
                if not fila:
                    return None
                await cur.execute("dual.purgas.siguiente_documento", (purga_id,))
                documento = await cur.fetchone()
                if not documento:
                    await cur.execute("dual.purgas.completar", (purga_id,))
                    return {"id": purga_id, "archivos": fila["archivos"], "bytes": fila["bytes"]}
                # Como máximo un archivo externo por transacción. El progreso anterior ya está
                # confirmado y nunca se libera por cancelar una ejecución parcialmente fallida.
                await runtime.services.purgar_documento(documento["clave"])
                await cur.execute("dual.purgas.archivar_documento", (documento["id"],))
    except Exception as exc:
        logger.error("La depuración {} falló y se reintentará: {}", purga_id, exc)
        try:
            async with runtime.database.transaction() as cur:
                await cur.execute("dual.purgas.registrar_error", (str(exc)[:500], purga_id))
        except Exception as registro:
            logger.error("No se pudo registrar el error de la depuración {}: {}", purga_id, registro)
        raise


async def ejecutar_manual(periodo_id, purga_id, user, *, runtime):
    """Reintento manual de una depuración ya vencida (la tarea de fondo es la vía normal)."""
    async with runtime.database.read() as cur:
        await cur.execute("dual.purgas.listar_periodo", (periodo_id,))
        fila = next((dict(p) for p in await cur.fetchall() if str(p["id"]) == str(purga_id)), None)
    if not fila:
        raise ApplicationError(status_code=404, detail="Depuración no encontrada")
    if fila["estado"] == "completada":
        return {"repetido": True, "purga": _presentar_purga(fila)}
    if fila["estado"] == "cancelada":
        raise ApplicationError(status_code=409, detail="La depuración fue cancelada.")
    try:
        resultado = await ejecutar_purga(runtime, purga_id)
    except Exception as exc:
        raise ApplicationError(
            status_code=500,
            detail="La eliminación no se completó; el error quedó registrado y se reintentará automáticamente.") from exc
    if resultado is None:
        raise ApplicationError(
            status_code=409,
            detail="La depuración aún no vence o ya se está ejecutando; vuelve a intentar más tarde.")
    return {"repetido": False, "purga": {**_presentar_purga(fila), "estado": "completada",
                                         "archivos": resultado["archivos"], "bytes": resultado["bytes"]}}


async def ejecutar_vencidas(runtime):
    """Ejecuta las depuraciones cuya gracia venció; un fallo no detiene a las demás."""
    async with runtime.database.read() as cur:
        await cur.execute("dual.purgas.vencidas")
        pendientes = [dict(f)["id"] for f in await cur.fetchall()]
    ejecutadas = 0
    for purga_id in pendientes:
        try:
            if await ejecutar_purga(runtime, purga_id):
                ejecutadas += 1
        except Exception:
            continue
    return ejecutadas
