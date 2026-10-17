from __future__ import annotations

from decimal import Decimal

from app.application.errors import ApplicationError
from app.application.use_cases.dual.archivado import exigir_vigente
from app.application.responses import FileResult
from app.domain import archive, calendar, grading

SITUACIONES = ("todos", "activos", "baja")
LIMITE_MAXIMO = 200


DESPLAZAMIENTO_MAXIMO = 10_000_000


def validar_texto(*valores, campo: str = "El texto") -> None:
    """PostgreSQL no admite NUL en campos de texto: se rechaza con 422 en vez de fallar con 500."""
    if any(v is not None and "\x00" in v for v in valores):
        raise ApplicationError(status_code=422, detail=f"{campo} contiene caracteres no válidos.")


def _escapar_like(texto: str) -> str:
    return texto.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def presentar_periodo(fila: dict) -> dict:
    """Recepción y evaluación del período, aparte de las fechas calendario (RN-23, RN-24)."""
    recepcion = "cerrada" if fila["cerrado"] else "abierta" if fila["abierto"] else "sin_abrir"
    return {
        "id": fila["id"], "cuatrimestre": fila["cuatrimestre"],
        "periodo_label": fila["periodo_label"] or fila["cuatrimestre"],
        "fecha_inicio": fila["fecha_inicio"], "fecha_fin": fila["fecha_fin"],
        "recepcion": recepcion,
        "evaluacion": "finalizada" if fila["evaluacion_finalizada_en"] else "en_curso",
        "cierre_efectivo": calendar.fecha_de_cierre(fila["cerrado_at"]),
        "finalizada_en": fila["evaluacion_finalizada_en"],
    }


def _resumen(periodo: dict, aprobados: list[dict], congelado: dict | None) -> dict:
    """Final desde el registro congelado de C07; provisional con la misma función de cálculo."""
    if periodo["evaluacion"] == "finalizada":
        base = congelado or {"suma": 0, "cantidad": 0, "promedio": None}
        suma, cantidad, promedio = base["suma"], base["cantidad"], base["promedio"]
    else:
        calculo = grading.calcular(a["nota"] for a in aprobados)
        suma, cantidad, promedio = calculo.suma, calculo.cantidad, calculo.promedio
    return {
        "aprobados": cantidad, "suma": suma,
        "promedio": None if promedio is None else f"{Decimal(promedio):.2f}",
        "promedio_texto": grading.mostrar(promedio),
        "definitivo": periodo["evaluacion"] == "finalizada",
    }


async def expediente(matricula, user, *, runtime, propio=False, ahora=None):
    """Expediente por período: grupo histórico, aprobados con su nota validada y promedio (RN-25).

    Una consulta del alumno solo llega aquí con su propia matrícula (la ruta la toma de la sesión), de
    modo que un identificador ajeno no puede pedirse. El personal consulta cualquier alumno, incluidos
    los dados de baja (RN-29, MP-10).
    """
    ahora = ahora or calendar.ahora()
    validar_texto(matricula, campo="La matrícula")
    async with runtime.database.read() as cur:
        await cur.execute("dual.expediente.alumno", (matricula,))
        alumno = await cur.fetchone()
        if not alumno:
            raise ApplicationError(status_code=404, detail="Alumno no encontrado")
        await cur.execute("dual.expediente.periodos", (matricula,))
        filas = [dict(f) for f in await cur.fetchall()]
        periodos = []
        for fila in filas:
            periodo = presentar_periodo(fila)
            await cur.execute("dual.expediente.grupo", (fila["id"], matricula))
            grupo = dict(await cur.fetchone() or {})
            await cur.execute("dual.expediente.aprobados", (matricula, fila["id"]))
            aprobados = [_aprobado(dict(a)) for a in await cur.fetchall()]
            await cur.execute("dual.expediente.resultado", (fila["id"], matricula))
            congelado = await cur.fetchone()
            await cur.execute("dual.purgas.estado_alumno", (matricula, fila["id"], matricula, fila["id"]))
            archivo = _archivo([dict(f) for f in await cur.fetchall()], periodo, matricula, propio)
            periodos.append({
                "periodo": periodo,
                "grupo": {"nomenclatura": grupo.get("nomenclatura"), "carrera": grupo.get("carrera"),
                          "grado": grupo.get("grado"), "carrera_codigo": grupo.get("carrera_codigo")},
                "aprobados": aprobados,
                "resumen": _resumen(periodo, aprobados, dict(congelado) if congelado else None),
                "paquete": _paquete(periodo, fila, propio, ahora, archivo),
                "archivo": archivo,
            })
    return {"alumno": dict(alumno), "periodos": periodos}


def _aprobado(fila: dict) -> dict:
    return {
        "reporte_id": fila["reporte_id"], "semana": fila["ordinal"], "semana_inicio": fila["semana_inicio"],
        "semana_fin": fila["semana_fin"], "version": fila["version"],
        "fecha_inicio": fila["fecha_inicio"], "fecha_fin": fila["fecha_fin"], "nota": fila["nota"],
        "declarada_nota": fila["declarada_nota"], "observacion": fila["observacion"],
        "firmado": fila["firmado"], "paginas": fila["paginas"], "archivado_en": _civil(fila.get("archivado_en")),
        "corregida": (fila["nota"], fila["fecha_inicio"], fila["fecha_fin"]) != (
            fila["declarada_nota"], fila["declarada_inicio"], fila["declarada_fin"]),
    }


def _civil(instante):
    return calendar.fecha_de_cierre(instante) if instante else None


def _archivo(purgas: list[dict], periodo: dict, matricula: str, propio: bool) -> dict:
    """Estado de los archivos del alumno en el período (C08B): normal, programada (con la fecha de
    eliminación) o archivado. Las notas, el promedio y el historial no dependen de este estado."""
    programada = next((p for p in purgas if p["estado"] == "programada"), None)
    completada = next((p for p in purgas if p["estado"] == "completada"), None)
    estado = "programada" if programada else "archivado" if completada else "normal"
    archivo = {
        "estado": estado,
        # Fechas civiles en America/Mexico_City (como `cierre_efectivo`): el cliente las muestra sin convertir.
        "eliminacion_en": _civil(programada["ejecutar_en"]) if programada else None,
        "archivado_en": _civil(completada["completada_en"]) if completada and not programada else None,
        "frase_esperada": f"DEPURAR {periodo['periodo_label']} {matricula}",
    }
    if not propio:
        archivo["purga_id"] = programada["purga_id"] if programada else None
    return archivo


def _paquete(periodo: dict, fila: dict, propio: bool, ahora, archivo: dict | None = None) -> dict:
    """Disponibilidad del paquete de archivo: del alumno (ventana de una semana) o del tutor."""
    if archivo and archivo["estado"] == "archivado":
        fecha = archivo["archivado_en"].isoformat() if archivo["archivado_en"] else ""
        return {"disponible": False, "hasta": None,
                "motivo": f"Los archivos de este período se depuraron el {fecha}; "
                          "las notas, el promedio y el historial se conservan."}
    if propio:
        return archive.ventana_alumno(fila["evaluacion_finalizada_en"], ahora)
    if periodo["evaluacion"] != "finalizada":
        return {"disponible": False, "hasta": None,
                "motivo": "El paquete se genera cuando la evaluación del período está finalizada."}
    return {"disponible": True, "hasta": None, "motivo": None}


async def descargar_aprobado(reporte_id, numero, documento, user, *, runtime):
    """Original o firmado de una versión aprobada, para el personal (MP-10). Lee el documento versionado
    por identificador; una versión que no está aprobada no se entrega y responde 404."""
    async with runtime.database.read() as cur:
        await cur.execute("dual.expediente.documentos_aprobados", (numero, reporte_id))
        fila = await cur.fetchone()
    if not fila:
        raise ApplicationError(status_code=404, detail="Reporte aprobado no encontrado")
    datos = dict(fila)
    exigir_vigente(datos, documento)
    clave = datos["firmado" if documento == "firmado" else "original"]
    if not clave:
        raise ApplicationError(status_code=404, detail="Esta versión no tiene documento firmado")
    contenido = await runtime.services.leer_documento(clave, datos.get("firmado_sha" if documento == "firmado" else "original_sha"))
    sufijo = "-firmado" if documento == "firmado" else ""
    return FileResult(
        iter([contenido]), media_type="application/pdf",
        headers={"Content-Disposition":
                 f'inline; filename="{archive.nombre_seguro(datos["matricula"])}-v{int(numero)}{sufijo}.pdf"'})


async def directorio(cuatrimestre, grupo, busqueda, situacion, limite, desplazamiento, user, *, runtime):
    """Directorio del personal paginado por servidor; incluye a los dados de baja con su indicador."""
    if situacion not in SITUACIONES:
        raise ApplicationError(status_code=422, detail="La situación debe ser todos, activos o baja.")
    if not 1 <= limite <= LIMITE_MAXIMO or not 0 <= desplazamiento <= DESPLAZAMIENTO_MAXIMO:
        raise ApplicationError(
            status_code=422,
            detail=f"El límite debe estar entre 1 y {LIMITE_MAXIMO} y el desplazamiento entre 0 y {DESPLAZAMIENTO_MAXIMO}.")
    validar_texto(cuatrimestre, grupo, busqueda, campo="El filtro")
    texto = _escapar_like(busqueda.strip()) if busqueda and busqueda.strip() else None
    parametros = (cuatrimestre, cuatrimestre, cuatrimestre, cuatrimestre, cuatrimestre, cuatrimestre,
                  grupo, grupo, texto, texto, texto, situacion, situacion, situacion, limite, desplazamiento)
    async with runtime.database.read() as cur:
        await cur.execute("dual.expediente.directorio", parametros)
        filas = [dict(f) for f in await cur.fetchall()]
    total = filas[0]["total"] if filas else 0
    for fila in filas:
        fila.pop("total", None)
    return {"items": filas, "total": total, "limite": limite, "desplazamiento": desplazamiento}
