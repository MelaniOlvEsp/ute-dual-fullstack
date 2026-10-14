# Consultas SQL parametrizadas del módulo.

QUERIES = {'foro.buzon.q000': {'dynamic': None,
                     'sql': 'SELECT alumno_id, area, estado FROM buzon_mensajes '
                            "WHERE id = %s AND area = 'dual'"},
 'foro.buzon.q001': {'dynamic': None,
                     'sql': '\n'
                            '            INSERT INTO buzon_mensajes\n'
                            '                (alumno_id, matricula, correo, area, '
                            'asunto, mensaje)\n'
                            '            VALUES (%s, %s, %s, %s, %s, %s)\n'
                            '            RETURNING id, correo, area, asunto, '
                            'mensaje, estado, created_at\n'
                            '            '},
 'foro.buzon.q002': {'dynamic': None,
                     'sql': '\n'
                            '            SELECT id, correo, area, asunto, mensaje, '
                            'estado, created_at\n'
                            '            FROM buzon_mensajes\n'
                            '            WHERE area = %s\n'
                            '            ORDER BY\n'
                            '                CASE estado\n'
                            "                    WHEN 'Enviado' THEN 0\n"
                            "                    WHEN 'Leido' THEN 1\n"
                            '                    ELSE 2\n'
                            '                END,\n'
                            '                created_at DESC\n'
                            '            '},
 'foro.buzon.q003': {'dynamic': None,
                     'sql': '\n'
                            '            SELECT id, correo, area, asunto, mensaje, '
                            'estado, created_at\n'
                            '            FROM buzon_mensajes\n'
                            "            WHERE alumno_id = %s AND area = 'dual'\n"
                            '            ORDER BY created_at DESC\n'
                            '            '},
 'foro.buzon.q004': {'dynamic': None,
                     'sql': '\n'
                            '            SELECT id, correo, area, asunto, mensaje, '
                            'estado, created_at\n'
                            "            FROM buzon_mensajes WHERE id = %s AND area = 'dual'\n"
                            '            '},
 'foro.buzon.q005': {'dynamic': None,
                     'sql': '\n'
                            '            SELECT id, mensaje_id, autor_id, '
                            'autor_rol, texto, created_at\n'
                            '            FROM buzon_respuestas\n'
                            '            WHERE mensaje_id = %s\n'
                            '            ORDER BY created_at ASC\n'
                            '            '},
 'foro.buzon.q006': {'dynamic': None,
                     'sql': '\n'
                            '            INSERT INTO buzon_respuestas\n'
                            '                (mensaje_id, autor_id, autor_rol, '
                            'texto)\n'
                            '            VALUES (%s, %s, %s, %s)\n'
                            '            RETURNING id, mensaje_id, autor_id, '
                            'autor_rol, texto, created_at\n'
                            '            '},
 'foro.buzon.q007': {'dynamic': None,
                     'sql': "UPDATE buzon_mensajes SET estado = 'Enviado' WHERE id "
                            '= %s'},
 'foro.buzon.q008': {'dynamic': None,
                     'sql': "UPDATE buzon_mensajes SET estado = 'Leido' WHERE id = "
                            '%s'},
 'foro.buzon.q009': {'dynamic': None,
                     'sql': '\n'
                            '            UPDATE buzon_mensajes\n'
                            "            SET estado = 'Cerrado', cerrado_por = %s, "
                            'cerrado_en = now()\n'
                            '            WHERE id = %s\n'
                            '            '}}
