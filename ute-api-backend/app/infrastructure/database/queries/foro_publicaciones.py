# Consultas SQL parametrizadas del módulo.

QUERIES = {
    'foro.publicaciones.q000': {'dynamic': None, 'sql': "SELECT nombre, roles FROM usuarios WHERE id = %s"},
    'foro.publicaciones.q001': {'dynamic': None, 'sql': """
        INSERT INTO foro_publicaciones (autor_id, autor_nombre, autor_rol, contenido)
        VALUES (%s, %s, %s, %s)
        RETURNING id, autor_id, autor_nombre, autor_rol, contenido, created_at
    """},
    # C09 (D2): lo eliminado se conserva y deja de mostrarse.
    'foro.publicaciones.q002': {'dynamic': None, 'sql': """
        SELECT id, autor_id, autor_nombre, autor_rol, contenido, created_at
        FROM foro_publicaciones
        WHERE eliminada_en IS NULL
        ORDER BY created_at DESC
        LIMIT %s
    """},
    'foro.publicaciones.q003': {'dynamic': None, 'sql': """
        SELECT publicacion_id, tipo, COUNT(*) AS total
        FROM foro_reacciones
        WHERE publicacion_id = ANY(%s)
        GROUP BY publicacion_id, tipo
    """},
    'foro.publicaciones.q004': {'dynamic': None, 'sql': """
        SELECT publicacion_id, tipo
        FROM foro_reacciones
        WHERE publicacion_id = ANY(%s) AND usuario_id = %s
    """},
    'foro.publicaciones.q005': {'dynamic': None, 'sql':
        "SELECT autor_id FROM foro_publicaciones WHERE id = %s AND eliminada_en IS NULL FOR UPDATE"},
    'foro.publicaciones.q006': {'dynamic': None, 'sql': """
        UPDATE foro_publicaciones SET eliminada_por = %s, eliminada_en = now()
        WHERE id = %s AND eliminada_en IS NULL
    """},
    'foro.publicaciones.q007': {'dynamic': None, 'sql':
        "SELECT id FROM foro_publicaciones WHERE id = %s AND eliminada_en IS NULL"},
    'foro.publicaciones.q008': {'dynamic': None, 'sql': """
        SELECT tipo FROM foro_reacciones
        WHERE publicacion_id = %s AND usuario_id = %s
    """},
    'foro.publicaciones.q009': {'dynamic': None, 'sql': """
        DELETE FROM foro_reacciones
        WHERE publicacion_id = %s AND usuario_id = %s
    """},
    'foro.publicaciones.q010': {'dynamic': None, 'sql': """
        INSERT INTO foro_reacciones (publicacion_id, usuario_id, tipo)
        VALUES (%s, %s, %s)
        ON CONFLICT (publicacion_id, usuario_id)
        DO UPDATE SET tipo = EXCLUDED.tipo, created_at = NOW()
    """},
}
