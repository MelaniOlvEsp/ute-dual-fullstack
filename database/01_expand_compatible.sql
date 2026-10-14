-- Expansión no destructiva del esquema original; incluye campos del proceso v2.
-- Mantiene los nombres de columnas consumidos por la API.
BEGIN;
SET LOCAL lock_timeout = '5s';

ALTER TABLE public.alumnos
 ADD COLUMN IF NOT EXISTS registro_dual_autorizado boolean NOT NULL DEFAULT FALSE;
ALTER TABLE public.usuarios
 ADD COLUMN IF NOT EXISTS credential_version integer NOT NULL DEFAULT 0,
 ADD COLUMN IF NOT EXISTS activo boolean NOT NULL DEFAULT TRUE;
ALTER TABLE public.reportes_dual
 ADD COLUMN IF NOT EXISTS revisado_por uuid REFERENCES public.usuarios(id),
 ADD COLUMN IF NOT EXISTS revisado_en timestamptz;

CREATE TABLE IF NOT EXISTS public.tutor_firmas (
 tutor_id uuid PRIMARY KEY REFERENCES public.usuarios(id) ON DELETE CASCADE,
 imagen bytea NOT NULL,
 content_type varchar(25) NOT NULL,
 actualizada_en timestamptz NOT NULL DEFAULT now()
);

-- Comprobar luego los valores históricos antes de validar restricciones.
ALTER TABLE public.reportes_dual
 ADD CONSTRAINT reportes_dual_semana_rango CHECK (semana BETWEEN 1 AND 18)
 NOT VALID;
ALTER TABLE public.reportes_dual
 ADD CONSTRAINT reportes_dual_fechas_ordenadas
 CHECK (fecha_inicio IS NULL OR fecha_fin IS NULL OR fecha_inicio <= fecha_fin)
 NOT VALID;
ALTER TABLE public.ciclos_dual
 ADD CONSTRAINT ciclos_dual_estados_excluyentes
 CHECK (NOT (abierto IS TRUE AND cerrado IS TRUE)) NOT VALID;
ALTER TABLE public.usuarios
 ADD CONSTRAINT usuarios_credential_version_no_negativo
 CHECK (credential_version >= 0) NOT VALID;
ALTER TABLE public.tutor_firmas
 ADD CONSTRAINT tutor_firmas_contenido_valido
 CHECK (content_type IN ('image/png','image/jpeg')
        AND octet_length(imagen) BETWEEN 1 AND 1048576) NOT VALID;

COMMIT;

