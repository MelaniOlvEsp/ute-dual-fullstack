# Consultas SQL parametrizadas del módulo.

QUERIES = {'dual.coordinador_dual.q000': {'dynamic': 'where',
                                'sql': '\n'
                                       '            SELECT\n'
                                       '                r.id, r.matricula, '
                                       'r.cuatrimestre, r.semana,\n'
                                       '                r.calificacion_alumno, '
                                       'r.fecha_inicio, r.fecha_fin,\n'
                                       '                r.archivo_pdf_url, '
                                       'r.estado, r.nota_agente,\n'
                                       '                r.created_at, '
                                       'r.updated_at, a.nombre, g.carrera,\n'
                                       '                g.nomenclatura, r.obligacion_id,\n'
                                       '                (SELECT max(v.numero) FROM '
                                       'reporte_versiones v\n'
                                       '                 WHERE v.reporte_id = r.id) '
                                       'AS version,\n'
                                       '                (SELECT e2.nombre\n'
                                       '                 FROM alumnos_dual ad2\n'
                                       '                 JOIN empresas e2 '
                                       'ON e2.id = ad2.empresa_id\n'
                                       '                 WHERE ad2.matricula = '
                                       'r.matricula\n'
                                       '                 ORDER BY ad2.activo DESC, '
                                       'ad2.fecha_inicio DESC,\n'
                                       '                          ad2.created_at DESC, '
                                       'ad2.id DESC\n'
                                       '                 LIMIT 1) AS empresa\n'
                                       '            FROM reportes_dual r\n'
                                       '            LEFT JOIN alumnos      a  ON '
                                       'a.matricula  = r.matricula\n'
                                       '            LEFT JOIN grupos       g  ON '
                                       'g.id         = a.grupo_id\n'
                                       '            {where}\n'
                                       '            ORDER BY r.created_at DESC\n'
                                       '            '},
 'dual.coordinador_dual.q002': {'dynamic': None,
                                'sql': 'SELECT id, nombre, created_at FROM '
                                       'empresas ORDER BY nombre ASC'},
 'dual.coordinador_dual.q003': {'dynamic': None,
                                'sql': 'SELECT id FROM empresas WHERE nombre = %s'},
 'dual.coordinador_dual.q004': {'dynamic': None,
                                'sql': '\n'
                                       '            INSERT INTO empresas (nombre)\n'
                                       '            VALUES (%s)\n'
                                       '            RETURNING id, nombre, '
                                       'created_at\n'
                                       '            '},
 'dual.coordinador_dual.q005': {'dynamic': None,
                                'sql': '\n'
                                       '                SELECT ad.id, '
                                       'ad.matricula, ad.cuatrimestre,\n'
                                       '                       ad.empresa_id, '
                                       'ad.activo, ad.created_at,\n'
                                       '                       a.nombre  AS '
                                       'nombre_alumno,\n'
                                       '                       e.nombre  AS '
                                       'nombre_empresa\n'
                                       '                FROM alumnos_dual ad\n'
                                       '                JOIN alumnos  a ON '
                                       'a.matricula = ad.matricula\n'
                                       '                JOIN empresas e ON '
                                       'e.id        = ad.empresa_id\n'
                                       '                WHERE ad.cuatrimestre = '
                                       '%s\n'
                                       '                ORDER BY a.nombre ASC\n'
                                       '                '},
 'dual.coordinador_dual.q006': {'dynamic': None,
                                'sql': '\n'
                                       '                SELECT ad.id, '
                                       'ad.matricula, ad.cuatrimestre,\n'
                                       '                       ad.empresa_id, '
                                       'ad.activo, ad.created_at,\n'
                                       '                       a.nombre  AS '
                                       'nombre_alumno,\n'
                                       '                       e.nombre  AS '
                                       'nombre_empresa\n'
                                       '                FROM alumnos_dual ad\n'
                                       '                JOIN alumnos  a ON '
                                       'a.matricula = ad.matricula\n'
                                       '                JOIN empresas e ON '
                                       'e.id        = ad.empresa_id\n'
                                       '                ORDER BY ad.cuatrimestre '
                                       'DESC, a.nombre ASC\n'
                                       '                '},
 'dual.coordinador_dual.q007': {'dynamic': None,
                                'sql': '\n'
                                       '            SELECT a.matricula, '
                                       'g.cuatrimestre::text AS cuatrimestre\n'
                                       '            FROM alumnos a\n'
                                       '            JOIN grupos g ON g.id = '
                                       'a.grupo_id\n'
                                       '            WHERE a.matricula = %s\n'
                                       '            '},
 'dual.coordinador_dual.q008': {'dynamic': None,
                                'sql': 'SELECT id FROM empresas WHERE id = %s'},
 'dual.coordinador_dual.q010': {'dynamic': None,
                                'sql': '\n'
                                       '            SELECT a.matricula,\n'
                                       '                   a.nombre,\n'
                                       '                   g.turno,\n'
                                       '                   g.carrera,\n'
                                       '                   g.cuatrimestre,\n'
                                       '                   g.nomenclatura,\n'
                                       '                   g.modalidad,\n'
                                       '                   COALESCE(ad.activo, '
                                       'FALSE) AS es_alumno_dual,\n'
                                       '                   ad.activo,\n'
                                       '                   ad.cuatrimestre AS '
                                       'cuatrimestre_dual,\n'
                                       '                   e.id            AS '
                                       'empresa_id,\n'
                                       '                   e.nombre        AS '
                                       'empresa\n'
                                       '            FROM alumnos a\n'
                                       '            LEFT JOIN grupos       g  ON '
                                       'g.id         = a.grupo_id\n'
                                       '            LEFT JOIN alumnos_dual ad ON '
                                       'ad.matricula = a.matricula\n'
                                       '                AND ad.activo = TRUE\n'
                                       '            LEFT JOIN empresas     e  ON '
                                       'e.id         = ad.empresa_id\n'
                                       '            WHERE a.matricula = %s\n'
                                       '            '},
 'dual.coordinador_dual.q011': {'dynamic': None,
                                'sql': '\n'
                                       '            SELECT a.matricula, '
                                       'g.cuatrimestre::text AS cuatrimestre\n'
                                       '            FROM alumnos a\n'
                                       '            LEFT JOIN grupos g ON g.id = '
                                       'a.grupo_id\n'
                                       '            WHERE a.matricula = %s\n'
                                       '            '},
 'dual.coordinador_dual.q012': {'dynamic': None,
                                'sql': 'SELECT id FROM empresas WHERE id = %s'},
 'dual.coordinador_dual.q016': {'dynamic': None,
                                'sql': '\n'
                                       '            SELECT cuatrimestre, '
                                       'fecha_inicio, periodo_label\n'
                                       '            FROM ciclos_dual\n'
                                       '            WHERE abierto = TRUE\n'
                                       '            ORDER BY created_at DESC\n'
                                       '            LIMIT 1\n'
                                       '            '},
 'dual.coordinador_dual.q018': {'dynamic': None,
                                'sql': '\n'
                                       '            SELECT cuatrimestre, '
                                       'periodo_label, fecha_inicio, fecha_fin,\n'
                                       '                   abierto, cerrado, '
                                       'cerrado_at\n'
                                       '            FROM ciclos_dual\n'
                                       '            WHERE abierto = TRUE\n'
                                       '            ORDER BY created_at DESC\n'
                                       '            LIMIT 1\n'
                                       '            '},
 'dual.coordinador_dual.q019': {'dynamic': None,
                                'sql': '\n'
                                       '            SELECT cuatrimestre, '
                                       'periodo_label, fecha_inicio, fecha_fin,\n'
                                       '                   abierto, cerrado, '
                                       'cerrado_at\n'
                                       '            FROM ciclos_dual\n'
                                       '            WHERE cerrado = TRUE\n'
                                       '            ORDER BY cerrado_at DESC\n'
                                       '            LIMIT 1\n'
                                       '            '},
 'dual.coordinador_dual.q020': {'dynamic': None,
                                'sql': 'SELECT cuatrimestre, periodo_label FROM '
                                       'ciclos_dual WHERE abierto = TRUE LIMIT 1'},
 'dual.coordinador_dual.q021': {'dynamic': None,
                                'sql': '\n'
                                       '            INSERT INTO ciclos_dual\n'
                                       '                (cuatrimestre, '
                                       'periodo_label, fecha_inicio, fecha_fin,\n'
                                       '                 abierto, cerrado)\n'
                                       '            VALUES (%s, %s, %s, %s, TRUE, '
                                       'FALSE)\n'
                                       '            ON CONFLICT (cuatrimestre)\n'
                                       '            DO UPDATE SET\n'
                                       '                periodo_label = '
                                       'EXCLUDED.periodo_label,\n'
                                       '                fecha_inicio   = '
                                       'EXCLUDED.fecha_inicio,\n'
                                       '                fecha_fin      = '
                                       'EXCLUDED.fecha_fin,\n'
                                       '                abierto        = TRUE,\n'
                                       '                cerrado        = FALSE,\n'
                                       '                cerrado_por    = NULL,\n'
                                       '                cerrado_at     = NULL\n'
                                       '            RETURNING id, cuatrimestre, '
                                       'periodo_label, fecha_inicio, fecha_fin\n'
                                       '            '},
 'dual.coordinador_dual.q024': {'dynamic': None,
                                'sql': '\n'
                                       '            SELECT archivo_pdf_url, '
                                       'archivo_pdf_local\n'
                                       '            FROM reportes_dual WHERE id = '
                                       '%s\n'
                                       '            '}}

QUERIES.update({
    'dual.coordinador_dual.active_incorporation': {
        'dynamic': None,
        'sql': '''
            SELECT id, matricula, cuatrimestre, empresa_id, activo,
                   fecha_inicio, fecha_baja, created_at
            FROM alumnos_dual
            WHERE matricula = %s AND activo = TRUE
            FOR UPDATE
        ''',
    },
    'dual.coordinador_dual.insert_incorporation': {
        'dynamic': None,
        'sql': '''
            INSERT INTO alumnos_dual
                (matricula, empresa_id, activo, fecha_inicio, asignado_por)
            VALUES (%s, %s, TRUE, %s, %s)
            RETURNING id, matricula, cuatrimestre, empresa_id, activo,
                      fecha_inicio, fecha_baja, created_at
        ''',
    },
    'dual.coordinador_dual.close_incorporation': {
        'dynamic': None,
        'sql': '''
            UPDATE alumnos_dual
            SET activo = FALSE, fecha_baja = %s, baja_por = %s
            WHERE matricula = %s AND activo = TRUE AND fecha_inicio <= %s
            RETURNING id, fecha_inicio, fecha_baja
        ''',
    },
    'dual.coordinador_dual.incorporation_history': {
        'dynamic': None,
        'sql': '''
            SELECT ad.id, ad.matricula, ad.empresa_id, e.nombre AS empresa,
                   ad.fecha_inicio, ad.fecha_baja, ad.activo, ad.created_at
            FROM alumnos_dual ad
            LEFT JOIN empresas e ON e.id = ad.empresa_id
            WHERE ad.matricula = %s
            ORDER BY ad.fecha_inicio DESC, ad.created_at DESC
        ''',
    },
    'dual.coordinador_dual.q010': {
        'dynamic': None,
        'sql': '''
            SELECT a.matricula, a.nombre, g.turno, c.nombre AS carrera,
                   c.codigo AS carrera_codigo, g.cuatrimestre, g.nomenclatura,
                   g.modalidad, COALESCE(ad.activo, FALSE) AS es_alumno_dual,
                   ad.activo, ad.fecha_inicio, ad.fecha_baja,
                   e.id AS empresa_id, e.nombre AS empresa
            FROM alumnos a
            LEFT JOIN grupos g ON g.id = a.grupo_id
            LEFT JOIN carreras c ON c.id = g.carrera_id
            LEFT JOIN alumnos_dual ad ON ad.matricula = a.matricula AND ad.activo = TRUE
            LEFT JOIN empresas e ON e.id = ad.empresa_id
            WHERE a.matricula = %s
        ''',
    },
})

# C03: la incorporación pertenece a un período por solapamiento de fechas (inicio/baja
# contra fecha_inicio/fecha_fin del período; sin fechas de período, solo si sigue activa)
# y el grupo se toma de la pertenencia del período. alumnos_dual.cuatrimestre ya no se
# escribe ni se consulta. Estas definiciones sustituyen a q005, q006, q015 y q017 de arriba.
_EN_PERIODO = '''(CASE WHEN p.fecha_inicio IS NULL OR p.fecha_fin IS NULL THEN ad.activo
                 ELSE ad.fecha_inicio <= p.fecha_fin
                      AND COALESCE(ad.fecha_baja, DATE 'infinity') >= p.fecha_inicio END)'''

QUERIES.update({
    'dual.coordinador_dual.q005': {
        'dynamic': None,
        'sql': f'''
            SELECT ad.id, ad.matricula, p.cuatrimestre, ad.empresa_id, ad.activo,
                   ad.fecha_inicio, ad.fecha_baja, ad.created_at,
                   a.nombre AS nombre_alumno, e.nombre AS nombre_empresa
            FROM ciclos_dual p
            JOIN alumnos_dual ad ON {_EN_PERIODO}
            JOIN alumnos a ON a.matricula = ad.matricula
            JOIN empresas e ON e.id = ad.empresa_id
            WHERE p.cuatrimestre = %s
            ORDER BY a.nombre ASC, ad.fecha_inicio DESC
        ''',
    },
    'dual.coordinador_dual.q006': {
        'dynamic': None,
        'sql': f'''
            SELECT ad.id, ad.matricula, per.cuatrimestre, ad.empresa_id, ad.activo,
                   ad.fecha_inicio, ad.fecha_baja, ad.created_at,
                   a.nombre AS nombre_alumno, e.nombre AS nombre_empresa
            FROM alumnos_dual ad
            JOIN alumnos a ON a.matricula = ad.matricula
            JOIN empresas e ON e.id = ad.empresa_id
            LEFT JOIN LATERAL (
                SELECT p.cuatrimestre FROM ciclos_dual p
                WHERE {_EN_PERIODO}
                ORDER BY p.fecha_inicio DESC NULLS LAST, p.created_at DESC
                LIMIT 1
            ) per ON TRUE
            ORDER BY ad.fecha_inicio DESC, a.nombre ASC
        ''',
    },
})
