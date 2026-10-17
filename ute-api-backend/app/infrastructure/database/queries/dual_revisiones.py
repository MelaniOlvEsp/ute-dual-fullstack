# C06: revisión de versiones, correcciones trazables y documentos firmados. Todas
# parametrizadas; ninguna actualiza ni borra revisiones (la base lo impide con disparadores).

QUERIES = {
    "dual.revisiones.reporte": {
        "dynamic": None,
        "sql": """
            SELECT r.id, r.obligacion_id, r.matricula, r.estado, r.semana,
                   (SELECT max(v.numero) FROM reporte_versiones v WHERE v.reporte_id = r.id) AS ultima
            FROM reportes_dual r
            WHERE r.id = %s
        """,
    },
    "dual.revisiones.reporte_bloqueado": {
        "dynamic": None,
        "sql": """
            SELECT r.id, r.obligacion_id, r.matricula, r.estado, r.semana,
                   (SELECT max(v.numero) FROM reporte_versiones v WHERE v.reporte_id = r.id) AS ultima
            FROM reportes_dual r
            WHERE r.id = %s
            FOR UPDATE
        """,
    },
    "dual.revisiones.version": {
        "dynamic": None,
        "sql": """
            SELECT v.id, v.numero, v.fecha_inicio, v.fecha_fin, v.nota, d.clave AS clave_original, d.sha256 AS sha_original,
                   rv.id AS revision_id, rv.tutor_id, rv.decision, rv.observacion,
                   rv.fecha_inicio AS rev_inicio, rv.fecha_fin AS rev_fin, rv.nota AS rev_nota
            FROM reporte_versiones v
            JOIN documentos d ON d.id = v.documento_id
            LEFT JOIN revisiones rv ON rv.version_id = v.id
            WHERE v.reporte_id = %s AND v.numero = %s
        """,
    },
    "dual.revisiones.insert_firmado": {
        "dynamic": None,
        "sql": """
            INSERT INTO documentos (clave, tamano, sha256, paginas, subido_por, rol, firma_modo)
            VALUES (%s, %s, %s, %s, %s, 'firmado', %s)
            RETURNING id
        """,
    },
    "dual.revisiones.insert_revision": {
        "dynamic": None,
        "sql": """
            INSERT INTO revisiones
                (version_id, tutor_id, decision, observacion, fecha_inicio, fecha_fin, nota,
                 documento_firmado_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id, revisado_en
        """,
    },
    "dual.revisiones.insert_correccion": {
        "dynamic": None,
        "sql": """
            INSERT INTO reporte_correcciones (revision_id, campo, valor_previo, valor_nuevo)
            VALUES (%s, %s, %s, %s)
        """,
    },
    # La decisión se copia a la versión revisada (puede fijarse una sola vez; lo impide la base).
    "dual.revisiones.decidir_version": {
        "dynamic": None,
        "sql": """
            UPDATE reporte_versiones
            SET decision = %s, nota_revision = %s, revisado_por = %s, revisado_en = %s
            WHERE id = %s AND decision IS NULL
        """,
    },
    # Columnas heredadas: reflejan la versión vigente con los valores validados por el tutor.
    "dual.revisiones.actualizar_reporte": {
        "dynamic": None,
        "sql": """
            UPDATE reportes_dual
            SET estado = %s, nota_agente = %s, revisado_por = %s, revisado_en = %s,
                calificacion_alumno = %s, fecha_inicio = %s, fecha_fin = %s,
                archivo_pdf_local = COALESCE(%s, archivo_pdf_local),
                archivo_pdf_url = CASE WHEN %s::text IS NULL THEN archivo_pdf_url ELSE NULL END,
                updated_at = NOW()
            WHERE id = %s
        """,
    },
    "dual.revisiones.detalle": {
        "dynamic": None,
        "sql": """
            SELECT r.id, r.matricula, r.estado, r.semana, r.cuatrimestre, r.created_at,
                   r.obligacion_id, a.nombre, g.carrera, g.nomenclatura,
                   o.semana_inicio, o.semana_fin, p.abierto AS periodo_abierto,
                   p.cerrado AS periodo_cerrado,
                   (SELECT e2.nombre
                    FROM alumnos_dual ad2
                    JOIN empresas e2 ON e2.id = ad2.empresa_id
                    WHERE ad2.matricula = r.matricula
                    ORDER BY ad2.activo DESC, ad2.fecha_inicio DESC, ad2.created_at DESC, ad2.id DESC
                    LIMIT 1) AS empresa,
                   (SELECT max(v.numero) FROM reporte_versiones v WHERE v.reporte_id = r.id) AS version_vigente
            FROM reportes_dual r
            LEFT JOIN alumnos a ON a.matricula = r.matricula
            LEFT JOIN grupos g ON g.id = a.grupo_id
            LEFT JOIN obligaciones_semanales o ON o.id = r.obligacion_id
            LEFT JOIN ciclos_dual p ON p.id = o.periodo_id
            WHERE r.id = %s
        """,
    },
    "dual.revisiones.versiones": {
        "dynamic": None,
        "sql": """
            SELECT v.numero, v.fecha_inicio, v.fecha_fin, v.nota, v.recibido_en,
                   d.tamano, d.paginas, d.sha256,
                   rv.decision, rv.observacion, rv.revisado_en, rv.fecha_inicio AS validada_inicio,
                   rv.fecha_fin AS validada_fin, rv.nota AS validada_nota,
                   (rv.documento_firmado_id IS NOT NULL) AS firmado,
                   df.firma_modo,
                   COALESCE((SELECT json_agg(json_build_object(
                                 'campo', c.campo, 'previo', c.valor_previo, 'nuevo', c.valor_nuevo)
                                 ORDER BY c.campo)
                             FROM reporte_correcciones c WHERE c.revision_id = rv.id), '[]'::json)
                       AS correcciones
            FROM reporte_versiones v
            JOIN documentos d ON d.id = v.documento_id
            LEFT JOIN revisiones rv ON rv.version_id = v.id
            LEFT JOIN documentos df ON df.id = rv.documento_firmado_id
            WHERE v.reporte_id = %s
            ORDER BY v.numero DESC
        """,
    },
    # Descarga para el personal: original y firmado de una versión (sin filtro de propietario).
    "dual.revisiones.documentos": {
        "dynamic": None,
        "sql": """
            SELECT d.clave AS original, ds.clave AS firmado, r.matricula,
                   d.sha256 AS original_sha, ds.sha256 AS firmado_sha,
                   d.archivado_en AS original_archivado, ds.archivado_en AS firmado_archivado
            FROM reportes_dual r
            JOIN reporte_versiones v ON v.reporte_id = r.id AND v.numero = %s
            JOIN documentos d ON d.id = v.documento_id
            LEFT JOIN revisiones rv ON rv.version_id = v.id
            LEFT JOIN documentos ds ON ds.id = rv.documento_firmado_id
            WHERE r.id = %s
        """,
    },
}
