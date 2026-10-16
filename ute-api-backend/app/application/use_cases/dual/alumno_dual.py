from __future__ import annotations

from app.application.ports.runtime import RuntimePort
from app.application.errors import ApplicationError
from app.application.responses import FileResult


# C05: la entrega y el reenvío viven en entregas.py (por obligación, con versiones).
# Aquí quedan la consulta de reportes propios y la descarga de la versión vigente.

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
