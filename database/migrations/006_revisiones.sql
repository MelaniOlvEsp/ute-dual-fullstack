-- C06: revisiones de versiones, correcciones trazables y documentos firmados.
-- Aditiva e idempotente sobre C05. No borra ni reasigna historia.
BEGIN;

SELECT pg_advisory_xact_lock(19866);

-- Un documento es el original entregado o el firmado derivado; nunca se sustituyen entre sí.
ALTER TABLE public.documentos ADD COLUMN IF NOT EXISTS rol text NOT NULL DEFAULT 'original';
ALTER TABLE public.documentos ADD COLUMN IF NOT EXISTS firma_modo text;

ALTER TABLE public.documentos DROP CONSTRAINT IF EXISTS documentos_tamano_check;
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'documentos_rol_valido') THEN
    ALTER TABLE public.documentos ADD CONSTRAINT documentos_rol_valido
      CHECK (rol IN ('original', 'firmado'));
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'documentos_firma_modo_valido') THEN
    ALTER TABLE public.documentos ADD CONSTRAINT documentos_firma_modo_valido
      CHECK ((rol = 'firmado') = (firma_modo IS NOT NULL)
             AND (firma_modo IS NULL OR firma_modo IN ('celda', 'hoja_adicional')));
  END IF;
  -- El original conserva el límite de 10 MB (DP-08); el firmado puede crecer con la firma.
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'documentos_tamano_por_rol') THEN
    ALTER TABLE public.documentos ADD CONSTRAINT documentos_tamano_por_rol
      CHECK ((rol = 'original' AND tamano BETWEEN 1 AND 10485760)
             OR (rol = 'firmado' AND tamano BETWEEN 1 AND 20971520));
  END IF;
END;
$$;

-- Una revisión por versión recibida: la decisión, los valores validados y el firmado.
CREATE TABLE IF NOT EXISTS public.revisiones (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  version_id uuid NOT NULL UNIQUE REFERENCES public.reporte_versiones(id),
  tutor_id uuid NOT NULL REFERENCES public.usuarios(id),
  decision text NOT NULL CHECK (decision IN ('Aprobada', 'Rechazada')),
  observacion text,
  fecha_inicio date NOT NULL,
  fecha_fin date NOT NULL,
  nota smallint NOT NULL CHECK (nota BETWEEN 1 AND 10),
  documento_firmado_id uuid UNIQUE REFERENCES public.documentos(id),
  revisado_en timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT revisiones_fechas CHECK (fecha_inicio <= fecha_fin),
  CONSTRAINT revisiones_observacion_longitud
    CHECK (observacion IS NULL OR length(btrim(observacion)) BETWEEN 1 AND 1000),
  CONSTRAINT revisiones_rechazo_con_observacion
    CHECK (decision <> 'Rechazada' OR observacion IS NOT NULL),
  CONSTRAINT revisiones_firmado_solo_si_aprobada
    CHECK ((decision = 'Aprobada') = (documento_firmado_id IS NOT NULL))
);

-- Valor previo y nuevo de cada dato que el tutor corrigió (RN-15); el autor y el instante
-- son los de la revisión.
CREATE TABLE IF NOT EXISTS public.reporte_correcciones (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  revision_id uuid NOT NULL REFERENCES public.revisiones(id),
  campo text NOT NULL CHECK (campo IN ('fecha_inicio', 'fecha_fin', 'nota')),
  valor_previo text NOT NULL,
  valor_nuevo text NOT NULL CHECK (valor_nuevo <> valor_previo),
  CONSTRAINT reporte_correcciones_unica UNIQUE (revision_id, campo)
);

-- Las revisiones y sus correcciones no se modifican ni se borran.
CREATE OR REPLACE FUNCTION public.revisiones_inmutables() RETURNS trigger AS $$
BEGIN
  RAISE EXCEPTION 'Las revisiones y correcciones registradas no se modifican ni se eliminan';
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS revisiones_inmutables ON public.revisiones;
CREATE TRIGGER revisiones_inmutables
  BEFORE UPDATE OR DELETE ON public.revisiones
  FOR EACH ROW EXECUTE FUNCTION public.revisiones_inmutables();

DROP TRIGGER IF EXISTS correcciones_inmutables ON public.reporte_correcciones;
CREATE TRIGGER correcciones_inmutables
  BEFORE UPDATE OR DELETE ON public.reporte_correcciones
  FOR EACH ROW EXECUTE FUNCTION public.revisiones_inmutables();

CREATE INDEX IF NOT EXISTS idx_revisiones_tutor ON public.revisiones (tutor_id);

ALTER TABLE public.revisiones ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.reporte_correcciones ENABLE ROW LEVEL SECURITY;

DO $$
DECLARE role_name text;
BEGIN
  FOREACH role_name IN ARRAY ARRAY['anon','authenticated'] LOOP
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = role_name) THEN
      EXECUTE format('REVOKE ALL ON TABLE public.revisiones FROM %I', role_name);
      EXECUTE format('REVOKE ALL ON TABLE public.reporte_correcciones FROM %I', role_name);
    END IF;
  END LOOP;
END;
$$;

COMMIT;
