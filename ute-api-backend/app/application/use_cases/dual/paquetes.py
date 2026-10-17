from __future__ import annotations

import asyncio
import os
from contextlib import suppress
from decimal import Decimal
from pathlib import Path

from app.application.errors import ApplicationError
from app.application.responses import FileResult
from app.domain import archive, calendar, grading
from app.application.use_cases.dual.expediente import validar_texto
from app.domain.organization import CAREER_BY_CODE

_BLOQUE = 64 * 1024
_ENCABEZADOS_CSV = ["matricula", "nombre", "carrera", "grupo", "periodo", "aprobados", "suma", "promedio",
                    "evaluacion"]


def _flujo(ruta: Path):
    """Entrega el ZIP por bloques y elimina el temporal al terminar o al cerrarse el flujo."""
    try:
        with open(ruta, "rb") as origen:
            while True:
                bloque = origen.read(_BLOQUE)
                if not bloque:
                    break
                yield bloque
    finally:
        with suppress(OSError):
            os.unlink(ruta)


async def _periodo_finalizado(cur, periodo_id):
    await cur.execute("dual.cierres.periodo", (periodo_id,))
    fila = await cur.fetchone()
    if not fila:
        raise ApplicationError(status_code=404, detail="Período no encontrado")
    periodo = dict(fila)
    if periodo["evaluacion_finalizada_en"] is None:
        raise ApplicationError(
            status_code=409,
            detail="El paquete se genera cuando la evaluación del período está finalizada.")
    return periodo


async def _alumno_en_periodo(cur, matricula, periodo_id):
    validar_texto(matricula, campo="La matrícula")
    await cur.execute("dual.expediente.alumno", (matricula,))
    alumno = await cur.fetchone()
    if not alumno:
        raise ApplicationError(status_code=404, detail="Alumno no encontrado")
    await cur.execute("dual.expediente.periodos", (matricula,))
    if str(periodo_id) not in {str(dict(f)["id"]) for f in await cur.fetchall()}:
        raise ApplicationError(status_code=404, detail="El alumno no tiene semanas en este período.")
    await cur.execute("dual.expediente.grupo", (periodo_id, matricula))
    grupo = dict(await cur.fetchone() or {})
    return {"matricula": matricula, "nombre": dict(alumno)["nombre"], "nomenclatura": grupo.get("nomenclatura"),
            "carrera": grupo.get("carrera"), "carrera_codigo": grupo.get("carrera_codigo")}


async def _plan(cur, periodo, alumnos):
    """Arma las entradas del ZIP, el manifiesto y el resumen CSV desde el expediente de cada alumno."""
    await cur.execute("dual.cierres.resultados", (periodo["id"],))
    congelados = {r["matricula"]: dict(r) for r in await cur.fetchall()}
    etiqueta_periodo = periodo["periodo_label"] or periodo["cuatrimestre"]
    entradas, filas_manifiesto, filas_csv = [], [], []
    for alumno in alumnos:
        await cur.execute("dual.paquetes.documentos", (alumno["matricula"], periodo["id"]))
        reportes = []
        for r in (dict(f) for f in await cur.fetchall()):
            if r.get("original_archivado") or r.get("firmado_archivado"):
                raise ApplicationError(
                    status_code=409,
                    detail="Los archivos de este período ya se depuraron; el paquete ya no puede generarse.")
            archivos = []
            for tipo in ("firmado", "original"):
                clave = r[f"{tipo}_clave"]
                if not clave:
                    continue
                ruta = archive.ruta_documento_en_paquete(
                    alumno["carrera_codigo"] or alumno["carrera"], etiqueta_periodo, alumno["nomenclatura"],
                    alumno["matricula"], r["ordinal"], r["version"], tipo)
                archivos.append({"tipo": tipo, "ruta": ruta, "sha256": r[f"{tipo}_sha"],
                                 "tamano": r[f"{tipo}_tamano"]})
                entradas.append({"ruta": ruta, "clave": clave, "sha256": r[f"{tipo}_sha"],
                                 "tamano": r[f"{tipo}_tamano"],
                                 "etiqueta": f"de la semana {r['ordinal']} del alumno {alumno['matricula']}"})
            reportes.append({"reporte_id": r["reporte_id"], "semana": r["ordinal"],
                             "semana_inicio": r["semana_inicio"], "semana_fin": r["semana_fin"],
                             "version": r["version"], "fecha_inicio": r["fecha_inicio"],
                             "fecha_fin": r["fecha_fin"], "nota": r["nota"], "archivos": archivos})
        base = congelados.get(alumno["matricula"], {"suma": 0, "cantidad": 0, "promedio": None})
        promedio = None if base["promedio"] is None else f"{Decimal(base['promedio']):.2f}"
        filas_manifiesto.append({
            "matricula": alumno["matricula"], "nombre": alumno["nombre"], "carrera": alumno["carrera"],
            "grupo": alumno["nomenclatura"], "aprobados": base["cantidad"], "suma": base["suma"],
            "promedio": promedio, "promedio_texto": grading.mostrar(base["promedio"]), "reportes": reportes})
        filas_csv.append([alumno["matricula"], alumno["nombre"], alumno["carrera"], alumno["nomenclatura"],
                          etiqueta_periodo, base["cantidad"], base["suma"],
                          promedio if promedio is not None else grading.SIN_CALIFICACION, "final"])
    return entradas, filas_manifiesto, filas_csv


async def _generar(runtime, periodo, alumnos, alcance, rol, user, matricula=None, carrera=None):
    servicios = runtime.services
    async with runtime.database.read() as cur:
        entradas, filas_manifiesto, filas_csv = await _plan(cur, periodo, alumnos)
    manifiesto = archive.manifiesto_bytes({
        "version": 1, "generado_en": calendar.ahora(), "alcance": alcance,
        "periodo": {"id": periodo["id"], "etiqueta": periodo["periodo_label"] or periodo["cuatrimestre"],
                    "fecha_inicio": periodo["fecha_inicio"], "fecha_fin": periodo["fecha_fin"],
                    "cierre_efectivo": calendar.fecha_de_cierre(periodo["cerrado_at"]),
                    "evaluacion_finalizada_en": periodo["evaluacion_finalizada_en"]},
        "alumnos": filas_manifiesto})
    resumen_csv = archive.construir_csv(_ENCABEZADOS_CSV, filas_csv)
    destino = servicios.nuevo_paquete_temporal()
    try:
        estadisticas = await asyncio.to_thread(servicios.construir_paquete, entradas, manifiesto, resumen_csv, destino)
        async with runtime.database.transaction() as cur:
            await cur.execute("dual.paquetes.registrar", (
                alcance, periodo["id"], matricula, carrera, rol, user["id"], archive.sha256_hex(manifiesto),
                len(alumnos), estadisticas["archivos"], estadisticas["bytes"]))
    except BaseException:
        with suppress(OSError):
            os.unlink(destino)
        raise
    return destino, estadisticas


def _nombre(prefijo, sujeto, periodo) -> str:
    return (f"{prefijo}-{archive.nombre_seguro(sujeto)}-"
            f"{archive.nombre_seguro(periodo['periodo_label'] or periodo['cuatrimestre'])}.zip")


def _respuesta(destino, estadisticas, nombre) -> FileResult:
    return FileResult(
        _flujo(destino), media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{nombre}"',
                 "Content-Length": str(estadisticas["tamano_zip"])})


async def paquete_de_alumno(matricula, periodo_id, user, *, runtime):
    """El tutor genera el paquete de un alumno con el período finalizado (DP-14)."""
    async with runtime.database.read() as cur:
        periodo = await _periodo_finalizado(cur, periodo_id)
        alumno = await _alumno_en_periodo(cur, matricula, periodo_id)
    destino, estadisticas = await _generar(
        runtime, periodo, [alumno], "alumno", "tutor", user, matricula=matricula)
    return _respuesta(destino, estadisticas, _nombre("paquete", matricula, periodo))


async def paquete_de_carrera(codigo, periodo_id, user, *, runtime):
    """El tutor genera el paquete de una carrera y un período finalizado (DP-14)."""
    codigo = (codigo or "").upper()
    if codigo not in CAREER_BY_CODE:
        raise ApplicationError(status_code=404, detail="Carrera no encontrada")
    async with runtime.database.read() as cur:
        periodo = await _periodo_finalizado(cur, periodo_id)
        await cur.execute("dual.paquetes.alumnos_carrera", (periodo_id, codigo))
        alumnos = [dict(f) for f in await cur.fetchall()]
    if not alumnos:
        raise ApplicationError(status_code=404, detail="No hay alumnos de esa carrera con semanas en este período.")
    destino, estadisticas = await _generar(
        runtime, periodo, alumnos, "carrera", "tutor", user, carrera=codigo)
    return _respuesta(destino, estadisticas, _nombre("paquete", codigo, periodo))


async def paquete_propio(periodo_id, user, *, runtime, ahora=None):
    """El alumno descarga solo su paquete, durante la semana posterior a la finalización (DP-14)."""
    matricula = user["matricula"]
    async with runtime.database.read() as cur:
        periodo = await _periodo_finalizado(cur, periodo_id)
        alumno = await _alumno_en_periodo(cur, matricula, periodo_id)
    ventana = archive.ventana_alumno(periodo["evaluacion_finalizada_en"], ahora)
    if not ventana["disponible"]:
        raise ApplicationError(status_code=403, detail=ventana["motivo"])
    destino, estadisticas = await _generar(
        runtime, periodo, [alumno], "alumno", "alumno", user, matricula=matricula)
    return _respuesta(destino, estadisticas, _nombre("mi-paquete", matricula, periodo))
