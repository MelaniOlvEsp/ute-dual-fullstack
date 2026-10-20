# C08B: depuración de los archivos PDF de un período (DP-14). Las filas de `documentos` se conservan.

# Reportes aprobados de un período con su carrera (grupo del período; si no, el actual) y los dos
# documentos de la versión aprobada vigente: los mismos que incluye el paquete de archivo de C08.
_APROBADOS = """
    FROM reportes_dual rd
    JOIN obligaciones_semanales o ON o.id = rd.obligacion_id
    JOIN alumnos_dual ad ON ad.id = o.incorporacion_id
    JOIN alumnos a ON a.matricula = ad.matricula
    LEFT JOIN alumno_grupo_periodo agp ON agp.matricula = a.matricula AND agp.periodo_id = o.periodo_id
    LEFT JOIN grupos gp ON gp.id = agp.grupo_id
    LEFT JOIN carreras cp ON cp.id = gp.carrera_id
    LEFT JOIN grupos gc ON gc.id = a.grupo_id
    LEFT JOIN carreras cc ON cc.id = gc.carrera_id
    JOIN LATERAL (SELECT x.* FROM reporte_versiones x WHERE x.reporte_id = rd.id
                  ORDER BY x.numero DESC LIMIT 1) v ON TRUE
    JOIN revisiones rv ON rv.version_id = v.id AND rv.decision = 'Aprobada'
    JOIN documentos d ON d.id = v.documento_id
    LEFT JOIN documentos ds ON ds.id = rv.documento_firmado_id
"""

_ALCANCE = """periodo_id = %s AND alcance = %s
              AND matricula IS NOT DISTINCT FROM %s::text AND carrera IS NOT DISTINCT FROM %s::text"""

QUERIES = {
    # Archivos y bytes por carrera: totales, vigentes (con archivo) y ya archivados.
    "dual.purgas.resumen_carreras": {
        "dynamic": None,
        "sql": f"""
            SELECT carrera, count(DISTINCT matricula) AS alumnos,
                   count(*) + count(t_f) AS archivos_total,
                   count(*) FILTER (WHERE a_o IS NULL) + count(t_f) FILTER (WHERE a_f IS NULL) AS archivos_vigentes,
                   COALESCE(sum(t_o) FILTER (WHERE a_o IS NULL), 0)
                     + COALESCE(sum(t_f) FILTER (WHERE a_f IS NULL), 0) AS bytes_vigentes
            FROM (
                SELECT ad.matricula, COALESCE(cp.codigo, cc.codigo) AS carrera,
                       d.tamano AS t_o, d.archivado_en AS a_o, ds.tamano AS t_f, ds.archivado_en AS a_f
                {_APROBADOS}
                WHERE o.periodo_id = %s AND rd.estado = 'Aprobada'
            ) base
            GROUP BY carrera
            ORDER BY carrera
        """,
    },
    "dual.purgas.paquetes_vigentes": {
        "dynamic": None,
        "sql": """
            SELECT DISTINCT ON (carrera) id, carrera, generado_en, archivos, manifiesto_sha256
            FROM paquetes_archivo
            WHERE periodo_id = %s AND alcance = 'carrera' AND rol = 'tutor' AND generado_en >= %s
            ORDER BY carrera, generado_en DESC
        """,
    },
    "dual.purgas.paquete_vigente": {
        "dynamic": None,
        "sql": f"""
            SELECT id, generado_en, archivos, manifiesto_sha256
            FROM paquetes_archivo
            WHERE {_ALCANCE} AND rol = 'tutor' AND generado_en >= %s
            ORDER BY generado_en DESC
            LIMIT 1
        """,
    },
    "dual.purgas.programada_de_alcance": {
        "dynamic": None,
        "sql": f"""
            SELECT id, estado, ejecutar_en, archivos, bytes
            FROM purgas_archivo
            WHERE {_ALCANCE} AND estado = 'programada'
        """,
    },
    "dual.purgas.insertar": {
        "dynamic": None,
        "sql": """
            INSERT INTO purgas_archivo
                (periodo_id, alcance, matricula, carrera, paquete_id, manifiesto_sha256, solicitada_por,
                 ejecutar_en, archivos, bytes)
            VALUES (%s, %s, %s, %s, %s, %s, %s, now() + make_interval(days => %s), %s, %s)
            RETURNING id, solicitada_en, ejecutar_en
        """,
    },
    "dual.purgas.marcar_documentos": {
        "dynamic": None,
        "sql": """
            UPDATE documentos SET purga_id = %s
            WHERE id = ANY(%s::uuid[]) AND purga_id IS NULL AND archivado_en IS NULL
        """,
    },
    "dual.purgas.obtener": {
        "dynamic": None,
        "sql": "SELECT * FROM purgas_archivo WHERE id = %s AND periodo_id = %s FOR UPDATE",
    },
    "dual.purgas.cancelar": {
        "dynamic": None,
        "sql": """
            UPDATE purgas_archivo SET estado = 'cancelada', cancelada_por = %s, cancelada_en = now()
            WHERE id = %s AND estado = 'programada' AND intentos = 0
              AND ejecutar_en > clock_timestamp()
            RETURNING id
        """,
    },
    "dual.purgas.liberar_documentos": {
        "dynamic": None,
        "sql": "UPDATE documentos SET purga_id = NULL WHERE purga_id = %s AND archivado_en IS NULL",
    },
    "dual.purgas.vencidas": {
        "dynamic": None,
        "sql": """
            SELECT id FROM purgas_archivo
            WHERE estado = 'programada' AND ejecutar_en <= now()
            ORDER BY ejecutar_en
            LIMIT 20
        """,
    },
    # Bloqueo por documento: dos procesos nunca borran simultáneamente el mismo archivo.
    "dual.purgas.bloquear_vencida": {
        "dynamic": None,
        "sql": """
            SELECT * FROM purgas_archivo
            WHERE id = %s AND estado = 'programada' AND ejecutar_en <= now()
            FOR UPDATE SKIP LOCKED
        """,
    },
    "dual.purgas.iniciar": {
        "dynamic": None,
        "sql": """
            UPDATE purgas_archivo SET intentos = intentos + 1, ultimo_error = NULL
            WHERE id = %s AND estado = 'programada'
        """,
    },
    "dual.purgas.siguiente_documento": {
        "dynamic": None,
        "sql": """
            SELECT id, clave, tamano FROM documentos
            WHERE purga_id = %s AND archivado_en IS NULL
            ORDER BY clave
            LIMIT 1
        """,
    },
    "dual.purgas.archivar_documento": {
        "dynamic": None,
        "sql": "UPDATE documentos SET archivado_en = now() WHERE id = %s AND archivado_en IS NULL",
    },
    "dual.purgas.completar": {
        "dynamic": None,
        "sql": """
            UPDATE purgas_archivo SET estado = 'completada', completada_en = now(), ultimo_error = NULL
            WHERE id = %s AND estado = 'programada'
        """,
    },
    "dual.purgas.registrar_error": {
        "dynamic": None,
        "sql": """
            UPDATE purgas_archivo SET ultimo_error = %s
            WHERE id = %s AND estado = 'programada'
        """,
    },
    "dual.purgas.listar_periodo": {
        "dynamic": None,
        "sql": """
            SELECT p.id, p.alcance, p.matricula, p.carrera, p.estado, p.solicitada_en, p.ejecutar_en,
                   p.completada_en, p.cancelada_en, p.archivos, p.bytes, p.intentos, p.ultimo_error,
                   u.nombre AS solicitada_por_nombre
            FROM purgas_archivo p
            JOIN usuarios u ON u.id = p.solicitada_por
            WHERE p.periodo_id = %s
            ORDER BY p.solicitada_en DESC
        """,
    },
    # Estado del archivo de un alumno en un período: purgas que afectan a sus documentos aprobados.
    "dual.purgas.estado_alumno": {
        "dynamic": None,
        "sql": f"""
            SELECT DISTINCT p.id AS purga_id, p.alcance, p.estado, p.ejecutar_en, p.completada_en
            FROM purgas_archivo p
            JOIN documentos dd ON dd.purga_id = p.id
            WHERE p.estado <> 'cancelada' AND dd.id IN (
                SELECT d.id {_APROBADOS}
                WHERE ad.matricula = %s AND o.periodo_id = %s AND rd.estado = 'Aprobada'
                UNION
                SELECT ds.id {_APROBADOS}
                WHERE ad.matricula = %s AND o.periodo_id = %s AND rd.estado = 'Aprobada' AND ds.id IS NOT NULL)
            ORDER BY p.ejecutar_en DESC
        """,
    },
}
