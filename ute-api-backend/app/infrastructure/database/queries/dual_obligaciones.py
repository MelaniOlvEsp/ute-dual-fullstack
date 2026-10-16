# C04: obligaciones semanales. Las semanas posteriores a la baja de una incorporación se
# excluyen de las lecturas (no se borran). Desde C05, "recibida" significa que la obligación
# tiene un reporte (entrega real ligada por `obligacion_id`), en cualquier estado.

# Obligaciones numeradas sobre TODA la incorporación (el ordinal no depende del filtro).
_NUMERADAS = '''
    numeradas AS (
        SELECT o.*, ad.matricula, ad.empresa_id, ad.activo AS incorporacion_activa,
               ROW_NUMBER() OVER (PARTITION BY o.incorporacion_id
                                  ORDER BY o.semana_inicio) AS ordinal
        FROM obligaciones_semanales o
        JOIN alumnos_dual ad ON ad.id = o.incorporacion_id
        WHERE o.semana_inicio <= COALESCE(ad.fecha_baja, DATE 'infinity')
          AND {alcance}
    )
'''

_COLUMNAS = '''
    n.id, n.incorporacion_id, n.matricula, n.ordinal, n.semana_inicio, n.semana_fin,
    n.inicio_efectivo, n.fin_efectivo, n.parcial,
    p.cuatrimestre AS periodo, p.periodo_label,
    e.nombre AS empresa,
    p.abierto AS periodo_abierto, p.cerrado AS periodo_cerrado,
    p.cerrado_at AS periodo_cerrado_en,
    (rd.id IS NOT NULL) AS recibida,
    rd.id AS reporte_id, rd.estado AS entrega,
    CASE WHEN rd.estado = 'Rechazada' THEN rd.nota_agente END AS observacion,
    (SELECT max(v.numero) FROM reporte_versiones v WHERE v.reporte_id = rd.id) AS version
'''

_UNIONES = '''
    FROM numeradas n
    LEFT JOIN ciclos_dual p ON p.id = n.periodo_id
    LEFT JOIN empresas e ON e.id = n.empresa_id
    LEFT JOIN reportes_dual rd ON rd.obligacion_id = n.id
'''

QUERIES = {
    "dual.obligaciones.candidates": {
        "dynamic": None,
        "sql": """
            SELECT ad.id, ad.matricula, ad.fecha_inicio, ad.fecha_baja, ad.activo,
                   (SELECT max(o.semana_inicio) FROM obligaciones_semanales o
                    WHERE o.incorporacion_id = ad.id) AS ultima
            FROM alumnos_dual ad
            WHERE (%s::text IS NULL AND ad.activo) OR ad.matricula = %s
        """,
    },
    "dual.obligaciones.lock": {
        "dynamic": None,
        "sql": "SELECT pg_advisory_xact_lock(hashtextextended(%s::text, 4))",
    },
    "dual.obligaciones.upsert": {
        "dynamic": None,
        "sql": """
            INSERT INTO obligaciones_semanales
                (incorporacion_id, semana_inicio, semana_fin, inicio_efectivo,
                 fin_efectivo, parcial, periodo_id)
            VALUES (%s, %s, %s, %s, %s, %s,
                    (SELECT id FROM ciclos_dual
                     WHERE fecha_inicio <= %s AND fecha_fin >= %s LIMIT 1))
            ON CONFLICT (incorporacion_id, semana_inicio) DO UPDATE
            SET inicio_efectivo = EXCLUDED.inicio_efectivo,
                fin_efectivo = EXCLUDED.fin_efectivo,
                parcial = EXCLUDED.parcial,
                periodo_id = COALESCE(obligaciones_semanales.periodo_id, EXCLUDED.periodo_id)
        """,
    },
    "dual.obligaciones.backfill_period": {
        "dynamic": None,
        "sql": """
            UPDATE obligaciones_semanales SET periodo_id = %s
            WHERE periodo_id IS NULL AND semana_fin BETWEEN %s AND %s
        """,
    },
    "dual.obligaciones.by_student": {
        "dynamic": None,
        "sql": f"""
            WITH {_NUMERADAS.format(
                alcance="o.incorporacion_id IN (SELECT id FROM alumnos_dual WHERE matricula = %s)")}
            SELECT {_COLUMNAS}
            {_UNIONES}
            WHERE (%s::text IS NULL OR p.cuatrimestre = %s)
            ORDER BY n.semana_inicio DESC, n.incorporacion_id
        """,
    },
    "dual.obligaciones.open": {
        "dynamic": None,
        "sql": f"""
            WITH {_NUMERADAS.format(alcance="TRUE")}
            SELECT {_COLUMNAS}, a.nombre,
                   COALESCE(gp.nomenclatura, gc.nomenclatura) AS nomenclatura
            {_UNIONES}
            JOIN alumnos a ON a.matricula = n.matricula
            LEFT JOIN alumno_grupo_periodo agp
              ON agp.matricula = n.matricula AND agp.periodo_id = n.periodo_id
            LEFT JOIN grupos gp ON gp.id = agp.grupo_id
            LEFT JOIN grupos gc ON gc.id = a.grupo_id
            WHERE rd.id IS NULL
              AND n.incorporacion_activa
            ORDER BY n.semana_inicio, a.nombre
        """,
    },
    "dual.obligaciones.missing_in_period": {
        "dynamic": None,
        "sql": f"""
            WITH {_NUMERADAS.format(alcance="TRUE")}
            SELECT {_COLUMNAS}, a.nombre,
                   COALESCE(gp.nomenclatura, gc.nomenclatura) AS nomenclatura
            {_UNIONES}
            JOIN alumnos a ON a.matricula = n.matricula
            LEFT JOIN alumno_grupo_periodo agp
              ON agp.matricula = n.matricula AND agp.periodo_id = n.periodo_id
            LEFT JOIN grupos gp ON gp.id = agp.grupo_id
            LEFT JOIN grupos gc ON gc.id = a.grupo_id
            WHERE p.cuatrimestre = %s AND n.ordinal = %s
              AND rd.id IS NULL
            ORDER BY a.nombre
        """,
    },
    "dual.obligaciones.overlapping_period": {
        "dynamic": None,
        "sql": """
            SELECT cuatrimestre, periodo_label, fecha_inicio, fecha_fin
            FROM ciclos_dual
            WHERE cuatrimestre <> %s
              AND fecha_inicio IS NOT NULL AND fecha_fin IS NOT NULL
              AND daterange(fecha_inicio, fecha_fin, '[]') && daterange(%s, %s, '[]')
            ORDER BY fecha_inicio
            LIMIT 1
        """,
    },
    "dual.obligaciones.period_lock": {
        "dynamic": None,
        "sql": "SELECT pg_advisory_xact_lock(19865)",
    },
    "dual.obligaciones.student_exists": {
        "dynamic": None,
        "sql": "SELECT matricula FROM alumnos WHERE matricula = %s",
    },
}
