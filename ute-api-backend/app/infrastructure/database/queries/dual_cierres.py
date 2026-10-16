# C07: cierre de recepción, finalización de la evaluación y promedio. Todas parametrizadas; la base
# impide modificar o borrar el resultado congelado y reabrir un período finalizado.

_COLUMNAS_PERIODO = """
    id, cuatrimestre, periodo_label, fecha_inicio, fecha_fin, abierto, cerrado, cerrado_por,
    cerrado_at, evaluacion_finalizada_en, evaluacion_finalizada_por
"""

# Obligaciones del período sin las semanas posteriores a la baja (no se borran, solo se excluyen).
_DEL_PERIODO = """
    FROM obligaciones_semanales o
    JOIN alumnos_dual ad ON ad.id = o.incorporacion_id
    LEFT JOIN reportes_dual rd ON rd.obligacion_id = o.id
    WHERE o.periodo_id = %s
      AND o.semana_inicio <= COALESCE(ad.fecha_baja, DATE 'infinity')
"""

QUERIES = {
    "dual.cierres.bloquear_compartido": {
        "dynamic": None,
        "sql": "SELECT id FROM ciclos_dual WHERE id = %s FOR SHARE",
    },
    "dual.cierres.bloquear_exclusivo": {
        "dynamic": None,
        "sql": f"SELECT {_COLUMNAS_PERIODO} FROM ciclos_dual WHERE id = %s FOR NO KEY UPDATE",
    },
    "dual.cierres.periodo": {
        "dynamic": None,
        "sql": f"SELECT {_COLUMNAS_PERIODO} FROM ciclos_dual WHERE id = %s",
    },
    "dual.cierres.listar": {
        "dynamic": None,
        "sql": f"""
            SELECT {_COLUMNAS_PERIODO}
            FROM ciclos_dual
            ORDER BY abierto DESC, fecha_inicio DESC NULLS LAST, created_at DESC
        """,
    },
    "dual.cierres.por_etiqueta": {
        "dynamic": None,
        "sql": f"SELECT {_COLUMNAS_PERIODO} FROM ciclos_dual WHERE cuatrimestre = %s",
    },
    "dual.cierres.cerrar": {
        "dynamic": None,
        "sql": """
            UPDATE ciclos_dual
            SET cerrado = TRUE, abierto = FALSE, cerrado_por = %s, cerrado_at = NOW()
            WHERE id = %s
            RETURNING cerrado_at
        """,
    },
    "dual.cierres.finalizar": {
        "dynamic": None,
        "sql": """
            UPDATE ciclos_dual
            SET evaluacion_finalizada_en = NOW(), evaluacion_finalizada_por = %s
            WHERE id = %s
            RETURNING evaluacion_finalizada_en
        """,
    },
    "dual.cierres.conteos": {
        "dynamic": None,
        "sql": f"""
            SELECT count(*) AS obligaciones,
                   count(rd.id) AS recibidas,
                   count(*) FILTER (WHERE rd.estado = 'Pendiente') AS pendientes_revision,
                   count(*) FILTER (WHERE rd.estado = 'Rechazada') AS rechazadas,
                   count(*) FILTER (WHERE rd.estado = 'Aprobada') AS aprobadas,
                   count(*) FILTER (WHERE rd.id IS NULL) AS sin_entrega,
                   count(*) FILTER (WHERE rd.id IS NULL AND %s::date IS NOT NULL
                                      AND o.semana_fin >= %s::date) AS no_recibidas_por_cierre
            {_DEL_PERIODO}
        """,
    },
    "dual.cierres.alumnos": {
        "dynamic": None,
        "sql": """
            SELECT ad.matricula, a.nombre,
                   COALESCE(gp.nomenclatura, gc.nomenclatura) AS nomenclatura,
                   count(*) AS obligaciones,
                   count(*) FILTER (WHERE rd.estado = 'Aprobada') AS aprobadas,
                   count(*) FILTER (WHERE rd.estado = 'Pendiente') AS pendientes_revision,
                   count(*) FILTER (WHERE rd.estado = 'Rechazada') AS rechazadas,
                   count(*) FILTER (WHERE rd.id IS NULL) AS sin_entrega
            FROM obligaciones_semanales o
            JOIN alumnos_dual ad ON ad.id = o.incorporacion_id
            JOIN alumnos a ON a.matricula = ad.matricula
            LEFT JOIN alumno_grupo_periodo agp
              ON agp.matricula = ad.matricula AND agp.periodo_id = o.periodo_id
            LEFT JOIN grupos gp ON gp.id = agp.grupo_id
            LEFT JOIN grupos gc ON gc.id = a.grupo_id
            LEFT JOIN reportes_dual rd ON rd.obligacion_id = o.id
            WHERE o.periodo_id = %s
              AND o.semana_inicio <= COALESCE(ad.fecha_baja, DATE 'infinity')
            GROUP BY ad.matricula, a.nombre, gp.nomenclatura, gc.nomenclatura
            ORDER BY a.nombre, ad.matricula
        """,
    },
    "dual.cierres.aprobadas": {
        "dynamic": None,
        "sql": f"""
            SELECT ad.matricula, rd.id AS reporte_id, rd.calificacion_alumno::int AS nota
            {_DEL_PERIODO}
              AND rd.estado = 'Aprobada'
            ORDER BY ad.matricula, o.semana_inicio
        """,
    },
    "dual.cierres.pendientes": {
        "dynamic": None,
        "sql": f"""
            SELECT count(*) AS pendientes
            {_DEL_PERIODO}
              AND rd.estado = 'Pendiente'
        """,
    },
    "dual.cierres.resultados": {
        "dynamic": None,
        "sql": """
            SELECT matricula, suma, cantidad, promedio
            FROM cierres_alumno_periodo
            WHERE periodo_id = %s
        """,
    },
    "dual.cierres.insert_cierre": {
        "dynamic": None,
        "sql": """
            INSERT INTO cierres_alumno_periodo (periodo_id, matricula, suma, cantidad, promedio, cerrado_por)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id
        """,
    },
    "dual.cierres.insert_nota": {
        "dynamic": None,
        "sql": "INSERT INTO cierre_alumno_notas (cierre_id, reporte_id, nota) VALUES (%s, %s, %s)",
    },
}
