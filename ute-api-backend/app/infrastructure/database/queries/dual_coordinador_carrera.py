# Consultas SQL parametrizadas del módulo.

QUERIES = {'dual.coordinador_carrera.q000': {'dynamic': None,
                                   'sql': '\n'
                                          '            SELECT DISTINCT cuatrimestre\n'
                                          '            FROM reportes_dual\n'
                                          "            WHERE estado = 'Aprobada'\n"
                                          '            ORDER BY cuatrimestre DESC\n'
                                          '            '},
 'dual.coordinador_carrera.q001': {'dynamic': None,
                                   'sql': 'SELECT periodo_label FROM ciclos_dual WHERE '
                                          'cuatrimestre = %s LIMIT 1'},
 'dual.coordinador_carrera.q002': {'dynamic': None,
                                   'sql': '\n'
                                          '            SELECT cuatrimestre, periodo_label\n'
                                          '            FROM ciclos_dual\n'
                                          '            ORDER BY created_at DESC\n'
                                          '            '},
 'dual.coordinador_carrera.q003': {'dynamic': 'where',
                                   'sql': '\n'
                                          '            SELECT DISTINCT\n'
                                          '                a.matricula,\n'
                                          '                a.nombre,\n'
                                          '                g.turno,\n'
                                          '                g.carrera,\n'
                                          '                g.cuatrimestre,\n'
                                          '                g.nomenclatura,\n'
                                          '                g.modalidad,\n'
                                          '                e.nombre AS empresa,\n'
                                          '                (\n'
                                          '                    SELECT COUNT(*)\n'
                                          '                    FROM reportes_dual rd\n'
                                          '                    WHERE rd.matricula = '
                                          'a.matricula\n'
                                          "                      AND rd.estado = 'Aprobada'\n"
                                          '                      AND (%s::text IS NULL\n'
                                          '                           OR rd.cuatrimestre = '
                                          'g.cuatrimestre::text)\n'
                                          '                ) AS reportes_aprobados,\n'
                                          '                (\n'
                                          '                    SELECT '
                                          'ROUND(AVG(rd.calificacion_alumno)::numeric, 2)\n'
                                          '                    FROM reportes_dual rd\n'
                                          '                    WHERE rd.matricula = '
                                          'a.matricula\n'
                                          "                      AND rd.estado = 'Aprobada'\n"
                                          '                      AND (%s::text IS NULL\n'
                                          '                           OR rd.cuatrimestre = '
                                          'g.cuatrimestre::text)\n'
                                          '                ) AS promedio\n'
                                          '            FROM alumnos a\n'
                                          '            LEFT JOIN grupos       g  ON '
                                          'g.id         = a.grupo_id\n'
                                          '            LEFT JOIN LATERAL (\n'
                                          '                SELECT x.empresa_id, x.activo FROM alumnos_dual x\n'
                                          '                WHERE x.matricula = a.matricula\n'
                                          '                ORDER BY x.activo DESC, x.fecha_inicio DESC,\n'
                                          '                         x.created_at DESC, x.id DESC\n'
                                          '                LIMIT 1\n'
                                          '            ) ad ON TRUE\n'
                                          '            LEFT JOIN empresas     e  ON '
                                          'e.id         = ad.empresa_id\n'
                                          '            {where}\n'
                                          '            ORDER BY a.nombre ASC\n'
                                          '            '},
 'dual.coordinador_carrera.q004': {'dynamic': None,
                                   'sql': 'SELECT matricula FROM alumnos WHERE matricula = '
                                          '%s'},
 'dual.coordinador_carrera.q005': {'dynamic': None,
                                   'sql': '\n'
                                          '                SELECT cuatrimestre\n'
                                          '                FROM reportes_dual\n'
                                          '                WHERE matricula = %s AND estado = '
                                          "'Aprobada'\n"
                                          '                ORDER BY cuatrimestre DESC\n'
                                          '                LIMIT 1\n'
                                          '                '},
 'dual.coordinador_carrera.q006': {'dynamic': None,
                                   'sql': '\n'
                                          '                SELECT id, matricula, '
                                          'cuatrimestre, semana,\n'
                                          '                       calificacion_alumno, '
                                          'archivo_pdf_url, estado,\n'
                                          '                       nota_agente, created_at, '
                                          'updated_at\n'
                                          '                FROM reportes_dual\n'
                                          '                WHERE matricula = %s\n'
                                          '                  AND cuatrimestre = %s\n'
                                          "                  AND estado = 'Aprobada'\n"
                                          '                ORDER BY semana ASC\n'
                                          '                '},
 'dual.coordinador_carrera.q007': {'dynamic': None,
                                   'sql': '\n'
                                          '                SELECT id, matricula, '
                                          'cuatrimestre, semana,\n'
                                          '                       calificacion_alumno, '
                                          'archivo_pdf_url, estado,\n'
                                          '                       nota_agente, created_at, '
                                          'updated_at\n'
                                          '                FROM reportes_dual\n'
                                          '                WHERE matricula = %s\n'
                                          "                  AND estado = 'Aprobada'\n"
                                          '                ORDER BY cuatrimestre DESC, semana '
                                          'ASC\n'
                                          '                '},
 'dual.coordinador_carrera.q008': {'dynamic': None,
                                   'sql': '\n'
                                          '            SELECT archivo_pdf_url, '
                                          'archivo_pdf_local\n'
                                          '            FROM reportes_dual WHERE id = %s\n'
                                          '            '},
 'dual.coordinador_carrera.q009': {'dynamic': None,
                                   'sql': '\n'
                                          '            SELECT a.matricula, g.nomenclatura\n'
                                          '            FROM alumnos a\n'
                                          '            LEFT JOIN grupos g ON g.id = '
                                          'a.grupo_id\n'
                                          '            WHERE a.matricula = %s\n'
                                          '            '},
 'dual.coordinador_carrera.q010': {'dynamic': None,
                                   'sql': '\n'
                                          '                SELECT semana, '
                                          'calificacion_alumno\n'
                                          '                FROM reportes_dual\n'
                                          '                WHERE matricula = %s\n'
                                          '                  AND cuatrimestre = %s\n'
                                          "                  AND estado = 'Aprobada'\n"
                                          '                ORDER BY semana ASC\n'
                                          '                '},
 'dual.coordinador_carrera.q011': {'dynamic': None,
                                   'sql': '\n'
                                          '                SELECT semana, '
                                          'calificacion_alumno\n'
                                          '                FROM reportes_dual\n'
                                          '                WHERE matricula = %s\n'
                                          "                  AND estado = 'Aprobada'\n"
                                          '                ORDER BY cuatrimestre DESC, semana '
                                          'ASC\n'
                                          '                '},
 'dual.coordinador_carrera.q012': {'dynamic': None,
                                   'sql': 'SELECT g.cuatrimestre::text AS cuatrimestre FROM '
                                          'alumnos a LEFT JOIN grupos g ON g.id = a.grupo_id '
                                          'WHERE a.matricula = %s'},
 'dual.coordinador_carrera.q013': {'dynamic': None,
                                   'sql': '\n'
                                          '            SELECT semana, archivo_pdf_url, '
                                          'archivo_pdf_local\n'
                                          '            FROM reportes_dual\n'
                                          '            WHERE matricula = %s\n'
                                          '              AND cuatrimestre = %s\n'
                                          "              AND estado = 'Aprobada'\n"
                                          '            ORDER BY semana ASC\n'
                                          '            '},
 'dual.coordinador_carrera.q014': {'dynamic': 'where',
                                   'sql': '\n'
                                          '            SELECT\n'
                                          '                g.id,\n'
                                          '                g.nomenclatura,\n'
                                          '                g.carrera,\n'
                                          '                g.cuatrimestre,\n'
                                          '                g.modalidad,\n'
                                          '                g.turno,\n'
                                          '                g.letra,\n'
                                          '                COUNT(a.matricula) AS '
                                          'total_alumnos\n'
                                          '            FROM grupos g\n'
                                          '            LEFT JOIN alumnos a ON a.grupo_id = '
                                          'g.id\n'
                                          '            {where}\n'
                                          '            GROUP BY g.id\n'
                                          '            ORDER BY g.carrera ASC, g.cuatrimestre '
                                          'ASC, g.letra ASC\n'
                                          '            '},
 'dual.coordinador_carrera.q015': {'dynamic': None,
                                   'sql': '\n'
                                          '                INSERT INTO grupos (\n'
                                          '                    plan, carrera, zona, '
                                          'modalidad,\n'
                                          '                    cuatrimestre, letra, turno\n'
                                          '                ) VALUES (%s, %s, %s, %s, %s, %s, '
                                          '%s)\n'
                                          '                RETURNING id, nomenclatura\n'
                                          '                '},
 'dual.coordinador_carrera.q016': {'dynamic': None,
                                   'sql': 'SELECT matricula FROM alumnos WHERE matricula = '
                                          'ANY(%s)'},
 'dual.coordinador_carrera.q017': {'dynamic': None,
                                   'sql': '\n'
                                          '                    INSERT INTO alumnos '
                                          '(matricula, nombre, email, grupo_id, '
                                          'registro_dual_autorizado)\n'
                                          '                    VALUES (%s, %s, %s, %s, TRUE)\n'
                                          '                    ON CONFLICT (matricula) DO '
                                          'UPDATE\n'
                                          '                    SET nombre   = '
                                          'EXCLUDED.nombre,\n'
                                          '                        email = EXCLUDED.email,\n'
                                          '                        grupo_id = '
                                          'EXCLUDED.grupo_id,\n'
                                          '                        registro_dual_autorizado = '
                                          'TRUE\n'
                                          '                    '},
 'dual.coordinador_carrera.q018': {'dynamic': None,
                                   'sql': 'SELECT id FROM grupos WHERE id = %s'},
 'dual.coordinador_carrera.q019': {'dynamic': None,
                                   'sql': '\n'
                                          '                INSERT INTO alumnos (matricula, '
                                          'nombre, email, grupo_id, '
                                          'registro_dual_autorizado)\n'
                                          '                VALUES (%s, %s, %s, %s, TRUE)\n'
                                          '                ON CONFLICT (matricula) DO UPDATE\n'
                                          '                SET nombre   = EXCLUDED.nombre,\n'
                                          '                    grupo_id = EXCLUDED.grupo_id,\n'
                                          '                        registro_dual_autorizado = '
                                          'TRUE\n'
                                          '                RETURNING matricula, nombre, '
                                          'grupo_id\n'
                                          '                '},
 'dual.coordinador_carrera.q020': {'dynamic': None,
                                   'sql': 'SELECT matricula FROM alumnos WHERE matricula = '
                                          '%s'},
 'dual.coordinador_carrera.q021': {'dynamic': None,
                                   'sql': 'SELECT matricula, nombre FROM alumnos WHERE '
                                          'matricula = %s'},
 'dual.coordinador_carrera.q022': {'dynamic': None,
                                   'sql': 'UPDATE usuarios SET activo = FALSE, credential_version = credential_version + 1 WHERE matricula = %s AND activo = TRUE'},
 'dual.coordinador_carrera.q025': {'dynamic': None,
                                   'sql': 'UPDATE alumnos SET registro_dual_autorizado = FALSE WHERE matricula = %s'},
 'dual.coordinador_carrera.update_student': {'dynamic': 'assignments',
                                             'sql': 'UPDATE alumnos SET {assignments} WHERE '
                                                    'matricula = %s'}}

# C03 conserva las claves públicas y sustituye únicamente sus contratos SQL.
QUERIES.update({
    'dual.coordinador_carrera.q001': {
        'dynamic': None,
        'sql': 'SELECT id, periodo_label FROM ciclos_dual WHERE cuatrimestre = %s LIMIT 1',
    },
    'dual.coordinador_carrera.q002': {
        'dynamic': None,
        'sql': '''
            SELECT id, cuatrimestre, periodo_label, fecha_inicio, fecha_fin
            FROM ciclos_dual
            ORDER BY fecha_inicio DESC NULLS LAST, created_at DESC
        ''',
    },
    'dual.coordinador_carrera.q014': {
        'dynamic': 'where',
        'sql': '''
            SELECT g.id, g.nomenclatura, c.nombre AS carrera,
                   c.codigo AS carrera_codigo, g.cuatrimestre,
                   g.modalidad, g.turno, g.letra, g.ciclo_ingreso,
                   COUNT(DISTINCT agp.matricula) AS total_alumnos
            FROM grupos g
            JOIN carreras c ON c.id = g.carrera_id
            LEFT JOIN alumno_grupo_periodo agp ON agp.grupo_id = g.id
            {where}
            GROUP BY g.id, c.nombre, c.codigo
            ORDER BY c.codigo, g.cuatrimestre, g.letra
        ''',
    },
    'dual.coordinador_carrera.q015': {
        'dynamic': None,
        'sql': '''
            INSERT INTO grupos
                (plan, carrera, zona, modalidad, cuatrimestre, letra, turno, carrera_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s,
                    (SELECT id FROM carreras WHERE nombre = %s AND activo = TRUE))
            RETURNING id, nomenclatura
        ''',
    },
})
