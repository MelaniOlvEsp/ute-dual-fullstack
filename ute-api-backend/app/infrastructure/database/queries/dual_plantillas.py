# C09: plantilla común versionada (pareja Word + PDF). Las versiones son inmutables.

_COLUMNAS = """p.id, p.numero, p.publicada_en, p.vigente, p.nota, u.nombre AS publicada_por_nombre,
               p.word_clave, p.word_tamano, p.word_sha256,
               p.pdf_clave, p.pdf_tamano, p.pdf_sha256, p.pdf_paginas"""

QUERIES = {
    "dual.plantillas.vigente": {
        "dynamic": None,
        "sql": f"""
            SELECT {_COLUMNAS}
            FROM plantillas_version p JOIN usuarios u ON u.id = p.publicada_por
            WHERE p.vigente
        """,
    },
    "dual.plantillas.por_numero": {
        "dynamic": None,
        "sql": f"""
            SELECT {_COLUMNAS}
            FROM plantillas_version p JOIN usuarios u ON u.id = p.publicada_por
            WHERE p.numero = %s
        """,
    },
    "dual.plantillas.listar": {
        "dynamic": None,
        "sql": f"""
            SELECT {_COLUMNAS}
            FROM plantillas_version p JOIN usuarios u ON u.id = p.publicada_por
            ORDER BY p.numero DESC
        """,
    },
    # Serializa las publicaciones: dos coordinadores no obtienen el mismo número.
    "dual.plantillas.bloquear": {
        "dynamic": None,
        "sql": "SELECT pg_advisory_xact_lock(19869)",
    },
    "dual.plantillas.siguiente_numero": {
        "dynamic": None,
        "sql": "SELECT COALESCE(max(numero), 0) + 1 AS numero FROM plantillas_version",
    },
    "dual.plantillas.retirar_vigente": {
        "dynamic": None,
        "sql": "UPDATE plantillas_version SET vigente = FALSE WHERE vigente",
    },
    "dual.plantillas.insertar": {
        "dynamic": None,
        "sql": """
            INSERT INTO plantillas_version
                (numero, publicada_por, vigente, nota, word_clave, word_tamano, word_sha256,
                 pdf_clave, pdf_tamano, pdf_sha256, pdf_paginas)
            VALUES (%s, %s, TRUE, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id, numero, publicada_en
        """,
    },
}
