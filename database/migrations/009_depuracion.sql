-- C08B: depuración de los archivos PDF de un período tras guardar el paquete ZIP (DP-14).
-- Aditiva e idempotente sobre C08. Solo se eliminan archivos físicos: las filas de `documentos` se
-- conservan con su clave, tamaño y SHA-256 originales, marcadas como archivadas; notas, promedios,
-- versiones, revisiones, correcciones y resultados congelados no se tocan.
BEGIN;

SELECT pg_advisory_xact_lock(19867);

CREATE TABLE IF NOT EXISTS public.purgas_archivo (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  periodo_id uuid NOT NULL REFERENCES public.ciclos_dual(id),
  alcance text NOT NULL CHECK (alcance IN ('alumno', 'carrera')),
  matricula text REFERENCES public.alumnos(matricula),
  carrera text,
  paquete_id uuid NOT NULL REFERENCES public.paquetes_archivo(id),
  manifiesto_sha256 char(64) NOT NULL CHECK (manifiesto_sha256 ~ '^[0-9a-f]{64}$'),
  solicitada_por uuid NOT NULL REFERENCES public.usuarios(id),
  solicitada_en timestamptz NOT NULL DEFAULT now(),
  ejecutar_en timestamptz NOT NULL,
  estado text NOT NULL DEFAULT 'programada' CHECK (estado IN ('programada', 'cancelada', 'completada')),
  cancelada_por uuid REFERENCES public.usuarios(id),
  cancelada_en timestamptz,
  completada_en timestamptz,
  archivos integer NOT NULL CHECK (archivos >= 0),
  bytes bigint NOT NULL CHECK (bytes >= 0),
  intentos integer NOT NULL DEFAULT 0 CHECK (intentos >= 0),
  ultimo_error text,
  CONSTRAINT purgas_alcance_coherente CHECK (
    (alcance = 'alumno' AND matricula IS NOT NULL AND carrera IS NULL)
    OR (alcance = 'carrera' AND carrera IS NOT NULL AND matricula IS NULL)),
  CONSTRAINT purgas_ejecucion_posterior CHECK (ejecutar_en >= solicitada_en),
  CONSTRAINT purgas_estado_coherente CHECK (
    (estado = 'programada' AND cancelada_en IS NULL AND cancelada_por IS NULL AND completada_en IS NULL)
    OR (estado = 'cancelada' AND cancelada_en IS NOT NULL AND cancelada_por IS NOT NULL AND completada_en IS NULL)
    OR (estado = 'completada' AND completada_en IS NOT NULL AND cancelada_en IS NULL AND cancelada_por IS NULL))
);

-- Una sola depuración programada por período y alcance.
CREATE UNIQUE INDEX IF NOT EXISTS idx_purgas_programada_unica
  ON public.purgas_archivo (periodo_id, alcance, COALESCE(matricula, ''), COALESCE(carrera, ''))
  WHERE estado = 'programada';
CREATE INDEX IF NOT EXISTS idx_purgas_vencimiento ON public.purgas_archivo (ejecutar_en) WHERE estado = 'programada';
CREATE INDEX IF NOT EXISTS idx_purgas_periodo ON public.purgas_archivo (periodo_id, solicitada_en);

-- Estados de un documento: normal (sin purga), en depuración (purga programada, archivo presente) y
-- archivado (archivo eliminado; la fila, la clave, el tamaño y el hash se conservan como evidencia).
ALTER TABLE public.documentos ADD COLUMN IF NOT EXISTS purga_id uuid REFERENCES public.purgas_archivo(id);
ALTER TABLE public.documentos ADD COLUMN IF NOT EXISTS archivado_en timestamptz;
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'documentos_archivado_con_purga') THEN
    ALTER TABLE public.documentos ADD CONSTRAINT documentos_archivado_con_purga
      CHECK (archivado_en IS NULL OR purga_id IS NOT NULL);
  END IF;
END;
$$;
CREATE INDEX IF NOT EXISTS idx_documentos_purga ON public.documentos (purga_id) WHERE purga_id IS NOT NULL;

CREATE OR REPLACE FUNCTION public.purgas_protegidas() RETURNS trigger AS $$
BEGIN
  IF TG_OP = 'DELETE' THEN
    RAISE EXCEPTION 'El registro de purgas de archivo no se elimina';
  END IF;
  IF OLD.estado <> 'programada' THEN
    RAISE EXCEPTION 'Una purga cancelada o completada no se modifica';
  END IF;
  IF NEW.id IS DISTINCT FROM OLD.id OR NEW.periodo_id IS DISTINCT FROM OLD.periodo_id
     OR NEW.alcance IS DISTINCT FROM OLD.alcance OR NEW.matricula IS DISTINCT FROM OLD.matricula
     OR NEW.carrera IS DISTINCT FROM OLD.carrera OR NEW.paquete_id IS DISTINCT FROM OLD.paquete_id
     OR NEW.manifiesto_sha256 IS DISTINCT FROM OLD.manifiesto_sha256
     OR NEW.solicitada_por IS DISTINCT FROM OLD.solicitada_por
     OR NEW.solicitada_en IS DISTINCT FROM OLD.solicitada_en
     OR NEW.ejecutar_en IS DISTINCT FROM OLD.ejecutar_en
     OR NEW.archivos IS DISTINCT FROM OLD.archivos OR NEW.bytes IS DISTINCT FROM OLD.bytes THEN
    RAISE EXCEPTION 'Los datos de una purga programada no se modifican';
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS purgas_protegidas ON public.purgas_archivo;
CREATE TRIGGER purgas_protegidas
  BEFORE UPDATE OR DELETE ON public.purgas_archivo
  FOR EACH ROW EXECUTE FUNCTION public.purgas_protegidas();

CREATE OR REPLACE FUNCTION public.documentos_protegidos() RETURNS trigger AS $$
BEGIN
  IF (to_jsonb(NEW) - 'purga_id' - 'archivado_en') IS DISTINCT FROM (to_jsonb(OLD) - 'purga_id' - 'archivado_en') THEN
    RAISE EXCEPTION 'Un documento no se modifica: solo cambia su estado de archivo';
  END IF;
  IF OLD.archivado_en IS NOT NULL
     AND (NEW.archivado_en IS DISTINCT FROM OLD.archivado_en OR NEW.purga_id IS DISTINCT FROM OLD.purga_id) THEN
    RAISE EXCEPTION 'Un documento archivado no se restablece';
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS documentos_protegidos ON public.documentos;
CREATE TRIGGER documentos_protegidos
  BEFORE UPDATE ON public.documentos
  FOR EACH ROW EXECUTE FUNCTION public.documentos_protegidos();

ALTER TABLE public.purgas_archivo ENABLE ROW LEVEL SECURITY;

DO $$
DECLARE role_name text;
BEGIN
  FOREACH role_name IN ARRAY ARRAY['anon','authenticated'] LOOP
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = role_name) THEN
      EXECUTE format('REVOKE ALL ON TABLE public.purgas_archivo FROM %I', role_name);
    END IF;
  END LOOP;
END;
$$;

COMMIT;
