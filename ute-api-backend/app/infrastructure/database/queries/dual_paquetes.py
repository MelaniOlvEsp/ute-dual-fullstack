# C08: paquetes de archivo (ZIP) por alumno y por carrera y período, y su registro inmutable.

_ORDINAL = """(SELECT count(*) FROM obligaciones_semanales x
                  WHERE x.incorporacion_id = o.incorporacion_id AND x.semana_inicio <= o.semana_inicio)"""

QUERIES = {
    "dual.paquetes.alumnos_carrera": {
        "dynamic": None,
        "sql": """
            SELECT DISTINCT a.matricula, a.nombre,
                   COALESCE(gp.nomenclatura, gc.nomenclatura) AS nomenclatura,
                   COALESCE(gp.carrera, gc.carrera) AS carrera,
                   COALESCE(cp.codigo, cc.codigo) AS carrera_codigo
            FROM obligaciones_semanales o
            JOIN alumnos_dual ad ON ad.id = o.incorporacion_id
            JOIN alumnos a ON a.matricula = ad.matricula
            LEFT JOIN alumno_grupo_periodo agp ON agp.matricula = a.matricula AND agp.periodo_id = o.periodo_id
            LEFT JOIN grupos gp ON gp.id = agp.grupo_id
            LEFT JOIN carreras cp ON cp.id = gp.carrera_id
            LEFT JOIN grupos gc ON gc.id = a.grupo_id
            LEFT JOIN carreras cc ON cc.id = gc.carrera_id
            WHERE o.periodo_id = %s
              AND o.semana_inicio <= COALESCE(ad.fecha_baja, DATE 'infinity')
              AND COALESCE(cp.codigo, cc.codigo) = %s
            ORDER BY nomenclatura, a.matricula
        """,
    },
    "dual.paquetes.documentos": {
        "dynamic": None,
        "sql": f"""
            SELECT rd.id AS reporte_id, o.semana_inicio, o.semana_fin, {_ORDINAL} AS ordinal,
                   v.numero AS version, rv.fecha_inicio, rv.fecha_fin, rv.nota,
                   d.clave AS original_clave, d.sha256 AS original_sha, d.tamano AS original_tamano,
                   ds.clave AS firmado_clave, ds.sha256 AS firmado_sha, ds.tamano AS firmado_tamano,
                   d.id AS original_id, d.archivado_en AS original_archivado, d.purga_id AS original_purga,
                   ds.id AS firmado_id, ds.archivado_en AS firmado_archivado, ds.purga_id AS firmado_purga
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
    "dual.paquetes.registrar": {
        "dynamic": None,
        "sql": """
            INSERT INTO paquetes_archivo
                (alcance, periodo_id, matricula, carrera, rol, generado_por, manifiesto_sha256,
                 alumnos, archivos, bytes)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id, generado_en
        """,
    },
}
