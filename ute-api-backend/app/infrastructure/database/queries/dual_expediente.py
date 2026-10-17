# C08: expediente por período, descarga de aprobados, directorio y paquetes de archivo. Todas
# parametrizadas y estáticas (sin cláusulas dinámicas). Las lecturas se calculan de las tablas de C03
# a C07 (pertenencias, obligaciones, versiones, revisiones y cierres), nunca del texto `cuatrimestre`.

_ORDINAL = """(SELECT count(*) FROM obligaciones_semanales x
                  WHERE x.incorporacion_id = o.incorporacion_id AND x.semana_inicio <= o.semana_inicio)"""

QUERIES = {
    "dual.expediente.alumno": {
        "dynamic": None,
        "sql": """
            SELECT a.matricula, a.nombre,
                   EXISTS (SELECT 1 FROM alumnos_dual x WHERE x.matricula = a.matricula AND x.activo) AS activo,
                   (SELECT max(x.fecha_baja) FROM alumnos_dual x WHERE x.matricula = a.matricula) AS fecha_baja
            FROM alumnos a
            WHERE a.matricula = %s
        """,
    },
    "dual.expediente.periodos": {
        "dynamic": None,
        "sql": """
            SELECT DISTINCT p.id, p.cuatrimestre, p.periodo_label, p.fecha_inicio, p.fecha_fin,
                   p.abierto, p.cerrado, p.cerrado_at, p.evaluacion_finalizada_en
            FROM obligaciones_semanales o
            JOIN alumnos_dual ad ON ad.id = o.incorporacion_id
            JOIN ciclos_dual p ON p.id = o.periodo_id
            WHERE ad.matricula = %s
              AND o.semana_inicio <= COALESCE(ad.fecha_baja, DATE 'infinity')
            ORDER BY p.fecha_inicio DESC
        """,
    },
    "dual.expediente.grupo": {
        "dynamic": None,
        "sql": """
            SELECT COALESCE(gp.nomenclatura, gc.nomenclatura) AS nomenclatura,
                   COALESCE(gp.carrera, gc.carrera) AS carrera,
                   COALESCE(gp.cuatrimestre, gc.cuatrimestre) AS grado,
                   COALESCE(cp.codigo, cc.codigo) AS carrera_codigo
            FROM alumnos a
            LEFT JOIN alumno_grupo_periodo agp ON agp.matricula = a.matricula AND agp.periodo_id = %s
            LEFT JOIN grupos gp ON gp.id = agp.grupo_id
            LEFT JOIN carreras cp ON cp.id = gp.carrera_id
            LEFT JOIN grupos gc ON gc.id = a.grupo_id
            LEFT JOIN carreras cc ON cc.id = gc.carrera_id
            WHERE a.matricula = %s
        """,
    },
    "dual.expediente.aprobados": {
        "dynamic": None,
        "sql": f"""
            SELECT rd.id AS reporte_id, o.semana_inicio, o.semana_fin, {_ORDINAL} AS ordinal,
                   v.numero AS version, v.fecha_inicio AS declarada_inicio, v.fecha_fin AS declarada_fin,
                   v.nota AS declarada_nota,
                   rv.fecha_inicio, rv.fecha_fin, rv.nota, rv.observacion, rv.revisado_en,
                   (rv.documento_firmado_id IS NOT NULL) AS firmado,
                   d.paginas, d.tamano AS tamano_original,
                   COALESCE(d.archivado_en, ds.archivado_en) AS archivado_en
            FROM reportes_dual rd
            JOIN obligaciones_semanales o ON o.id = rd.obligacion_id
            JOIN alumnos_dual ad ON ad.id = o.incorporacion_id
            JOIN LATERAL (SELECT x.* FROM reporte_versiones x WHERE x.reporte_id = rd.id
                          ORDER BY x.numero DESC LIMIT 1) v ON TRUE
            JOIN revisiones rv ON rv.version_id = v.id AND rv.decision = 'Aprobada'
            JOIN documentos d ON d.id = v.documento_id
            LEFT JOIN documentos ds ON ds.id = rv.documento_firmado_id
            WHERE ad.matricula = %s AND o.periodo_id = %s AND rd.estado = 'Aprobada'
            ORDER BY o.semana_inicio
        """,
    },
    "dual.expediente.resultado": {
        "dynamic": None,
        "sql": """
            SELECT suma, cantidad, promedio, cerrado_en
            FROM cierres_alumno_periodo
            WHERE periodo_id = %s AND matricula = %s
        """,
    },
    # Descarga para el personal de un reporte aprobado: la versión indicada debe tener la decisión
    # "Aprobada" (el coordinador no ve versiones pendientes ni rechazadas).
    "dual.expediente.documentos_aprobados": {
        "dynamic": None,
        "sql": """
            SELECT d.clave AS original, ds.clave AS firmado, r.matricula,
                   d.sha256 AS original_sha, ds.sha256 AS firmado_sha,
                   d.archivado_en AS original_archivado, ds.archivado_en AS firmado_archivado
            FROM reportes_dual r
            JOIN reporte_versiones v ON v.reporte_id = r.id AND v.numero = %s
            JOIN documentos d ON d.id = v.documento_id
            JOIN revisiones rv ON rv.version_id = v.id AND rv.decision = 'Aprobada'
            LEFT JOIN documentos ds ON ds.id = rv.documento_firmado_id
            WHERE r.id = %s
        """,
    },
    "dual.expediente.directorio": {
        "dynamic": None,
        "sql": """
            SELECT a.matricula, a.nombre, g.carrera, g.nomenclatura, g.turno, g.modalidad,
                   g.cuatrimestre, e.nombre AS empresa, ad.activo, ad.fecha_baja,
                   (SELECT count(*) FROM reportes_dual rd
                      JOIN obligaciones_semanales o ON o.id = rd.obligacion_id
                      JOIN ciclos_dual p ON p.id = o.periodo_id
                    WHERE rd.matricula = a.matricula AND rd.estado = 'Aprobada'
                      AND (%s::text IS NULL OR p.cuatrimestre = %s)) AS reportes_aprobados,
                   (SELECT ROUND(AVG(rd.calificacion_alumno)::numeric, 2) FROM reportes_dual rd
                      JOIN obligaciones_semanales o ON o.id = rd.obligacion_id
                      JOIN ciclos_dual p ON p.id = o.periodo_id
                    WHERE rd.matricula = a.matricula AND rd.estado = 'Aprobada'
                      AND (%s::text IS NULL OR p.cuatrimestre = %s)) AS promedio,
                   count(*) OVER () AS total
            FROM alumnos a
            JOIN LATERAL (SELECT x.* FROM alumnos_dual x WHERE x.matricula = a.matricula
                          ORDER BY x.activo DESC, x.fecha_inicio DESC, x.created_at DESC, x.id DESC
                          LIMIT 1) ad ON TRUE
            LEFT JOIN grupos g ON g.id = a.grupo_id
            LEFT JOIN empresas e ON e.id = ad.empresa_id
            WHERE (%s::text IS NULL OR a.matricula IN (
                      SELECT x.matricula FROM obligaciones_semanales o
                      JOIN alumnos_dual x ON x.id = o.incorporacion_id
                      JOIN ciclos_dual p ON p.id = o.periodo_id WHERE p.cuatrimestre = %s))
              AND (%s::text IS NULL OR g.nomenclatura = %s)
              AND (%s::text IS NULL OR a.matricula ILIKE '%%' || %s || '%%' OR a.nombre ILIKE '%%' || %s || '%%')
              AND (%s::text = 'todos' OR (%s::text = 'activos' AND ad.activo)
                   OR (%s::text = 'baja' AND NOT ad.activo))
            ORDER BY a.nombre, a.matricula
            LIMIT %s OFFSET %s
        """,
    },
}
