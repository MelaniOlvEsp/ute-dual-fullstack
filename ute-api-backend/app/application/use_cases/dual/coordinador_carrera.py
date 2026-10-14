from __future__ import annotations

import csv
import io
import zipfile
from loguru import logger
from uuid import UUID
from app.application.dto.reportes import ReporteDualResponse
from app.application.ports.runtime import RuntimePort
from app.application.errors import ApplicationError
from app.application.ports.query import QueryRef
from app.application.responses import FileResult
from app.domain.periods import periodo_actual as _periodo_actual


CAMPOS_CSV = ["semana", "calificacion_alumno"]


# Ejecuta las reglas del caso de uso con dependencias inyectadas.
async def listar_periodos(user, *, runtime: RuntimePort):
    async with runtime.database.read() as cur:
        await cur.execute('dual.coordinador_carrera.q000')
        rows = await cur.fetchall()
        periodos = []
        for r in rows:
            cuatri = r["cuatrimestre"]
            # Buscar periodo_label en ciclos_dual
            await cur.execute(
                'dual.coordinador_carrera.q001',
                (cuatri,),
            )
            ciclo = await cur.fetchone()
            periodos.append(
                {
                    "cuatrimestre": cuatri,
                    "periodo_label": (
                        dict(ciclo)["periodo_label"] if ciclo else cuatri
                    ),
                }
            )
        # También incluir periodos de ciclos_dual sin reportes aún
        await cur.execute('dual.coordinador_carrera.q002')
        ciclos = await cur.fetchall()
        for c in ciclos:
            c = dict(c)
            if not any(
                p["cuatrimestre"] == c["cuatrimestre"] for p in periodos
            ):
                periodos.append(
                    {
                        "cuatrimestre": c["cuatrimestre"],
                        "periodo_label": c["periodo_label"],
                    }
                )
        return periodos


# Ejecuta las reglas del caso de uso con dependencias inyectadas.
async def listar_alumnos(cuatrimestre, grupo, user, *, runtime: RuntimePort):
    async with runtime.database.read() as cur:
        condiciones = ["ad.activo = TRUE"]
        params = [
            cuatrimestre,
            cuatrimestre,
        ]

        if cuatrimestre:
            condiciones.append("g.cuatrimestre::text = %s")
            params.append(cuatrimestre)
        if grupo:
            condiciones.append("g.nomenclatura = %s")
            params.append(grupo)

        where = f"WHERE {' AND '.join(condiciones)}"

        await cur.execute(
            QueryRef('dual.coordinador_carrera.q003', where=where),
            params,
        )
        rows = await cur.fetchall()
        return [dict(r) for r in rows]


# Ejecuta las reglas del caso de uso con dependencias inyectadas.
async def expediente_alumno(
    matricula,
    cuatrimestre,
    user,
    *, runtime: RuntimePort,
):
    async with runtime.database.read() as cur:
        await cur.execute(
            'dual.coordinador_carrera.q004', (matricula,)
        )
        if not await cur.fetchone():
            raise ApplicationError(
                status_code=404,
                detail="Alumno no encontrado",
            )

        # Si no se especifica cuatrimestre, usar el más reciente con reportes
        if not cuatrimestre:
            await cur.execute(
                'dual.coordinador_carrera.q005',
                (matricula,),
            )
            reciente = await cur.fetchone()
            if reciente:
                cuatrimestre = reciente["cuatrimestre"]

        if cuatrimestre:
            await cur.execute(
                'dual.coordinador_carrera.q006',
                (matricula, cuatrimestre),
            )
        else:
            await cur.execute(
                'dual.coordinador_carrera.q007',
                (matricula,),
            )
        rows = await cur.fetchall()
        return [dict(r) for r in rows]


# Ejecuta las reglas del caso de uso con dependencias inyectadas.
async def descargar_reporte_pdf_carrera(
    reporte_id,
    user,
    *, runtime: RuntimePort,
):
    async with runtime.database.read() as cur:
        await cur.execute(
            'dual.coordinador_carrera.q008',
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


# Ejecuta las reglas del caso de uso con dependencias inyectadas.
async def exportar_csv(
    matricula,
    cuatrimestre,
    user,
    *, runtime: RuntimePort,
):
    async with runtime.database.read() as cur:
        await cur.execute(
            'dual.coordinador_carrera.q009',
            (matricula,),
        )
        alumno = await cur.fetchone()
        if not alumno:
            raise ApplicationError(
                status_code=404,
                detail="Alumno no encontrado",
            )
        alumno = dict(alumno)
        nomenclatura = alumno.get("nomenclatura") or "sin-grupo"
        nombre_archivo = f"{matricula}-{nomenclatura}.csv"

        if cuatrimestre:
            await cur.execute(
                'dual.coordinador_carrera.q010',
                (matricula, cuatrimestre),
            )
        else:
            await cur.execute(
                'dual.coordinador_carrera.q011',
                (matricula,),
            )
        rows = await cur.fetchall()

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=CAMPOS_CSV)
    writer.writeheader()
    for r in rows:
        writer.writerow(dict(r))

    output.seek(0)
    return FileResult(
        io.BytesIO(output.getvalue().encode("utf-8")),
        media_type="text/csv",
        headers={
            "Content-Disposition": (f"attachment; filename={nombre_archivo}")
        },
    )


# Ejecuta las reglas del caso de uso con dependencias inyectadas.
async def exportar_zip(
    matricula,
    cuatrimestre,
    user,
    *, runtime: RuntimePort,
):
    async with runtime.database.read() as cur:
        # Validar que el cuatrimestre este cerrado
        await cur.execute(
            'dual.coordinador_carrera.q012',
            (matricula,),
        )
        alumno = await cur.fetchone()
        if not alumno:
            raise ApplicationError(
                status_code=404,
                detail="Alumno no encontrado",
            )
        alumno = dict(alumno)
        cuatrimestre_actual = cuatrimestre or alumno.get("cuatrimestre") or ""

        # Obtener reportes aprobados
        await cur.execute(
            'dual.coordinador_carrera.q013',
            (matricula, cuatrimestre_actual),
        )
        reportes = await cur.fetchall()

        if not reportes:
            raise ApplicationError(
                status_code=404,
                detail="No hay reportes aprobados para exportar",
            )

    # Construir ZIP en memoria: intenta local, si no existe usa Drive
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for r in reportes:
            r = dict(r)
            semana = r["semana"]
            nombre_pdf = f"{matricula}/semana_{semana}.pdf"
            try:
                if r.get("archivo_pdf_local"):
                    pdf_bytes = await runtime.services.leer_pdf_local(r["archivo_pdf_local"])
                elif r.get("archivo_pdf_url"):
                    pdf_bytes = await runtime.services.get_file_bytes_async(
                        r["archivo_pdf_url"]
                    )
                else:
                    raise Exception("Sin referencia de archivo")
                zf.writestr(nombre_pdf, pdf_bytes)
            except Exception as e:
                zf.writestr(
                    f"{matricula}/semana_{semana}_ERROR.txt",
                    f"No se pudo descargar: {e}",
                )

    zip_buffer.seek(0)
    return FileResult(
        zip_buffer,
        media_type="application/zip",
        headers={
            "Content-Disposition": (
                f"attachment; filename=expediente_{matricula}.zip"
            )
        },
    )


# Ejecuta las reglas del caso de uso con dependencias inyectadas.
async def listar_grupos(carrera, user, *, runtime: RuntimePort):
    async with runtime.database.read() as cur:
        condiciones = []
        params = []

        if carrera:
            condiciones.append("g.carrera = %s")
            params.append(carrera)

        where = "WHERE " + " AND ".join(condiciones) if condiciones else ""

        await cur.execute(
            QueryRef('dual.coordinador_carrera.q014', where=where),
            params,
        )
        rows = await cur.fetchall()
        return [dict(r) for r in rows]


# Ejecuta las reglas del caso de uso con dependencias inyectadas.
async def crear_grupo(data, user, *, runtime: RuntimePort):
    # Nomenclatura generada por columna GENERATED ALWAYS en la BD
    async with runtime.database.transaction() as cur:
        try:
            await cur.execute(
                'dual.coordinador_carrera.q015',
                (
                    data.plan,
                    data.carrera,
                    data.zona,
                    data.modalidad,
                    data.cuatrimestre,
                    data.letra,
                    data.turno,
                ),
            )
            row = await cur.fetchone()
            return dict(row)
        except Exception as exc:
            logger.error(f"Error creando grupo: {exc}")
            raise ApplicationError(
                status_code=400,
                detail="El grupo ya existe o los parametros son invalidos.",
            )


# Ejecuta las reglas del caso de uso con dependencias inyectadas.
async def cargar_alumnos_csv(grupo_id, file, user, *, runtime: RuntimePort):
    content = await file.read()

    try:
        texto = content.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise ApplicationError(
            status_code=422,
            detail="El archivo no tiene codificación UTF-8 válida.",
        )

    reader = csv.DictReader(io.StringIO(texto))

    if reader.fieldnames is None or not {"matricula", "nombre"}.issubset(
        {f.strip().lower() for f in reader.fieldnames}
    ):
        raise ApplicationError(
            status_code=422,
            detail='El CSV debe tener las columnas "matricula" y "nombre".',
        )

    # Parsear y validar todas las filas antes de tocar la BD
    filas_validas = []
    errores = []

    for i, row in enumerate(reader, start=2):  # fila 1 = encabezado
        matricula = (row.get("matricula") or "").strip()
        nombre = (row.get("nombre") or "").strip()

        if not matricula and not nombre:
            continue

        if not matricula.isdigit():
            errores.append(
                {
                    "fila": i,
                    "matricula": matricula,
                    "razon": "La matrícula debe contener solo dígitos.",
                }
            )
            continue

        if len(matricula) != 9:
            errores.append(
                {
                    "fila": i,
                    "matricula": matricula,
                    "razon": (
                        f"Matrícula con {len(matricula)} dígitos "
                        f"(se esperan 9)."
                    ),
                }
            )
            continue

        if not nombre:
            errores.append(
                {
                    "fila": i,
                    "matricula": matricula,
                    "razon": "El nombre no puede estar vacío.",
                }
            )
            continue

        filas_validas.append(
            {
                "fila": i,
                "matricula": matricula,
                "nombre": nombre,
            }
        )

    if not filas_validas:
        return {"insertados": [], "actualizados": [], "errores": errores}

    insertados = []
    actualizados = []

    async with runtime.database.transaction() as cur:
        # Detectar en bloque qué matrículas ya existen en la BD
        matriculas_csv = [f["matricula"] for f in filas_validas]
        await cur.execute(
            'dual.coordinador_carrera.q016',
            (matriculas_csv,),
        )
        existentes = {r[0] for r in await cur.fetchall()}

        for f in filas_validas:
            email = f"{f['matricula']}@ute.edu.mx"
            try:
                await cur.execute(
                    'dual.coordinador_carrera.q017',
                    (f["matricula"], f["nombre"], email, grupo_id),
                )
                alumno_info = {
                    "matricula": f["matricula"],
                    "nombre": f["nombre"],
                }
                if f["matricula"] in existentes:
                    actualizados.append(alumno_info)
                else:
                    insertados.append(alumno_info)
            except Exception as exc:
                logger.error(
                    f"Error cargando alumno {f['matricula']} desde CSV: {exc}"
                )
                errores.append(
                    {
                        "fila": f["fila"],
                        "matricula": f["matricula"],
                        "razon": "Error al guardar en la base de datos",
                    }
                )

    return {
        "insertados": insertados,
        "actualizados": actualizados,
        "errores": errores,
    }


# Ejecuta las reglas del caso de uso con dependencias inyectadas.
async def agregar_alumno_individual(
    grupo_id,
    data,
    user,
    *, runtime: RuntimePort,
):
    async with runtime.database.transaction() as cur:
        # Verificar que el grupo existe
        await cur.execute('dual.coordinador_carrera.q018', (grupo_id,))
        if not await cur.fetchone():
            raise ApplicationError(
                status_code=404,
                detail="Grupo no encontrado",
            )

        email = f"{data.matricula}@ute.edu.mx"
        try:
            await cur.execute(
                'dual.coordinador_carrera.q019',
                (data.matricula, data.nombre, email, grupo_id),
            )
            row = await cur.fetchone()
            return dict(row)
        except Exception as exc:
            logger.error(f"Error al agregar alumno {data.matricula}: {exc}")
            raise ApplicationError(
                status_code=400,
                detail="No se pudo agregar el alumno. Verifica los datos e "
                "intenta de nuevo.",
            )


# Ejecuta las reglas del caso de uso con dependencias inyectadas.
async def actualizar_alumno(matricula, body, user, *, runtime: RuntimePort):
    async with runtime.database.transaction() as cur:
        await cur.execute(
            'dual.coordinador_carrera.q020', (matricula,)
        )
        if not await cur.fetchone():
            raise ApplicationError(
                status_code=404,
                detail="Alumno no encontrado",
            )

        campos = []
        valores = []

        if body.nombre:
            campos.append("nombre = %s")
            valores.append(body.nombre)

        if not campos:
            raise ApplicationError(
                status_code=400,
                detail="No hay campos para actualizar",
            )

        valores.append(matricula)
        query = QueryRef('dual.coordinador_carrera.update_student', assignments=campos)
        await cur.execute(query, tuple(valores))

    return {"mensaje": "Alumno actualizado correctamente"}


# Ejecuta las reglas del caso de uso con dependencias inyectadas.
async def eliminar_alumno(matricula, user, *, runtime: RuntimePort):
    async with runtime.database.transaction() as cur:
        await cur.execute(
            'dual.coordinador_carrera.q021',
            (matricula,),
        )
        alumno = await cur.fetchone()
        if not alumno:
            raise ApplicationError(
                status_code=404,
                detail="Alumno no encontrado",
            )

        # Eliminar registros dependientes en orden de dependencia
        await cur.execute(
            'dual.coordinador_carrera.q022', (matricula,)
        )
        await cur.execute(
            'dual.coordinador_carrera.q023', (matricula,)
        )
        await cur.execute(
            'dual.coordinador_carrera.q024', (matricula,)
        )
        await cur.execute(
            'dual.coordinador_carrera.q025', (matricula,)
        )

    logger.info(
        f"Alumno {alumno['nombre']} ({matricula}) eliminado completamente "
        f"por {user['sub']}"
    )
    return {"mensaje": "Alumno eliminado completamente del sistema"}
