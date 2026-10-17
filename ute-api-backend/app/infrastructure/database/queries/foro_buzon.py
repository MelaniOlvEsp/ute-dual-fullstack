# Consultas SQL parametrizadas del módulo.

QUERIES = {
    'foro.buzon.q000': {'dynamic': None, 'sql': """
        SELECT alumno_id, area, estado FROM buzon_mensajes
        WHERE id = %s AND area = 'dual'
    """},
    # C09: un hilo nuevo puede enlazar el anterior (hilo_anterior_id).
    'foro.buzon.q001': {'dynamic': None, 'sql': """
        INSERT INTO buzon_mensajes
            (alumno_id, matricula, correo, area, asunto, mensaje, hilo_anterior_id)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        RETURNING id, correo, area, asunto, mensaje, estado, created_at, hilo_anterior_id
    """},
    'foro.buzon.q002': {'dynamic': None, 'sql': """
        SELECT id, correo, area, asunto, mensaje, estado, created_at
        FROM buzon_mensajes
        WHERE area = %s
        ORDER BY
            CASE estado
                WHEN 'Enviado' THEN 0
                WHEN 'Leido' THEN 1
                ELSE 2
            END,
            created_at DESC
    """},
    'foro.buzon.q003': {'dynamic': None, 'sql': """
        SELECT id, correo, area, asunto, mensaje, estado, created_at
        FROM buzon_mensajes
        WHERE alumno_id = %s AND area = 'dual'
        ORDER BY created_at DESC
    """},
    'foro.buzon.q004': {'dynamic': None, 'sql': """
        SELECT id, correo, area, asunto, mensaje, estado, created_at,
               hilo_anterior_id, cerrado_en, reabierto_en
        FROM buzon_mensajes WHERE id = %s AND area = 'dual'
    """},
    'foro.buzon.q005': {'dynamic': None, 'sql': """
        SELECT id, mensaje_id, autor_id, autor_rol, texto, created_at
        FROM buzon_respuestas
        WHERE mensaje_id = %s
        ORDER BY created_at ASC
    """},
    'foro.buzon.q006': {'dynamic': None, 'sql': """
        INSERT INTO buzon_respuestas (mensaje_id, autor_id, autor_rol, texto)
        VALUES (%s, %s, %s, %s)
        RETURNING id, mensaje_id, autor_id, autor_rol, texto, created_at
    """},
    # Marcar como leído nunca reabre un hilo cerrado (C09, D1).
    'foro.buzon.q008': {'dynamic': None, 'sql':
        "UPDATE buzon_mensajes SET estado = 'Leido' WHERE id = %s AND estado = 'Enviado'"},
    'foro.buzon.q009': {'dynamic': None, 'sql': """
        UPDATE buzon_mensajes
        SET estado = 'Cerrado', cerrado_por = %s, cerrado_en = now()
        WHERE id = %s
    """},
    'foro.buzon.hilo_propio': {'dynamic': None, 'sql':
        "SELECT id, estado FROM buzon_mensajes WHERE id = %s AND alumno_id = %s AND area = 'dual'"},
    'foro.buzon.reabrir': {'dynamic': None, 'sql': """
        UPDATE buzon_mensajes SET estado = 'Leido', reabierto_por = %s, reabierto_en = now()
        WHERE id = %s AND estado = 'Cerrado'
    """},
}
