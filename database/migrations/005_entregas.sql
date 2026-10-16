-- C05: entregas por obligación, versiones inmutables y documentos privados.
-- Aditiva e idempotente sobre C04. No borra ni reasigna historia.
BEGIN;

SELECT pg_advisory_xact_lock(19866);

-- Documentos: la clave la genera el servidor; nunca se guarda una ruta ni un nombre del cliente.
CREATE TABLE IF NOT EXISTS public.documentos (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  clave text NOT NULL UNIQUE,
  tipo text NOT NULL DEFAULT 'application/pdf' CHECK (tipo = 'application/pdf'),
  tamano integer NOT NULL CHECK (tamano BETWEEN 1 AND 10485760),
  sha256 char(64) NOT NULL CHECK (sha256 ~ '^[0-9a-f]{64}$'),
  paginas integer NOT NULL CHECK (paginas >= 1),
  subido_por uuid REFERENCES public.usuarios(id),
  created_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT documentos_clave_formato CHECK (clave ~ '^[0-9a-f]{32}\.pdf$')
);

-- Reporte lógico: uno por obligación. Las columnas heredadas se mantienen sincronizadas
-- con la versión vigente mientras C06 migra la revisión.
ALTER TABLE public.reportes_dual
  ADD COLUMN IF NOT EXISTS obligacion_id uuid REFERENCES public.obligaciones_semanales(id);
CREATE UNIQUE INDEX IF NOT EXISTS idx_reportes_dual_obligacion
  ON public.reportes_dual (obligacion_id) WHERE obligacion_id IS NOT NULL;

-- Sin techo de 18 semanas ni unicidad por semana textual (RN-07): la identidad es la obligación.
ALTER TABLE public.reportes_dual DROP CONSTRAINT IF EXISTS reportes_dual_semana_check;
ALTER TABLE public.reportes_dual DROP CONSTRAINT IF EXISTS reportes_dual_unico;
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'reportes_dual_semana_positiva') THEN
    ALTER TABLE public.reportes_dual ADD CONSTRAINT reportes_dual_semana_positiva CHECK (semana >= 1);
  END IF;
  -- Nota entera (RN-12) para filas nuevas; las heredadas no se validan retroactivamente.
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'reportes_dual_nota_entera') THEN
    ALTER TABLE public.reportes_dual ADD CONSTRAINT reportes_dual_nota_entera
      CHECK (calificacion_alumno = trunc(calificacion_alumno)) NOT VALID;
  END IF;
END;
$$;

CREATE TABLE IF NOT EXISTS public.reporte_versiones (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  reporte_id uuid NOT NULL REFERENCES public.reportes_dual(id),
  numero integer NOT NULL CHECK (numero >= 1),
  fecha_inicio date NOT NULL,
  fecha_fin date NOT NULL,
  nota smallint NOT NULL CHECK (nota BETWEEN 1 AND 10),
  documento_id uuid NOT NULL REFERENCES public.documentos(id),
  recibido_en timestamptz NOT NULL DEFAULT now(),
  recibido_por uuid REFERENCES public.usuarios(id),
  -- Decisión sobre esta versión; se copia aquí al reenviar para conservar la historia.
  decision text CHECK (decision IN ('Aprobada','Rechazada')),
  nota_revision text,
  revisado_por uuid REFERENCES public.usuarios(id),
  revisado_en timestamptz,
  CONSTRAINT reporte_versiones_unica UNIQUE (reporte_id, numero),
  CONSTRAINT reporte_versiones_fechas CHECK (fecha_inicio <= fecha_fin)
);
CREATE INDEX IF NOT EXISTS idx_reporte_versiones_documento ON public.reporte_versiones (documento_id);

-- Las versiones recibidas son inmutables: solo se puede registrar la decisión una vez.
CREATE OR REPLACE FUNCTION public.reporte_versiones_inmutables() RETURNS trigger AS $$
BEGIN
  IF TG_OP = 'DELETE' THEN
    RAISE EXCEPTION 'Las versiones de reporte no se eliminan';
  END IF;
  IF NEW.reporte_id IS DISTINCT FROM OLD.reporte_id
     OR NEW.numero IS DISTINCT FROM OLD.numero
     OR NEW.fecha_inicio IS DISTINCT FROM OLD.fecha_inicio
     OR NEW.fecha_fin IS DISTINCT FROM OLD.fecha_fin
     OR NEW.nota IS DISTINCT FROM OLD.nota
     OR NEW.documento_id IS DISTINCT FROM OLD.documento_id
     OR NEW.recibido_en IS DISTINCT FROM OLD.recibido_en
     OR NEW.recibido_por IS DISTINCT FROM OLD.recibido_por THEN
    RAISE EXCEPTION 'Una versión recibida no se modifica';
  END IF;
  IF OLD.decision IS NOT NULL AND (
       NEW.decision IS DISTINCT FROM OLD.decision
       OR NEW.nota_revision IS DISTINCT FROM OLD.nota_revision
       OR NEW.revisado_por IS DISTINCT FROM OLD.revisado_por
       OR NEW.revisado_en IS DISTINCT FROM OLD.revisado_en) THEN
    RAISE EXCEPTION 'La decisión de una versión ya está registrada';
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS reporte_versiones_inmutables ON public.reporte_versiones;
CREATE TRIGGER reporte_versiones_inmutables
  BEFORE UPDATE OR DELETE ON public.reporte_versiones
  FOR EACH ROW EXECUTE FUNCTION public.reporte_versiones_inmutables();

ALTER TABLE public.documentos ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.reporte_versiones ENABLE ROW LEVEL SECURITY;

DO $$
DECLARE role_name text;
BEGIN
  FOREACH role_name IN ARRAY ARRAY['anon','authenticated'] LOOP
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = role_name) THEN
      EXECUTE format('REVOKE ALL ON TABLE public.documentos FROM %I', role_name);
      EXECUTE format('REVOKE ALL ON TABLE public.reporte_versiones FROM %I', role_name);
    END IF;
  END LOOP;
END;
$$;

COMMIT;
