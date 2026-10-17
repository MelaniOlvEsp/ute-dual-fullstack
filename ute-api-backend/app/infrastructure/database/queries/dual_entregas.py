# C05: entregas por obligación, versiones y documentos. Todas parametrizadas; ninguna
# actualiza ni borra versiones recibidas (la base lo impide con un disparador).

QUERIES = {
    "dual.entregas.lock": {
        "dynamic": None,
        "sql": "SELECT pg_advisory_xact_lock(hashtextextended(%s::text, 5))",
    },
    "dual.entregas.obligacion_propia": {
        "dynamic": None,
        "sql": """
            SELECT o.id, o.semana_inicio, o.semana_fin, o.periodo_id, ad.matricula,
                   (SELECT count(*) FROM obligaciones_semanales x
                    WHERE x.incorporacion_id = o.incorporacion_id
                      AND x.semana_inicio <= o.semana_inicio) AS ordinal,
                   p.cuatrimestre AS periodo, p.abierto, p.cerrado
            FROM obligaciones_semanales o
            JOIN alumnos_dual ad ON ad.id = o.incorporacion_id
            LEFT JOIN ciclos_dual p ON p.id = o.periodo_id
            WHERE o.id = %s AND ad.matricula = %s
              AND o.semana_inicio <= COALESCE(ad.fecha_baja, DATE 'infinity')
        """,
    },
    "dual.entregas.reporte_de_obligacion": {
        "dynamic": None,
        "sql": """
            SELECT r.id, r.estado, r.nota_agente, r.revisado_por, r.revisado_en,
                   (SELECT max(v.numero) FROM reporte_versiones v WHERE v.reporte_id = r.id) AS ultima
            FROM reportes_dual r
            WHERE r.obligacion_id = %s
            FOR UPDATE
        """,
    },
    "dual.entregas.version_actual": {
        "dynamic": None,
        "sql": """
            SELECT v.numero, v.fecha_inicio, v.fecha_fin, v.nota, d.sha256
            FROM reporte_versiones v
            JOIN documentos d ON d.id = v.documento_id
            WHERE v.reporte_id = %s
            ORDER BY v.numero DESC
            LIMIT 1
        """,
    },
    "dual.entregas.insert_documento": {
        "dynamic": None,
        "sql": """
            INSERT INTO documentos (clave, tamano, sha256, paginas, subido_por)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id
        """,
    },
    "dual.entregas.insert_reporte": {
        "dynamic": None,
        "sql": """
            INSERT INTO reportes_dual
                (matricula, cuatrimestre, semana, calificacion_alumno, estado,
                 fecha_inicio, fecha_fin, archivo_pdf_local, obligacion_id)
            VALUES (%s, %s, %s, %s, 'Pendiente', %s, %s, %s, %s)
            RETURNING id
        """,
    },
    "dual.entregas.insert_version": {
        "dynamic": None,
        "sql": """
            INSERT INTO reporte_versiones
                (reporte_id, numero, fecha_inicio, fecha_fin, nota, documento_id, recibido_por)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id, numero, recibido_en
        """,
    },
    "dual.entregas.snapshot_decision": {
        "dynamic": None,
        "sql": """
            UPDATE reporte_versiones
            SET decision = %s, nota_revision = %s, revisado_por = %s, revisado_en = %s
            WHERE reporte_id = %s AND numero = %s AND decision IS NULL
        """,
    },
    "dual.entregas.reenviar": {
        "dynamic": None,
        "sql": """
            UPDATE reportes_dual
            SET estado = 'Pendiente', calificacion_alumno = %s, fecha_inicio = %s, fecha_fin = %s,
                archivo_pdf_local = %s, archivo_pdf_url = NULL, nota_agente = NULL,
                revisado_por = NULL, revisado_en = NULL, updated_at = NOW()
            WHERE id = %s
        """,
    },
    "dual.entregas.versiones": {
        "dynamic": None,
        "sql": """
            SELECT v.numero, v.fecha_inicio, v.fecha_fin, v.nota, v.recibido_en,
                   COALESCE(v.decision,
                            CASE WHEN v.numero = u.ultima AND r.estado IN ('Aprobada', 'Rechazada')
                                 THEN r.estado END) AS decision,
                   COALESCE(v.nota_revision,
                            CASE WHEN v.numero = u.ultima THEN r.nota_agente END) AS nota_revision,
                   COALESCE(v.revisado_en,
                            CASE WHEN v.numero = u.ultima THEN r.revisado_en END) AS revisado_en,
                   d.tamano, d.sha256, d.paginas,
                   (rv.documento_firmado_id IS NOT NULL) AS firmado,
                   rv.fecha_inicio AS validada_inicio, rv.fecha_fin AS validada_fin,
                   rv.nota AS validada_nota
            FROM reportes_dual r
            JOIN reporte_versiones v ON v.reporte_id = r.id
            JOIN documentos d ON d.id = v.documento_id
            LEFT JOIN revisiones rv ON rv.version_id = v.id
            CROSS JOIN LATERAL (SELECT max(x.numero) AS ultima
                                FROM reporte_versiones x WHERE x.reporte_id = r.id) u
            WHERE r.id = %s AND r.matricula = %s
            ORDER BY v.numero DESC
        """,
    },
    "dual.entregas.version_documento": {
        "dynamic": None,
        "sql": """
            SELECT d.clave AS original, ds.clave AS firmado,
                   d.archivado_en AS original_archivado, ds.archivado_en AS firmado_archivado
            FROM reportes_dual r
            JOIN reporte_versiones v ON v.reporte_id = r.id
            JOIN documentos d ON d.id = v.documento_id
            LEFT JOIN revisiones rv ON rv.version_id = v.id
            LEFT JOIN documentos ds ON ds.id = rv.documento_firmado_id
            WHERE r.id = %s AND r.matricula = %s AND v.numero = %s
        """,
    },
    "dual.entregas.claves_referenciadas": {
        "dynamic": None,
        "sql": "SELECT clave FROM documentos",
    },
}
