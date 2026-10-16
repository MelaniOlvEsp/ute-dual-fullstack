QUERIES = {
    "dual.organization.careers": {
        "dynamic": None,
        "sql": "SELECT id, codigo, nombre FROM carreras WHERE activo = TRUE ORDER BY codigo",
    },
    "dual.organization.group_period": {
        "dynamic": None,
        "sql": """
            SELECT g.id AS grupo_id, g.nomenclatura, p.id AS periodo_id,
                   p.periodo_label
            FROM grupos g CROSS JOIN ciclos_dual p
            WHERE g.id = %s AND p.id = %s
        """,
    },
    "dual.organization.students_for_period": {
        "dynamic": None,
        "sql": """
            SELECT a.matricula, a.nombre, agp.grupo_id, g.nomenclatura
            FROM alumnos a
            LEFT JOIN alumno_grupo_periodo agp
              ON agp.matricula = a.matricula AND agp.periodo_id = %s
            LEFT JOIN grupos g ON g.id = agp.grupo_id
            WHERE a.matricula = ANY(%s)
        """,
    },
    "dual.organization.insert_student": {
        "dynamic": None,
        "sql": """
            INSERT INTO alumnos
                (matricula, nombre, email, grupo_id, registro_dual_autorizado)
            VALUES (%s, %s, %s, %s, TRUE)
            ON CONFLICT (matricula) DO NOTHING
            RETURNING matricula
        """,
    },
    "dual.organization.authorize_student": {
        "dynamic": None,
        "sql": """
            UPDATE alumnos SET registro_dual_autorizado = TRUE
            WHERE matricula = %s
        """,
    },
    "dual.organization.insert_membership": {
        "dynamic": None,
        "sql": """
            INSERT INTO alumno_grupo_periodo
                (matricula, grupo_id, periodo_id, asignado_por)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (matricula, periodo_id) DO NOTHING
            RETURNING id
        """,
    },
    "dual.organization.set_current_group": {
        "dynamic": None,
        # El grupo vigente se deriva de la pertenencia del período más reciente
        # (año y luego Enero-Abril < Mayo-Agosto < Septiembre-Diciembre); registrar
        # un período anterior no lo modifica. Parámetro: matrícula (dos veces).
        "sql": """
            UPDATE alumnos
            SET grupo_id = (
                SELECT agp.grupo_id
                FROM alumno_grupo_periodo agp
                JOIN ciclos_dual p ON p.id = agp.periodo_id
                WHERE agp.matricula = %s
                ORDER BY substring(COALESCE(p.periodo_label, p.cuatrimestre) FROM '[0-9]{4}$')::int DESC,
                         CASE split_part(COALESCE(p.periodo_label, p.cuatrimestre), ' ', 1)
                              WHEN 'Enero-Abril' THEN 1
                              WHEN 'Mayo-Agosto' THEN 2
                              ELSE 3 END DESC,
                         agp.asignado_en DESC, agp.id DESC
                LIMIT 1)
            WHERE matricula = %s
        """,
    },
    "dual.organization.history": {
        "dynamic": None,
        "sql": """
            SELECT agp.id, agp.periodo_id, p.periodo_label,
                   agp.grupo_id, g.nomenclatura, g.cuatrimestre,
                   c.codigo AS carrera_codigo, c.nombre AS carrera,
                   agp.asignado_en
            FROM alumno_grupo_periodo agp
            JOIN ciclos_dual p ON p.id = agp.periodo_id
            JOIN grupos g ON g.id = agp.grupo_id
            JOIN carreras c ON c.id = g.carrera_id
            WHERE agp.matricula = %s
            ORDER BY p.fecha_inicio DESC NULLS LAST, agp.asignado_en DESC
        """,
    },
    "dual.organization.source_members": {
        "dynamic": None,
        "sql": """
            SELECT agp.matricula, a.nombre
            FROM alumno_grupo_periodo agp
            JOIN alumnos a ON a.matricula = agp.matricula
            WHERE agp.grupo_id = %s AND agp.periodo_id = %s
              AND (%s::text[] IS NULL OR agp.matricula = ANY(%s))
            ORDER BY a.nombre
        """,
    },
}
