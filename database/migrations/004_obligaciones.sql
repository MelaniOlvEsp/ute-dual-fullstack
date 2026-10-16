-- C04: períodos sin solapamiento y obligaciones semanales por incorporación.
-- Aditiva e idempotente sobre C03. No borra ni reasigna historia.
BEGIN;

SELECT pg_advisory_xact_lock(19864);

DO $$
BEGIN
  IF EXISTS (
    SELECT 1
    FROM public.ciclos_dual a
    JOIN public.ciclos_dual b ON a.id < b.id
    WHERE a.fecha_inicio IS NOT NULL AND a.fecha_fin IS NOT NULL
      AND b.fecha_inicio IS NOT NULL AND b.fecha_fin IS NOT NULL
      AND daterange(a.fecha_inicio, a.fecha_fin, '[]') && daterange(b.fecha_inicio, b.fecha_fin, '[]')
  ) THEN
    RAISE EXCEPTION 'C04 detectó períodos con fechas solapadas. Corregir sus fechas antes de migrar; no se modificaron datos.';
  END IF;
END;
$$;

DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ciclos_dual_sin_solape') THEN
    ALTER TABLE public.ciclos_dual ADD CONSTRAINT ciclos_dual_sin_solape
      EXCLUDE USING gist (daterange(fecha_inicio, fecha_fin, '[]') WITH &&)
      WHERE (fecha_inicio IS NOT NULL AND fecha_fin IS NOT NULL);
  END IF;
END;
$$;

CREATE TABLE IF NOT EXISTS public.obligaciones_semanales (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  incorporacion_id uuid NOT NULL REFERENCES public.alumnos_dual(id),
  semana_inicio date NOT NULL,
  semana_fin date NOT NULL,
  inicio_efectivo date NOT NULL,
  fin_efectivo date NOT NULL,
  parcial boolean NOT NULL,
  periodo_id uuid REFERENCES public.ciclos_dual(id),
  created_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT obligaciones_semanales_unica UNIQUE (incorporacion_id, semana_inicio),
  CONSTRAINT obligaciones_semanales_lunes CHECK (EXTRACT(ISODOW FROM semana_inicio) = 1),
  CONSTRAINT obligaciones_semanales_domingo CHECK (semana_fin = semana_inicio + 6),
  CONSTRAINT obligaciones_semanales_efectivo CHECK (
    inicio_efectivo >= semana_inicio AND fin_efectivo <= semana_fin
    AND inicio_efectivo <= fin_efectivo)
);
CREATE INDEX IF NOT EXISTS idx_obligaciones_periodo ON public.obligaciones_semanales (periodo_id);
CREATE INDEX IF NOT EXISTS idx_obligaciones_semana_fin ON public.obligaciones_semanales (semana_fin);

ALTER TABLE public.obligaciones_semanales ENABLE ROW LEVEL SECURITY;

DO $$
DECLARE role_name text;
BEGIN
  FOREACH role_name IN ARRAY ARRAY['anon','authenticated'] LOOP
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = role_name) THEN
      EXECUTE format('REVOKE ALL ON TABLE public.obligaciones_semanales FROM %I', role_name);
    END IF;
  END LOOP;
END;
$$;

COMMIT;
