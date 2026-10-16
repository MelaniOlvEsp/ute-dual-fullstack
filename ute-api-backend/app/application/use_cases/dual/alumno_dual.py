from __future__ import annotations

from uuid import UUID
from loguru import logger
from datetime import date
from app.application.dto.reportes import ReporteDualResponse
from app.application.ports.runtime import RuntimePort
from app.application.errors import ApplicationError
from app.application.ports.query import QueryRef
from app.application.responses import FileResult


# Ejecuta las reglas del caso de uso con dependencias inyectadas.
async def subir_reporte(
    semana,
    calificacion_alumno,
    fecha_inicio,
    fecha_fin,
    archivo,
    user,
    *, runtime: RuntimePort,
):
    # Verifica que exista un cuatrimestre dual abierto y obtiene su id
    async with runtime.database.read() as cur:
        await cur.execute(
            'dual.alumno_dual.q000'
        )
        ciclo_abierto = await cur.fetchone()
        if not ciclo_abierto:
            raise ApplicationError(
                status_code=403,
                detail="No hay un cuatrimestre dual activo.",
            )
        cuatrimestre = dict(ciclo_abierto)["cuatrimestre"]

    matricula = user["matricula"]

    async with runtime.database.transaction() as cur:
        # Consultar estatus dual activo
        await cur.execute(
            'dual.alumno_dual.q001',
            (matricula,),
        )
        dual = await cur.fetchone()

        if not dual:
            raise ApplicationError(
                status_code=403,
                detail="No tienes una asignación dual registrada",
            )

        dual = dict(dual)

        if not dual["activo"]:
            raise ApplicationError(
                status_code=403,
                detail="Tu acceso dual fue desactivado."
                "Contacta a tu coordinador dual.",
            )

        if not (1 <= semana <= 18):
            raise ApplicationError(
                status_code=400,
                detail="La semana debe ser entre 1 y 18",
            )

        if not (1.0 <= calificacion_alumno <= 10.0):
            raise ApplicationError(
                status_code=400,
                detail="La calificación debe ser entre 1 y 10",
            )

        # Verificar existencia de reportes previos para el periodo
        await cur.execute(
            'dual.alumno_dual.q002',
            (matricula, cuatrimestre, semana),
        )
        existente = await cur.fetchone()

        if existente:
            existente = dict(existente)
            if existente["estado"] == "Aprobada":
                raise ApplicationError(
                    status_code=409,
                    detail="Este reporte ya fue aprobado",
                )
            if existente["estado"] == "Pendiente":
                raise ApplicationError(
                    status_code=409,
                    detail="Tienes un reporte pendiente. Espera la revisión.",
                )

            # Remover expediente anterior en caso de reenvio por rechazo
            await runtime.services.eliminar_pdf_local(existente.get("archivo_pdf_local"))
            await cur.execute(
                'dual.alumno_dual.q003', (existente["id"],)
            )
            logger.info(
                f"Reporte rechazado semana {semana} "
                f"eliminado para reenvío — {matricula}"
            )

        drive_id = await runtime.services.procesar_y_subir_pdf_reporte(
            archivo, matricula, cuatrimestre, semana
        )

        await cur.execute(
            'dual.alumno_dual.q004',
            (
                matricula,
                cuatrimestre,
                semana,
                calificacion_alumno,
                fecha_inicio,
                fecha_fin,
                drive_id,
            ),
        )
        # Asegurar la correcta insercion del registro en la base de datos
        row_data = await cur.fetchone()
        if not row_data:
            raise ApplicationError(
                status_code=500,
                detail="Error al registrar el reporte",
            )
        reporte_id = row_data["id"]

    logger.info(
        f"Reporte semana {semana} subido por {matricula} — "
        f"cuatrimestre {cuatrimestre}"
    )
    return {
        "mensaje": "Reporte subido correctamente",
        "reporte_id": reporte_id,
    }


# Ejecuta las reglas del caso de uso con dependencias inyectadas.
async def mis_reportes(cuatrimestre, user, *, runtime: RuntimePort):
    async with runtime.database.read() as cur:
        if cuatrimestre:
            await cur.execute(
                'dual.alumno_dual.q005',
                (user["matricula"], cuatrimestre),
            )
        else:
            await cur.execute(
                'dual.alumno_dual.q006',
                (user["matricula"],),
            )
        rows = await cur.fetchall()
        return [dict(r) for r in rows]


# Ejecuta las reglas del caso de uso con dependencias inyectadas.
async def obtener_semana_actual(user, *, runtime: RuntimePort):
    matricula = user["matricula"]
    async with runtime.database.read() as cur:
        # Obtener el cuatrimestre del ciclo activo (o el más reciente)
        await cur.execute('dual.alumno_dual.q007')
        ciclo = await cur.fetchone()

        if not ciclo:
            # Fallback: último ciclo cerrado
            await cur.execute('dual.alumno_dual.q008')
            ciclo = await cur.fetchone()

        if not ciclo:
            # Sin ciclos duales: usar cuatrimestre del grupo
            await cur.execute(
                'dual.alumno_dual.q009',
                (matricula,),
            )
            row = await cur.fetchone()
            if not row:
                raise ApplicationError(
                    status_code=404,
                    detail="Alumno sin grupo asignado",
                )
            cuatrimestre = dict(row)["cuatrimestre"]
            cuatrimestre_cerrado = False
        else:
            ciclo = dict(ciclo)
            cuatrimestre = ciclo["cuatrimestre"]
            cuatrimestre_cerrado = ciclo["cerrado"]

        await cur.execute(
            'dual.alumno_dual.q010',
            (matricula, cuatrimestre),
        )
        ultimo = await cur.fetchone()

        if not ultimo:
            bloqueado = cuatrimestre_cerrado or False
            return {
                "semana_disponible": 1,
                "bloqueado": bloqueado,
                "cuatrimestre_cerrado": cuatrimestre_cerrado,
            }

        ultimo = dict(ultimo)
        if ultimo["estado"] in ("Pendiente", "Rechazada"):
            return {
                "semana_disponible": ultimo["semana"],
                "bloqueado": ultimo["estado"] == "Pendiente"
                or cuatrimestre_cerrado,
                "estado_actual": ultimo["estado"],
                "nota_agente": ultimo.get("nota_agente"),
                "cuatrimestre_cerrado": cuatrimestre_cerrado,
            }

        # Si fue aprobada, le toca la siguiente
        siguiente = ultimo["semana"] + 1
        return {
            "semana_disponible": siguiente if siguiente <= 18 else 18,
            "bloqueado": siguiente > 18 or cuatrimestre_cerrado,
            "estado_actual": "Completado" if siguiente > 18 else None,
            "cuatrimestre_cerrado": cuatrimestre_cerrado,
        }


# Ejecuta las reglas del caso de uso con dependencias inyectadas.
async def descargar_reporte_pdf_alumno(
    reporte_id,
    user,
    *, runtime: RuntimePort,
):
    matricula = user["matricula"]

    async with runtime.database.read() as cur:
        await cur.execute(
            'dual.alumno_dual.q011',
            (reporte_id,),
        )
        row = await cur.fetchone()
        if not row:
            raise ApplicationError(
                status_code=404,
                detail="Reporte no encontrado",
            )
        reporte = dict(row)
        if reporte["matricula"] != matricula:
            raise ApplicationError(
                status_code=404,
                detail="Reporte no encontrado",
            )

    pdf_bytes = await runtime.services.obtener_pdf_bytes(reporte)

    return FileResult(
        iter([pdf_bytes]),
        media_type="application/pdf",
        headers={"Content-Disposition": "inline"},
    )
