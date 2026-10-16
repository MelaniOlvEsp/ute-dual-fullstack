from __future__ import annotations

from datetime import date
from uuid import UUID
from loguru import logger
from app.application.dto.reportes import ReporteDualUpdateAgente, EmpresaCreate, EmpresaOut, AsignacionCreate, AsignacionOut, CuatrimestreCerrar, CuatrimestreAbrir, CuatrimestreActualOut
from app.application.ports.runtime import RuntimePort
from app.application.errors import ApplicationError
from app.application.ports.query import QueryRef
from app.application.responses import FileResult
from app.application.use_cases.dual import obligaciones
from app.domain import calendar


# Ejecuta las reglas del caso de uso con dependencias inyectadas.
async def listar_reportes(
    estado,
    cuatrimestre,
    user,
    *, runtime: RuntimePort,
):
    async with runtime.database.read() as cur:
        condiciones = []
        params = []

        if estado:
            condiciones.append("r.estado = %s")
            params.append(estado)
        if cuatrimestre:
            condiciones.append("r.cuatrimestre = %s")
            params.append(cuatrimestre)

        where = f"WHERE {' AND '.join(condiciones)}" if condiciones else ""

        await cur.execute(
            QueryRef('dual.coordinador_dual.q000', where=where),
            params,
        )
        rows = await cur.fetchall()
        return [dict(r) for r in rows]


# Ejecuta las reglas del caso de uso con dependencias inyectadas.
async def revisar_reporte(reporte_id, data, user, *, runtime: RuntimePort):
    # Solo el tutor puede revisar y firmar reportes semanales.
    drive_id = None
    old_local = None
    async with runtime.database.transaction() as cur:
        await cur.execute('dual.coordinador_dual.q001', (reporte_id,))
        row = await cur.fetchone()
        if not row:
            raise ApplicationError(404, 'Reporte no encontrado')
        report = dict(row)
        assignments = [
            'estado = %s', 'nota_agente = %s', 'updated_at = NOW()',
            'revisado_por = %s', 'revisado_en = NOW()',
        ]
        values = [data.estado, data.nota_agente, user['id']]
        if data.calificacion_alumno is not None:
            assignments.append('calificacion_alumno = %s')
            values.append(data.calificacion_alumno)
        if data.fecha_inicio is not None:
            assignments.append('fecha_inicio = %s')
            values.append(data.fecha_inicio)
        if data.fecha_fin is not None:
            assignments.append('fecha_fin = %s')
            values.append(data.fecha_fin)
        if data.estado == 'Aprobada':
            if report['estado'] == 'Aprobada':
                raise ApplicationError(409, 'El reporte ya fue aprobado')
            await cur.execute('dual.tutor.get_signature', (user['id'],))
            signature = await cur.fetchone()
            if not signature:
                raise ApplicationError(409, 'Primero adjunta tu firma académica')
            await cur.execute('dual.tutor.identity', (user['id'],))
            identity = await cur.fetchone()
            tutor_name = (dict(identity).get('nombre') if identity else None)
            pdf = await runtime.services.obtener_pdf_bytes(report)
            signed_pdf = runtime.services.sign_pdf(
                pdf, bytes(signature['imagen']), tutor_name or user['sub']
            )
            filename = (f"{report['matricula']}-S{report['semana']}-"
                        f"{report['cuatrimestre']}-firmado.pdf")
            drive_id = await runtime.services.upload_file_async(
                signed_pdf, filename, 'application/pdf',
                runtime.settings.drive_folder_dual,
            )
            assignments.extend(['archivo_pdf_url = %s',
                                'archivo_pdf_local = NULL'])
            values.append(drive_id)
            old_local = report.get('archivo_pdf_local')
        values.append(reporte_id)
        await cur.execute(
            QueryRef('dual.coordinador_dual.update_report',
                     assignments=tuple(assignments)), tuple(values)
        )
    if old_local:
        await runtime.services.eliminar_pdf_local(old_local)
    return {'mensaje': f'Reporte actualizado a {data.estado}'}


# Ejecuta las reglas del caso de uso con dependencias inyectadas.
async def listar_empresas(user, *, runtime: RuntimePort):
    async with runtime.database.read() as cur:
        await cur.execute(
            'dual.coordinador_dual.q002'
        )
        rows = await cur.fetchall()
        return [dict(r) for r in rows]


# Ejecuta las reglas del caso de uso con dependencias inyectadas.
async def crear_empresa(data, user, *, runtime: RuntimePort):
    async with runtime.database.transaction() as cur:
        await cur.execute(
            'dual.coordinador_dual.q003', (data.nombre,)
        )
        if await cur.fetchone():
            raise ApplicationError(
                status_code=409,
                detail="Ya existe una empresa con ese nombre",
            )

        await cur.execute(
            'dual.coordinador_dual.q004',
            (data.nombre,),
        )
        row = await cur.fetchone()
        if not row:
            raise ApplicationError(
                status_code=500,
                detail="Error al crear empresa",
            )
        return dict(row)


# Ejecuta las reglas del caso de uso con dependencias inyectadas.
async def listar_asignaciones(cuatrimestre, user, *, runtime: RuntimePort):
    async with runtime.database.read() as cur:
        if cuatrimestre:
            await cur.execute(
                'dual.coordinador_dual.q005',
                (cuatrimestre,),
            )
        else:
            await cur.execute('dual.coordinador_dual.q006')
        rows = await cur.fetchall()
        return [dict(r) for r in rows]


# Ejecuta las reglas del caso de uso con dependencias inyectadas.
async def asignar_alumno_empresa(data, user, *, runtime: RuntimePort):
    async with runtime.database.transaction() as cur:
        # La incorporación no depende del grado ni del período: solo exige alumno con grupo.
        await cur.execute(
            'dual.coordinador_dual.q007',
            (data.matricula,),
        )
        if not await cur.fetchone():
            raise ApplicationError(
                status_code=404,
                detail="Alumno no encontrado o sin grupo asignado",
            )

        # Verificar que la empresa exista
        await cur.execute(
            'dual.coordinador_dual.q008', (data.empresa_id,)
        )
        if not await cur.fetchone():
            raise ApplicationError(
                status_code=404,
                detail="Empresa no encontrada",
            )

        await cur.execute(
            'dual.coordinador_dual.active_incorporation', (data.matricula,)
        )
        active = await cur.fetchone()
        if active:
            active = dict(active)
            if str(active["empresa_id"]) == str(data.empresa_id):
                return active
            raise ApplicationError(
                status_code=409,
                detail="El alumno ya tiene una incorporación activa. Registra su baja antes de cambiar de empresa.",
            )

        await cur.execute(
            'dual.coordinador_dual.insert_incorporation',
            (data.matricula, data.empresa_id, data.fecha_inicio, user["id"]),
        )
        row = await cur.fetchone()
        if not row:
            raise ApplicationError(
                status_code=500,
                detail="Error al asignar empresa",
            )
        await obligaciones.generar(cur, dict(row), calendar.hoy())

    logger.info(
        f"Alumno {data.matricula} asignado a empresa {data.empresa_id} "
        f"desde {data.fecha_inicio} por {user['sub']}"
    )
    return dict(row)


# Ejecuta las reglas del caso de uso con dependencias inyectadas.
async def buscar_alumno(matricula, user, *, runtime: RuntimePort):
    async with runtime.database.read() as cur:
        await cur.execute(
            'dual.coordinador_dual.q010',
            (matricula,),
        )
        row = await cur.fetchone()
        if not row:
            raise ApplicationError(
                status_code=404,
                detail="Alumno no encontrado",
            )
        return dict(row)


# Ejecuta las reglas del caso de uso con dependencias inyectadas.
async def actualizar_alumno_dual(
    matricula,
    body,
    user,
    *, runtime: RuntimePort,
):
    es_dual = body.alumno_dual
    empresa_id = body.empresa_id

    async with runtime.database.transaction() as cur:
        await cur.execute(
            'dual.coordinador_dual.q011',
            (matricula,),
        )
        if not await cur.fetchone():
            raise ApplicationError(
                status_code=404,
                detail="Alumno no encontrado",
            )

        if es_dual:
            # Verificar empresa
            await cur.execute(
                'dual.coordinador_dual.q012', (empresa_id,)
            )
            if not await cur.fetchone():
                raise ApplicationError(
                    status_code=404,
                    detail="Empresa no encontrada",
                )

            await cur.execute(
                'dual.coordinador_dual.active_incorporation', (matricula,)
            )
            active = await cur.fetchone()
            if active:
                active = dict(active)
                if str(active["empresa_id"]) == str(empresa_id):
                    return {"mensaje": "La incorporación ya estaba activa"}
                raise ApplicationError(
                    status_code=409,
                    detail="Registra la baja vigente antes de cambiar de empresa.",
                )
            await cur.execute(
                'dual.coordinador_dual.insert_incorporation',
                (matricula, empresa_id, body.fecha_inicio, user["id"]),
            )
            creada = await cur.fetchone()
            await obligaciones.generar(cur, dict(creada), calendar.hoy())
        else:
            await cur.execute(
                'dual.coordinador_dual.close_incorporation',
                (body.fecha_baja, user["id"], matricula, body.fecha_baja),
            )
            cerrada = await cur.fetchone()
            if not cerrada:
                raise ApplicationError(
                    status_code=409,
                    detail="No existe una incorporación activa o la baja es anterior al inicio.",
                )
            # La baja es inclusiva: recorta su semana y no deja obligaciones posteriores.
            await obligaciones.generar(cur, dict(cerrada), calendar.hoy())

    logger.info(
        f"Alumno {matricula} → alumno_dual={es_dual} por {user['sub']}"
    )
    return {"mensaje": "Alumno actualizado correctamente"}


async def historial_incorporaciones(matricula, user, *, runtime: RuntimePort):
    async with runtime.database.read() as cur:
        await cur.execute('dual.coordinador_dual.q011', (matricula,))
        if not await cur.fetchone():
            raise ApplicationError(status_code=404, detail="Alumno no encontrado")
        await cur.execute('dual.coordinador_dual.incorporation_history', (matricula,))
        return [dict(row) for row in await cur.fetchall()]


# Pendientes basados en obligaciones semanales (C04); ver use_cases/dual/obligaciones.py.
async def alumnos_sin_reporte(
    cuatrimestre,
    semana,
    user,
    *, runtime: RuntimePort,
):
    return await obligaciones.alumnos_sin_reporte(
        cuatrimestre, semana, user, runtime=runtime)


async def alumnos_atrasados(user, *, runtime: RuntimePort):
    return await obligaciones.alumnos_atrasados(user, runtime=runtime)

# Ejecuta las reglas del caso de uso con dependencias inyectadas.
async def cuatrimestre_actual(user, *, runtime: RuntimePort):
    async with runtime.database.read() as cur:
        await cur.execute('dual.coordinador_dual.q018')
        row = await cur.fetchone()
        if row:
            return dict(row)

        # Fallback: último cerrado
        await cur.execute('dual.coordinador_dual.q019')
        row = await cur.fetchone()
        if row:
            return dict(row)

        return {
            "cuatrimestre": None,
            "periodo_label": None,
            "fecha_inicio": None,
            "fecha_fin": None,
            "abierto": False,
            "cerrado": False,
            "cerrado_at": None,
        }


# Ejecuta las reglas del caso de uso con dependencias inyectadas.
async def abrir_cuatrimestre(data, user, *, runtime: RuntimePort):
    async with runtime.database.transaction() as cur:
        # Serializa la apertura para que dos solicitudes no creen períodos solapados.
        await cur.execute('dual.obligaciones.period_lock')
        # Bloquear si ya hay uno abierto
        await cur.execute(
            'dual.coordinador_dual.q020'
        )
        activo = await cur.fetchone()
        if activo:
            a = dict(activo)
            raise ApplicationError(
                status_code=409,
                detail=f"Ya hay un cuatrimestre activo: {a['periodo_label']} "
                f"({a['cuatrimestre']}). "
                f"Ciérralo antes de abrir uno nuevo.",
            )

        cuatrimestre = f"{data.periodo_label}"

        # DP-04: períodos manuales, con fechas explícitas y sin solapamiento.
        await cur.execute(
            'dual.obligaciones.overlapping_period',
            (cuatrimestre, data.fecha_inicio, data.fecha_fin),
        )
        solapado = await cur.fetchone()
        if solapado:
            s = dict(solapado)
            raise ApplicationError(
                status_code=409,
                detail=f"Las fechas se solapan con {s['periodo_label'] or s['cuatrimestre']} "
                f"({s['fecha_inicio']} a {s['fecha_fin']}). Ajusta las fechas.",
            )

        await cur.execute(
            'dual.coordinador_dual.q021',
            (
                cuatrimestre,
                data.periodo_label,
                data.fecha_inicio,
                data.fecha_fin,
            ),
        )
        row = await cur.fetchone()
        # Semanas ya generadas cuyo domingo cae en este período y aún no tenían período.
        await obligaciones.abrir_periodo_resuelve(
            cur, dict(row)["id"], data.fecha_inicio, data.fecha_fin)

    logger.info(f"Cuatrimestre {data.periodo_label} abierto por {user['sub']}")
    return {
        "mensaje": f"Cuatrimestre {data.periodo_label} abierto correctamente.",
        "cuatrimestre": dict(row),
    }


# Ejecuta las reglas del caso de uso con dependencias inyectadas.
async def cerrar_cuatrimestre(data, user, *, runtime: RuntimePort):
    async with runtime.database.transaction() as cur:
        # Verificar que existe un cuatrimestre abierto
        await cur.execute(
            'dual.coordinador_dual.q022'
        )
        abierto_row = await cur.fetchone()
        if not abierto_row:
            raise ApplicationError(
                status_code=400,
                detail="No hay un cuatrimestre abierto que cerrar.",
            )

        cuatrimestre_target = dict(abierto_row)["cuatrimestre"]

        await cur.execute(
            'dual.coordinador_dual.q023',
            (user["id"], data.periodo_label, cuatrimestre_target),
        )

    logger.info(
        f"Cuatrimestre '{data.periodo_label}' cerrado por {user['sub']}"
    )
    return {
        "mensaje": (
            f"Cuatrimestre '{data.periodo_label}' cerrado correctamente."
        ),
        "cuatrimestre": cuatrimestre_target,
        "periodo_label": data.periodo_label,
    }


# Ejecuta las reglas del caso de uso con dependencias inyectadas.
async def descargar_reporte_pdf_coordinador(
    reporte_id,
    user,
    *, runtime: RuntimePort,
):
    async with runtime.database.read() as cur:
        await cur.execute(
            'dual.coordinador_dual.q024',
            (reporte_id,),
        )
        row = await cur.fetchone()
        if not row:
            raise ApplicationError(
                status_code=404,
                detail="Reporte no encontrado",
            )

    pdf_bytes = await runtime.services.obtener_pdf_bytes(dict(row))

    return FileResult(
        iter([pdf_bytes]),
        media_type="application/pdf",
        headers={"Content-Disposition": "inline"},
    )
