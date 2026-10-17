-- C08: registro de los paquetes de archivo (ZIP) generados por el tutor o por el alumno.
-- Aditiva e idempotente sobre C07. El registro no se modifica ni se borra: es la evidencia que
-- habilitará la depuración de archivos de C08B (DP-14). No borra ni reasigna historia.
BEGIN;

SELECT pg_advisory_xact_lock(19866);

CREATE TABLE IF NOT EXISTS public.paquetes_archivo (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  alcance text NOT NULL CHECK (alcance IN ('alumno', 'carrera')),
  periodo_id uuid NOT NULL REFERENCES public.ciclos_dual(id),
  matricula text REFERENCES public.alumnos(matricula),
  carrera text,
  rol text NOT NULL CHECK (rol IN ('tutor', 'alumno')),
  generado_por uuid NOT NULL REFERENCES public.usuarios(id),
  generado_en timestamptz NOT NULL DEFAULT now(),
  manifiesto_sha256 char(64) NOT NULL CHECK (manifiesto_sha256 ~ '^[0-9a-f]{64}$'),
  alumnos integer NOT NULL CHECK (alumnos >= 0),
  archivos integer NOT NULL CHECK (archivos >= 0),
  bytes bigint NOT NULL CHECK (bytes >= 0),
  CONSTRAINT paquetes_alcance_coherente CHECK (
    (alcance = 'alumno' AND matricula IS NOT NULL AND carrera IS NULL)
    OR (alcance = 'carrera' AND carrera IS NOT NULL AND matricula IS NULL)),
  CONSTRAINT paquetes_alumno_solo_alcance_alumno CHECK (rol = 'tutor' OR alcance = 'alumno')
);

CREATE INDEX IF NOT EXISTS idx_paquetes_periodo ON public.paquetes_archivo (periodo_id, generado_en);
CREATE INDEX IF NOT EXISTS idx_paquetes_matricula ON public.paquetes_archivo (matricula) WHERE matricula IS NOT NULL;

CREATE OR REPLACE FUNCTION public.paquetes_inmutables() RETURNS trigger AS $$
BEGIN
  RAISE EXCEPTION 'El registro de paquetes de archivo no se modifica ni se elimina';
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS paquetes_inmutables ON public.paquetes_archivo;
CREATE TRIGGER paquetes_inmutables
  BEFORE UPDATE OR DELETE ON public.paquetes_archivo
  FOR EACH ROW EXECUTE FUNCTION public.paquetes_inmutables();

ALTER TABLE public.paquetes_archivo ENABLE ROW LEVEL SECURITY;

DO $$
DECLARE role_name text;
BEGIN
  FOREACH role_name IN ARRAY ARRAY['anon','authenticated'] LOOP
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = role_name) THEN
      EXECUTE format('REVOKE ALL ON TABLE public.paquetes_archivo FROM %I', role_name);
    END IF;
  END LOOP;
END;
$$;

COMMIT;
