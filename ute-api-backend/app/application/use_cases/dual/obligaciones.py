from __future__ import annotations

from app.application.errors import ApplicationError
from app.domain import calendar

# Estados derivados de la obligación (RN-09/RN-10): no se almacenan.
OVERDUE = "Overdue"
PENDING = "Pending"


async def generar(cur, incorporacion, hasta):
    """Genera o ajusta las obligaciones de una incorporación de forma idempotente.

    Serializa por incorporación con un bloqueo transaccional. Nunca borra filas: la baja
    recorta `fin_efectivo` de su semana y no genera semanas posteriores.
    """
    await cur.execute("dual.obligaciones.lock", (str(incorporacion["id"]),))
    semanas = calendar.semanas_incorporacion(
        incorporacion["fecha_inicio"], incorporacion.get("fecha_baja"), hasta)
    for semana in semanas:
        await cur.execute("dual.obligaciones.upsert", (
            incorporacion["id"], semana.semana_inicio, semana.semana_fin,
            semana.inicio_efectivo, semana.fin_efectivo, semana.parcial,
            semana.semana_fin, semana.semana_fin))
    return len(semanas)


async def sincronizar(cur, hasta, matricula=None):
    """Completa las semanas faltantes hasta la semana vigente (todas las activas o un alumno)."""
    await cur.execute("dual.obligaciones.candidates", (matricula, matricula))
    for fila in await cur.fetchall():
        inc = dict(fila)
        baja = inc["fecha_baja"]
        limite = min(hasta, baja) if baja is not None else hasta
        if limite < inc["fecha_inicio"]:
            continue
        ultima = inc["ultima"]
        if ultima is not None and ultima >= calendar.lunes_de(limite):
            continue
        await generar(cur, inc, hasta)


async def abrir_periodo_resuelve(cur, periodo_id, fecha_inicio, fecha_fin):
    """Asigna el período a obligaciones ya generadas que no lo tenían (período creado después)."""
    await cur.execute("dual.obligaciones.backfill_period", (periodo_id, fecha_inicio, fecha_fin))


def _presentar(filas, hoy):
    resultado = []
    for fila in filas:
        item = dict(fila)
        item["estado"] = calendar.estado_obligacion(item["semana_fin"], hoy, item["recibida"])
        resultado.append(item)
    return resultado


async def mis_obligaciones(matricula, periodo, *, runtime, hoy=None):
    hoy = hoy or calendar.hoy()
    async with runtime.database.transaction() as cur:
        await sincronizar(cur, hoy, matricula)
        await cur.execute("dual.obligaciones.by_student", (matricula, periodo, periodo))
        return _presentar(await cur.fetchall(), hoy)


async def obligaciones_de_alumno(matricula, periodo, user, *, runtime, hoy=None):
    hoy = hoy or calendar.hoy()
    async with runtime.database.transaction() as cur:
        await cur.execute("dual.obligaciones.student_exists", (matricula,))
        if not await cur.fetchone():
            raise ApplicationError(status_code=404, detail="Alumno no encontrado")
        await sincronizar(cur, hoy, matricula)
        await cur.execute("dual.obligaciones.by_student", (matricula, periodo, periodo))
        return _presentar(await cur.fetchall(), hoy)


def _como_pendiente(item):
    """Forma histórica de la bandeja de pendientes del tutor, ahora basada en obligaciones."""
    return {
        "matricula": item["matricula"], "nombre": item["nombre"],
        "nomenclatura": item["nomenclatura"], "empresa": item["empresa"],
        "ultima_semana": item["ordinal"] - 1, "semana_esperada": item["ordinal"],
        "cuatrimestre": item["periodo"], "periodo_label": item["periodo_label"],
        "semana_inicio": item["semana_inicio"], "semana_fin": item["semana_fin"],
        "inicio_efectivo": item["inicio_efectivo"], "fin_efectivo": item["fin_efectivo"],
        "parcial": item["parcial"],
        "status": OVERDUE if item["estado"] == calendar.ATRASADA else PENDING,
    }


async def alumnos_atrasados(user, *, runtime, hoy=None):
    hoy = hoy or calendar.hoy()
    async with runtime.database.transaction() as cur:
        await sincronizar(cur, hoy)
        await cur.execute("dual.obligaciones.open")
        return [_como_pendiente(i) for i in _presentar(await cur.fetchall(), hoy)]


async def alumnos_sin_reporte(periodo, semana, user, *, runtime, hoy=None):
    if semana < 1:
        raise ApplicationError(status_code=400, detail="La semana debe ser 1 o mayor")
    hoy = hoy or calendar.hoy()
    async with runtime.database.transaction() as cur:
        await sincronizar(cur, hoy)
        await cur.execute("dual.obligaciones.missing_in_period", (periodo, semana))
        return [_como_pendiente(i) for i in _presentar(await cur.fetchall(), hoy)]
