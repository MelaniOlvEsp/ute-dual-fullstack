"""Consultas de firma académica."""
QUERIES = {
    'dual.tutor.save_signature': {'dynamic': None, 'sql': """
        INSERT INTO tutor_firmas (tutor_id, imagen, content_type)
        VALUES (%s, %s, %s)
        ON CONFLICT (tutor_id) DO UPDATE
        SET imagen = EXCLUDED.imagen,
            content_type = EXCLUDED.content_type,
            actualizada_en = NOW()
    """},
    'dual.tutor.signature_exists': {'dynamic': None, 'sql':
        'SELECT 1 FROM tutor_firmas WHERE tutor_id = %s'},
    'dual.tutor.get_signature': {'dynamic': None, 'sql':
        'SELECT imagen FROM tutor_firmas WHERE tutor_id = %s'},
    'dual.tutor.identity': {'dynamic': None, 'sql':
        'SELECT nombre FROM usuarios WHERE id = %s'},
}
