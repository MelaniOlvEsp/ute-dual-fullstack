from __future__ import annotations

from collections import defaultdict
from decimal import Decimal

from app.application.errors import ApplicationError
from app.domain import calendar, grading


def _texto_pendientes(pendientes):
    if pendientes == 1:
        return "Queda 1 reporte pendiente de revisión."
    return f"Quedan {pendientes} reportes pendientes de revisión."


def _estado(periodo):
    """Recepción y evaluación por período (RN-23); independientes de las fechas calendario."""
    if periodo["evaluacion_finalizada_en"] is not None:
        evaluacion = "finalizada"
    else:
        evaluacion = "en_curso"
    if periodo["cerrado"]:
        recepcion = "cerrada"
    elif periodo["abierto"]:
        recepcion = "abierta"
    else:
        recepcion = "sin_abrir"
    return recepcion, evaluacion


def _presentar_periodo(periodo):
    recepcion, evaluacion = _estado(periodo)
    return {
        "id": periodo["id"],
        "cuatrimestre": periodo["cuatrimestre"],
        "periodo_label": periodo["periodo_label"] or periodo["cuatrimestre"],
        "fecha_inicio": periodo["fecha_inicio"],
        "fecha_fin": periodo["fecha_fin"],
        "recepcion": recepcion,
        "evaluacion": evaluacion,
        # RN-24: el cierre efectivo se muestra aparte de las fechas calendario.
        "cierre_efectivo": calendar.fecha_de_cierre(periodo["cerrado_at"]),
        "cerrado_en": periodo["cerrado_at"],
        "finalizada_en": periodo["evaluacion_finalizada_en"],
    }


async def _periodo(cur, periodo_id, consulta="dual.cierres.periodo"):
    await cur.execute(consulta, (periodo_id,))
    fila = await cur.fetchone()
    if not fila:
        raise ApplicationError(status_code=404, detail="Período no encontrado")
    return dict(fila)


async def listar(user, *, runtime):
    async with runtime.database.read() as cur:
        await cur.execute("dual.cierres.listar")
        return [_presentar_periodo(dict(f)) for f in await cur.fetchall()]


async def _resumen(cur, periodo):
    presentado = _presentar_periodo(periodo)
    cierre = presentado["cierre_efectivo"]
    await cur.execute("dual.cierres.conteos", (cierre, cierre, periodo["id"]))
    conteos = dict(await cur.fetchone())
    await cur.execute("dual.cierres.alumnos", (periodo["id"],))
    alumnos = [dict(f) for f in await cur.fetchall()]

    if presentado["evaluacion"] == "finalizada":
        # Final: se lee el resultado congelado, nunca se recalcula.
        await cur.execute("dual.cierres.resultados", (periodo["id"],))
        congelados = {r["matricula"]: dict(r) for r in await cur.fetchall()}
        for alumno in alumnos:
            fila = congelados.get(alumno["matricula"], {"suma": 0, "cantidad": 0, "promedio": None})
            alumno.update(suma=fila["suma"], aprobados=fila["cantidad"], promedio=fila["promedio"])
    else:
        # Provisional: se calcula en vivo con la misma regla que la finalización.
        await cur.execute("dual.cierres.aprobadas", (periodo["id"],))
        notas = defaultdict(list)
        for fila in await cur.fetchall():
            notas[fila["matricula"]].append(fila["nota"])
        for alumno in alumnos:
            resultado = grading.calcular(notas.get(alumno["matricula"], []))
            alumno.update(suma=resultado.suma, aprobados=resultado.cantidad, promedio=resultado.promedio)

    definitivo = presentado["evaluacion"] == "finalizada"
    for alumno in alumnos:
        promedio = alumno["promedio"]
        alumno["promedio"] = None if promedio is None else f"{Decimal(promedio):.2f}"
        alumno["promedio_texto"] = grading.mostrar(promedio)
        alumno["definitivo"] = definitivo
        alumno.pop("aprobadas", None)

    pendientes = conteos["pendientes_revision"]
    puede_cerrar = presentado["recepcion"] == "abierta"
    if presentado["recepcion"] != "cerrada":
        motivo_finalizar = "Cierra la recepción antes de finalizar la evaluación."
    elif presentado["evaluacion"] == "finalizada":
        motivo_finalizar = "La evaluación ya fue finalizada."
    elif pendientes:
        motivo_finalizar = _texto_pendientes(pendientes)
    else:
        motivo_finalizar = None
    return {
        "periodo": presentado,
        "conteos": conteos,
        "alumnos": alumnos,
        "puede_cerrar_recepcion": puede_cerrar,
        "puede_finalizar": motivo_finalizar is None,
        "motivo_finalizar": motivo_finalizar,
    }


async def resumen(periodo_id, user, *, runtime):
    async with runtime.database.read() as cur:
        return await _resumen(cur, await _periodo(cur, periodo_id))


async def cerrar_recepcion(periodo_id, user, *, runtime):
    """Cierra la recepción de un período identificado por ID (RN-18). Idempotente.

    Toma el bloqueo exclusivo de la fila del período: una entrega que compite con el cierre o gana
    y queda antes, o espera, ve el período cerrado y recibe 409.
    """
    async with runtime.database.transaction() as cur:
        periodo = await _periodo(cur, periodo_id, "dual.cierres.bloquear_exclusivo")
        if periodo["cerrado"]:
            return {"mensaje": "La recepción ya estaba cerrada", "repetido": True,
                    **await _resumen(cur, periodo)}
        if not periodo["abierto"]:
            raise ApplicationError(status_code=409, detail="Este período no tiene la recepción abierta.")
        await cur.execute("dual.cierres.cerrar", (user["id"], periodo["id"]))
        periodo = await _periodo(cur, periodo_id)
        return {"mensaje": "Recepción cerrada", "repetido": False, **await _resumen(cur, periodo)}


async def finalizar_evaluacion(periodo_id, user, *, runtime):
    """Finaliza la evaluación y congela el promedio de cada alumno (RN-20, RN-21, RN-22). Idempotente."""
    async with runtime.database.transaction() as cur:
        periodo = await _periodo(cur, periodo_id, "dual.cierres.bloquear_exclusivo")
        if periodo["evaluacion_finalizada_en"] is not None:
            return {"mensaje": "La evaluación ya estaba finalizada", "repetido": True,
                    **await _resumen(cur, periodo)}
        if not periodo["cerrado"]:
            raise ApplicationError(
                status_code=409, detail="Cierra la recepción antes de finalizar la evaluación.")
        await cur.execute("dual.cierres.pendientes", (periodo["id"],))
        pendientes = dict(await cur.fetchone())["pendientes"]
        if pendientes:
            raise ApplicationError(
                status_code=409, detail=f"No se puede finalizar: {_texto_pendientes(pendientes)}")

        await cur.execute("dual.cierres.alumnos", (periodo["id"],))
        matriculas = [dict(f)["matricula"] for f in await cur.fetchall()]
        await cur.execute("dual.cierres.aprobadas", (periodo["id"],))
        aprobadas = defaultdict(list)
        for fila in await cur.fetchall():
            aprobadas[fila["matricula"]].append((fila["reporte_id"], fila["nota"]))

        for matricula in matriculas:
            detalle = aprobadas.get(matricula, [])
            resultado = grading.calcular(nota for _, nota in detalle)
            await cur.execute("dual.cierres.insert_cierre", (
                periodo["id"], matricula, resultado.suma, resultado.cantidad, resultado.promedio, user["id"]))
            cierre_id = dict(await cur.fetchone())["id"]
            for reporte_id, nota in detalle:
                await cur.execute("dual.cierres.insert_nota", (cierre_id, reporte_id, nota))
        await cur.execute("dual.cierres.finalizar", (user["id"], periodo["id"]))
        periodo = await _periodo(cur, periodo_id)
        return {"mensaje": "Evaluación finalizada", "repetido": False, **await _resumen(cur, periodo)}
