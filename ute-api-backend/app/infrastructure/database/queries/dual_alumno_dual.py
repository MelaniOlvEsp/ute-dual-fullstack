# Consultas SQL parametrizadas del módulo.
# C05: las consultas del flujo secuencial (período abierto, semana 1–18, borrado del rechazado)
# se retiraron; la entrega vive en dual_entregas.py.

QUERIES = {
    'dual.alumno_dual.q005': {
        'dynamic': None,
        'sql': '''
            SELECT id, matricula, cuatrimestre, semana,
                   calificacion_alumno, archivo_pdf_url, estado,
                   nota_agente, created_at, updated_at
            FROM reportes_dual
            WHERE matricula = %s AND cuatrimestre = %s
            ORDER BY semana ASC
        ''',
    },
    'dual.alumno_dual.q006': {
        'dynamic': None,
        'sql': '''
            SELECT id, matricula, cuatrimestre, semana,
                   calificacion_alumno, archivo_pdf_url, estado,
                   nota_agente, created_at, updated_at
            FROM reportes_dual
            WHERE matricula = %s
            ORDER BY cuatrimestre DESC, semana ASC
        ''',
    },
    'dual.alumno_dual.q011': {
        'dynamic': None,
        'sql': '''
            SELECT archivo_pdf_url, archivo_pdf_local, matricula
            FROM reportes_dual WHERE id = %s
        ''',
    },
}
