# Consultas SQL parametrizadas del módulo.

QUERIES = {'dual.alumno_dual.q000': {'dynamic': None,
                           'sql': 'SELECT cuatrimestre FROM ciclos_dual WHERE '
                                  'abierto = TRUE LIMIT 1'},
 'dual.alumno_dual.q001': {'dynamic': None,
                           'sql': '\n'
                                  '            SELECT ad.activo\n'
                                  '            FROM alumnos_dual ad\n'
                                  '            WHERE ad.matricula = %s\n'
                                  '            ORDER BY ad.created_at DESC\n'
                                  '            LIMIT 1\n'
                                  '            '},
 'dual.alumno_dual.q002': {'dynamic': None,
                           'sql': '\n'
                                  '            SELECT id, estado, archivo_pdf_url, '
                                  'archivo_pdf_local\n'
                                  '            FROM reportes_dual\n'
                                  '            WHERE matricula = %s AND '
                                  'cuatrimestre = %s AND semana = %s\n'
                                  '            '},
 'dual.alumno_dual.q003': {'dynamic': None,
                           'sql': 'DELETE FROM reportes_dual WHERE id = %s'},
 'dual.alumno_dual.q004': {'dynamic': None,
                           'sql': '\n'
                                  '            INSERT INTO reportes_dual\n'
                                  '                (matricula, cuatrimestre, '
                                  'semana, calificacion_alumno,\n'
                                  '                 fecha_inicio, fecha_fin, '
                                  'archivo_pdf_url, estado)\n'
                                  '            VALUES (%s, %s, %s, %s, %s, %s, %s, '
                                  "'Pendiente')\n"
                                  '            RETURNING id\n'
                                  '            '},
 'dual.alumno_dual.q005': {'dynamic': None,
                           'sql': '\n'
                                  '                SELECT id, matricula, '
                                  'cuatrimestre, semana,\n'
                                  '                       calificacion_alumno, '
                                  'archivo_pdf_url, estado,\n'
                                  '                       nota_agente, created_at, '
                                  'updated_at\n'
                                  '                FROM reportes_dual\n'
                                  '                WHERE matricula = %s AND '
                                  'cuatrimestre = %s\n'
                                  '                ORDER BY semana ASC\n'
                                  '                '},
 'dual.alumno_dual.q006': {'dynamic': None,
                           'sql': '\n'
                                  '                SELECT id, matricula, '
                                  'cuatrimestre, semana,\n'
                                  '                       calificacion_alumno, '
                                  'archivo_pdf_url, estado,\n'
                                  '                       nota_agente, created_at, '
                                  'updated_at\n'
                                  '                FROM reportes_dual\n'
                                  '                WHERE matricula = %s\n'
                                  '                ORDER BY cuatrimestre DESC, '
                                  'semana ASC\n'
                                  '                '},
 'dual.alumno_dual.q007': {'dynamic': None,
                           'sql': '\n'
                                  '            SELECT cuatrimestre, cerrado FROM '
                                  'ciclos_dual\n'
                                  '            WHERE abierto = TRUE\n'
                                  '            ORDER BY created_at DESC LIMIT 1\n'
                                  '            '},
 'dual.alumno_dual.q008': {'dynamic': None,
                           'sql': '\n'
                                  '                SELECT cuatrimestre, cerrado '
                                  'FROM ciclos_dual\n'
                                  '                WHERE cerrado = TRUE\n'
                                  '                ORDER BY cerrado_at DESC LIMIT '
                                  '1\n'
                                  '                '},
 'dual.alumno_dual.q009': {'dynamic': None,
                           'sql': '\n'
                                  '                SELECT g.cuatrimestre::text AS '
                                  'cuatrimestre\n'
                                  '                FROM alumnos a\n'
                                  '                JOIN grupos g ON g.id = '
                                  'a.grupo_id\n'
                                  '                WHERE a.matricula = %s\n'
                                  '                '},
 'dual.alumno_dual.q010': {'dynamic': None,
                           'sql': '\n'
                                  '            SELECT semana, estado, nota_agente\n'
                                  '            FROM reportes_dual\n'
                                  '            WHERE matricula = %s AND '
                                  'cuatrimestre = %s\n'
                                  '            ORDER BY semana DESC, created_at '
                                  'DESC\n'
                                  '            LIMIT 1\n'
                                  '            '},
 'dual.alumno_dual.q011': {'dynamic': None,
                           'sql': '\n'
                                  '            SELECT archivo_pdf_url, '
                                  'archivo_pdf_local, matricula\n'
                                  '            FROM reportes_dual WHERE id = %s\n'
                                  '            '}}
