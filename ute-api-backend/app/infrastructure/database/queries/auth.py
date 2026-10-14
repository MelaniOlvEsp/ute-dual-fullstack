"""Consultas parametrizadas de identidad sin verificación de correo."""

QUERIES = {
    "auth.student_allowed": {"dynamic": None, "sql": """
        SELECT matricula FROM alumnos
        WHERE matricula = %s AND LOWER(email) = %s
          AND registro_dual_autorizado = TRUE
    """},
    "auth.account_exists": {"dynamic": None, "sql":
        "SELECT id FROM usuarios WHERE LOWER(email) = %s"},
    "auth.insert_student": {"dynamic": None, "sql": """
        INSERT INTO usuarios
            (email, password_hash, roles, matricula,
             must_change_password)
        VALUES (%s, %s, '{"alumno":true}'::jsonb, %s, FALSE)
    """},
    "auth.login": {"dynamic": None, "sql": """
        SELECT u.id, u.email, u.password_hash, u.roles, u.matricula,
               u.must_change_password, u.credential_version,
               u.login_attempts, u.login_locked_until,
               COALESCE(a.nombre, u.nombre) AS nombre, g.turno,
               g.id AS grupo_id, g.nomenclatura, g.cuatrimestre,
               g.carrera, g.modalidad,
               COALESCE(ad.activo, FALSE) AS dual_activo
        FROM usuarios u
        LEFT JOIN alumnos a ON a.matricula = u.matricula
        LEFT JOIN grupos g ON g.id = a.grupo_id
        LEFT JOIN LATERAL (
            SELECT activo FROM alumnos_dual
            WHERE matricula = u.matricula AND activo = TRUE
            ORDER BY created_at DESC, id DESC LIMIT 1
        ) ad ON TRUE
        WHERE LOWER(u.email) = %s AND u.activo = TRUE
    """},
    "auth.login_failed": {"dynamic": None, "sql": """
        UPDATE usuarios SET login_attempts = %s,
            login_locked_until = %s WHERE LOWER(email) = %s
    """},
    "auth.login_reset": {"dynamic": None, "sql": """
        UPDATE usuarios SET login_attempts = 0,
            login_locked_until = NULL WHERE LOWER(email) = %s
    """},
    "auth.me": {"dynamic": None, "sql": """
        SELECT u.id, u.email, u.roles, u.matricula, u.must_change_password,
               COALESCE(a.nombre, u.nombre) AS nombre, g.turno,
               g.id AS grupo_id, g.nomenclatura, g.cuatrimestre,
               g.carrera, g.modalidad, e.nombre AS empresa,
               COALESCE(ad.activo, FALSE) AS dual_activo
        FROM usuarios u
        LEFT JOIN alumnos a ON a.matricula = u.matricula
        LEFT JOIN grupos g ON g.id = a.grupo_id
        LEFT JOIN LATERAL (
            SELECT activo, empresa_id FROM alumnos_dual
            WHERE matricula = u.matricula AND activo = TRUE
            ORDER BY created_at DESC, id DESC LIMIT 1
        ) ad ON TRUE
        LEFT JOIN empresas e ON e.id = ad.empresa_id
        WHERE LOWER(u.email) = %s AND u.activo = TRUE
    """},
    "auth.security_state": {"dynamic": None, "sql": """
        SELECT roles, must_change_password, credential_version
        FROM usuarios WHERE id = %s AND LOWER(email) = %s AND activo = TRUE
    """},
    "auth.password_current": {"dynamic": None, "sql":
        "SELECT password_hash FROM usuarios WHERE id = %s"},
    "auth.password_change": {"dynamic": None, "sql": """
        UPDATE usuarios SET password_hash = %s,
            must_change_password = FALSE,
            credential_version = credential_version + 1,
            login_attempts = 0, login_locked_until = NULL
        WHERE id = %s
    """},
    "auth.create_tutor": {"dynamic": None, "sql": """
        INSERT INTO usuarios
            (nombre, email, password_hash, roles,
             matricula, must_change_password)
        VALUES (%s, %s, %s, '{"tutor_academico":true}'::jsonb,
                NULL, TRUE)
    """},
    "auth.list_tutors": {"dynamic": None, "sql": """
        SELECT id, nombre, email, roles FROM usuarios
        WHERE activo = TRUE AND COALESCE((roles->>'tutor_academico')::boolean, FALSE)
        ORDER BY nombre
    """},
    "auth.delete_tutor": {"dynamic": None, "sql": """
        UPDATE usuarios SET activo = FALSE,
            credential_version = credential_version + 1
        WHERE id = %s AND activo = TRUE
          AND COALESCE((roles->>'tutor_academico')::boolean, FALSE)
        RETURNING id
    """},
    "auth.student_for_reset": {"dynamic": None, "sql": """
        SELECT u.id, u.email FROM usuarios u JOIN alumnos a
          ON a.matricula = u.matricula
        WHERE u.matricula = %s AND u.activo = TRUE
          AND a.registro_dual_autorizado = TRUE
          AND COALESCE((u.roles->>'alumno')::boolean, FALSE)
        FOR UPDATE OF u
    """},
    "auth.password_temp": {"dynamic": None, "sql": """
        UPDATE usuarios SET password_hash = %s,
          must_change_password = TRUE,
          credential_version = credential_version + 1,
          login_attempts = 0, login_locked_until = NULL
        WHERE id = %s
    """},
}
