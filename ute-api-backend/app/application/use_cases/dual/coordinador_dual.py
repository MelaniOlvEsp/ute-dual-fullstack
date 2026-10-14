from __future__ import annotations

from datetime import date
from uuid import UUID
from loguru import logger
from app.application.dto.reportes import ReporteDualUpdateAgente, EmpresaCreate, EmpresaOut, AsignacionCreate, AsignacionOut, CuatrimestreCerrar, CuatrimestreAbrir, CuatrimestreActualOut
from app.application.ports.runtime import RuntimePort
from app.application.errors import ApplicationError
from app.application.ports.query import QueryRef
from app.application.responses import FileResult


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
        # Verificar que el alumno exista y obtener su cuatrimestre actual
        await cur.execute(
            'dual.coordinador_dual.q007',
            (data.matricula,),
        )
        alumno = await cur.fetchone()
        if not alumno:
            raise ApplicationError(
                status_code=404,
                detail="Alumno no encontrado o sin grupo asignado",
            )
        cuatrimestre = dict(alumno)["cuatrimestre"]

        # Verificar que la empresa exista
        await cur.execute(
            'dual.coordinador_dual.q008', (data.empresa_id,)
        )
        if not await cur.fetchone():
            raise ApplicationError(
                status_code=404,
                detail="Empresa no encontrada",
            )

        # Upsert de asignacion activa
        await cur.execute(
            'dual.coordinador_dual.q009',
            (data.matricula, cuatrimestre, data.empresa_id),
        )
        row = await cur.fetchone()
        if not row:
            raise ApplicationError(
                status_code=500,
                detail="Error al asignar empresa",
            )

    logger.info(
        f"Alumno {data.matricula} asignado a empresa {data.empresa_id} "
        f"cuatrimestre {cuatrimestre} por {user['sub']}"
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
        # Verificar alumno y obtener cuatrimestre actual
        await cur.execute(
            'dual.coordinador_dual.q011',
            (matricula,),
        )
        alumno = await cur.fetchone()
        if not alumno:
            raise ApplicationError(
                status_code=404,
                detail="Alumno no encontrado",
            )
        cuatrimestre = dict(alumno)["cuatrimestre"]

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

            # Insertar o actualizar asignacion en alumnos_dual
            await cur.execute(
                'dual.coordinador_dual.q013',
                (matricula, cuatrimestre, empresa_id),
            )
        else:
            # Desactivar solo la asignacion del cuatrimestre actual
            await cur.execute(
                'dual.coordinador_dual.q014',
                (matricula, cuatrimestre),
            )

    logger.info(
        f"Alumno {matricula} → alumno_dual={es_dual} por {user['sub']}"
    )
    return {"mensaje": "Alumno actualizado correctamente"}


# Ejecuta las reglas del caso de uso con dependencias inyectadas.
async def alumnos_sin_reporte(
    cuatrimestre,
    semana,
    user,
    *, runtime: RuntimePort,
):
    if not (1 <= semana <= 18):
        raise ApplicationError(
            status_code=400,
            detail="La semana debe ser entre 1 y 18",
        )

    async with runtime.database.read() as cur:
        await cur.execute(
            'dual.coordinador_dual.q015',
            (cuatrimestre, semana),
        )
        rows = await cur.fetchall()
        return [dict(r) for r in rows]


# Ejecuta las reglas del caso de uso con dependencias inyectadas.
async def alumnos_atrasados(user, *, runtime: RuntimePort):
    hoy = date.today()
    weekday = hoy.weekday()  # 0=Monday, 4=Friday, 6=Sunday

    async with runtime.database.read() as cur:
        # Obtener cuatrimestre activo para calcular semana actual global
        await cur.execute('dual.coordinador_dual.q016')
        ciclo = await cur.fetchone()
        if not ciclo:
            return []

        ciclo = dict(ciclo)
        fecha_inicio = ciclo.get("fecha_inicio")
        cuatrimestre = ciclo["cuatrimestre"]

        # Calcular semana actual global desde fecha_inicio
        semana_actual = 1
        if fecha_inicio and isinstance(fecha_inicio, date):
            dias_transcurridos = (hoy - fecha_inicio).days
            semana_actual = min(18, max(1, dias_transcurridos // 7 + 1))

        await cur.execute(
            'dual.coordinador_dual.q017',
            (cuatrimestre,),
        )
        rows = await cur.fetchall()

        resultado = []
        for r in rows:
            r = dict(r)
            semana_esperada = r["semana_esperada"]

            # Solo mostrar semanas actuales o pasadas (no futuras)
            if semana_esperada > semana_actual:
                continue

            # Determinar status: Pending vs Overdue
            if semana_esperada < semana_actual:
                # Semana ya pasó → Overdue
                r["status"] = "Overdue"
            elif semana_esperada == semana_actual:
                if weekday >= 6:
                    r["status"] = "Overdue"
                else:
                    r["status"] = "Pending"
            else:
                r["status"] = "Pending"

            r["semana_actual_global"] = semana_actual
            resultado.append(r)

        return resultado


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
