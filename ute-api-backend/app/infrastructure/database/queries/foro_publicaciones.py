# Consultas SQL parametrizadas del módulo.

QUERIES = {'foro.publicaciones.q000': {'dynamic': None,
                             'sql': 'SELECT nombre, roles FROM usuarios WHERE id = '
                                    '%s'},
 'foro.publicaciones.q001': {'dynamic': None,
                             'sql': '\n'
                                    '            INSERT INTO foro_publicaciones\n'
                                    '                (autor_id, autor_nombre, '
                                    'autor_rol, contenido)\n'
                                    '            VALUES (%s, %s, %s, %s)\n'
                                    '            RETURNING id, autor_id, '
                                    'autor_nombre, autor_rol, contenido,\n'
                                    '                      created_at\n'
                                    '            '},
 'foro.publicaciones.q002': {'dynamic': None,
                             'sql': '\n'
                                    '            SELECT id, autor_id, '
                                    'autor_nombre, autor_rol, contenido,\n'
                                    '                   created_at\n'
                                    '            FROM foro_publicaciones\n'
                                    '            ORDER BY created_at DESC\n'
                                    '            LIMIT %s\n'
                                    '            '},
 'foro.publicaciones.q003': {'dynamic': None,
                             'sql': '\n'
                                    '            SELECT publicacion_id, tipo, '
                                    'COUNT(*) AS total\n'
                                    '            FROM foro_reacciones\n'
                                    '            WHERE publicacion_id = ANY(%s)\n'
                                    '            GROUP BY publicacion_id, tipo\n'
                                    '            '},
 'foro.publicaciones.q004': {'dynamic': None,
                             'sql': '\n'
                                    '            SELECT publicacion_id, tipo\n'
                                    '            FROM foro_reacciones\n'
                                    '            WHERE publicacion_id = ANY(%s) '
                                    'AND usuario_id = %s\n'
                                    '            '},
 'foro.publicaciones.q005': {'dynamic': None,
                             'sql': 'SELECT autor_id FROM foro_publicaciones WHERE '
                                    'id = %s'},
 'foro.publicaciones.q006': {'dynamic': None,
                             'sql': 'DELETE FROM foro_publicaciones WHERE id = %s'},
 'foro.publicaciones.q007': {'dynamic': None,
                             'sql': 'SELECT id FROM foro_publicaciones WHERE id = '
                                    '%s'},
 'foro.publicaciones.q008': {'dynamic': None,
                             'sql': '\n'
                                    '            SELECT tipo FROM foro_reacciones\n'
                                    '            WHERE publicacion_id = %s AND '
                                    'usuario_id = %s\n'
                                    '            '},
 'foro.publicaciones.q009': {'dynamic': None,
                             'sql': '\n'
                                    '                DELETE FROM foro_reacciones\n'
                                    '                WHERE publicacion_id = %s AND '
                                    'usuario_id = %s\n'
                                    '                '},
 'foro.publicaciones.q010': {'dynamic': None,
                             'sql': '\n'
                                    '            INSERT INTO foro_reacciones '
                                    '(publicacion_id, usuario_id, tipo)\n'
                                    '            VALUES (%s, %s, %s)\n'
                                    '            ON CONFLICT (publicacion_id, '
                                    'usuario_id)\n'
                                    '            DO UPDATE SET tipo = '
                                    'EXCLUDED.tipo, created_at = NOW()\n'
                                    '            '}}
