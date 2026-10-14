-- Ejecutar tras un respaldo y antes de desplegar el nuevo código.
BEGIN;
ALTER TABLE alumnos
    ADD COLUMN IF NOT EXISTS registro_dual_autorizado boolean
    NOT NULL DEFAULT FALSE;
ALTER TABLE usuarios
    ADD COLUMN IF NOT EXISTS credential_version integer
    NOT NULL DEFAULT 0;

-- Los alumnos históricos no reciben acceso nuevo de forma automática.
-- Un tutor debe volver a autorizar su matrícula desde el módulo de grupos.
-- Convertir explícitamente los roles antiguos tras revisar cada cuenta:
-- UPDATE usuarios SET roles = '{"tutor_academico":true}'::jsonb
-- WHERE email = 'tutor.real@ute.edu.mx';

CREATE TABLE IF NOT EXISTS tutor_firmas (
    tutor_id uuid PRIMARY KEY REFERENCES usuarios(id) ON DELETE CASCADE,
    imagen bytea NOT NULL,
    content_type varchar(25) NOT NULL,
    actualizada_en timestamptz NOT NULL DEFAULT NOW()
);
ALTER TABLE reportes_dual
    ADD COLUMN IF NOT EXISTS revisado_por uuid REFERENCES usuarios(id),
    ADD COLUMN IF NOT EXISTS revisado_en timestamptz;

-- Reducir a tres roles y no conceder privilegios por conversión implícita.
UPDATE usuarios SET roles = (
    CASE
        WHEN COALESCE((roles->>'tutor_academico')::boolean, FALSE)
            THEN '{"tutor_academico":true}'::jsonb
        WHEN COALESCE((roles->>'coordinador_dual')::boolean, FALSE)
            THEN '{"coordinador_dual":true}'::jsonb
        WHEN COALESCE((roles->>'alumno')::boolean, FALSE)
             AND matricula IS NOT NULL
            THEN '{"alumno":true}'::jsonb
        ELSE '{}'::jsonb
    END
);
COMMIT;
