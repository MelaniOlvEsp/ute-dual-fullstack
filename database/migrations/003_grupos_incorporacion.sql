-- C03: catálogo institucional, historia de grupo e incorporación con fechas.
-- Idempotente sobre el esquema canónico C01. No borra ni reasigna historia.
BEGIN;

SELECT pg_advisory_xact_lock(19863);

DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM public.grupos
    WHERE carrera NOT IN (
      'ING.NME TEC DE LA INFORMACIÓN E INNOVACION DIGITAL',
      'ING. NME LOGISTICA',
      'LIC. NME MERCADOTECNIA'
    )
  ) THEN
    RAISE EXCEPTION 'C03 detectó grupos de carreras fuera de TIC, Logística y Mercadotecnia. No se modificaron datos.';
  END IF;

  IF EXISTS (
    SELECT matricula FROM public.alumnos_dual
    WHERE activo IS TRUE GROUP BY matricula HAVING count(*) > 1
  ) THEN
    RAISE EXCEPTION 'C03 detectó más de una incorporación activa por alumno. Resolver antes de migrar.';
  END IF;
END;
$$;

CREATE TABLE IF NOT EXISTS public.carreras (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  codigo varchar(3) NOT NULL UNIQUE,
  nombre text NOT NULL UNIQUE,
  activo boolean NOT NULL DEFAULT TRUE,
  CONSTRAINT carreras_codigo_c03 CHECK (codigo IN ('TII','LOG','MER')),
  CONSTRAINT carreras_nombre_c03 CHECK (nombre IN (
    'ING.NME TEC DE LA INFORMACIÓN E INNOVACION DIGITAL',
    'ING. NME LOGISTICA',
    'LIC. NME MERCADOTECNIA'
  ))
);

INSERT INTO public.carreras (codigo, nombre, activo) VALUES
 ('TII', 'ING.NME TEC DE LA INFORMACIÓN E INNOVACION DIGITAL', TRUE),
 ('LOG', 'ING. NME LOGISTICA', TRUE),
 ('MER', 'LIC. NME MERCADOTECNIA', TRUE)
ON CONFLICT (codigo) DO UPDATE SET nombre = EXCLUDED.nombre, activo = TRUE;

ALTER TABLE public.grupos ADD COLUMN IF NOT EXISTS carrera_id uuid;
UPDATE public.grupos g
SET carrera_id = c.id
FROM public.carreras c
WHERE g.carrera = c.nombre AND g.carrera_id IS NULL;
ALTER TABLE public.grupos ALTER COLUMN carrera_id SET NOT NULL;

DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'grupos_carrera_id_fkey') THEN
    ALTER TABLE public.grupos ADD CONSTRAINT grupos_carrera_id_fkey
      FOREIGN KEY (carrera_id) REFERENCES public.carreras(id);
  END IF;
END;
$$;

ALTER TABLE public.grupos DROP CONSTRAINT IF EXISTS grupos_carrera_check;
ALTER TABLE public.grupos ADD CONSTRAINT grupos_carrera_check CHECK (carrera IN (
  'ING.NME TEC DE LA INFORMACIÓN E INNOVACION DIGITAL',
  'ING. NME LOGISTICA',
  'LIC. NME MERCADOTECNIA'
));

ALTER TABLE public.grupos DROP COLUMN IF EXISTS nomenclatura;
ALTER TABLE public.grupos ADD COLUMN nomenclatura text GENERATED ALWAYS AS (
  plan::text ||
  CASE carrera
    WHEN 'ING.NME TEC DE LA INFORMACIÓN E INNOVACION DIGITAL' THEN 'TII'
    WHEN 'ING. NME LOGISTICA' THEN 'LOG'
    WHEN 'LIC. NME MERCADOTECNIA' THEN 'MER'
    ELSE 'ERR'
  END || '-' || zona::text || '-' ||
  CASE modalidad
    WHEN 'bis' THEN 'B'
    WHEN 'intensivo' THEN 'I'
    WHEN 'mixta' THEN 'M'
    WHEN 'despresurizada' THEN 'D'
    ELSE 'ERR'
  END || '-' || cuatrimestre::text || letra::text
) STORED;

CREATE TABLE IF NOT EXISTS public.alumno_grupo_periodo (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  matricula text NOT NULL REFERENCES public.alumnos(matricula),
  grupo_id uuid NOT NULL REFERENCES public.grupos(id),
  periodo_id uuid NOT NULL REFERENCES public.ciclos_dual(id),
  asignado_por uuid REFERENCES public.usuarios(id),
  asignado_en timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT alumno_grupo_periodo_unico UNIQUE (matricula, periodo_id)
);
CREATE INDEX IF NOT EXISTS idx_agp_grupo_periodo
  ON public.alumno_grupo_periodo (grupo_id, periodo_id);

ALTER TABLE public.alumnos_dual ADD COLUMN IF NOT EXISTS fecha_inicio date;
ALTER TABLE public.alumnos_dual ADD COLUMN IF NOT EXISTS fecha_baja date;
ALTER TABLE public.alumnos_dual ADD COLUMN IF NOT EXISTS asignado_por uuid REFERENCES public.usuarios(id);
ALTER TABLE public.alumnos_dual ADD COLUMN IF NOT EXISTS baja_por uuid REFERENCES public.usuarios(id);
UPDATE public.alumnos_dual SET fecha_inicio = created_at::date WHERE fecha_inicio IS NULL;
UPDATE public.alumnos_dual
SET fecha_baja = created_at::date
WHERE activo IS FALSE AND fecha_baja IS NULL;
ALTER TABLE public.alumnos_dual ALTER COLUMN fecha_inicio SET NOT NULL;
-- La vigencia se define por fechas; el texto cuatrimestre queda solo como dato heredado.
ALTER TABLE public.alumnos_dual ALTER COLUMN cuatrimestre DROP NOT NULL;
ALTER TABLE public.alumnos_dual DROP CONSTRAINT IF EXISTS alumnos_dual_unico;
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'alumnos_dual_fechas_c03') THEN
    ALTER TABLE public.alumnos_dual ADD CONSTRAINT alumnos_dual_fechas_c03
      CHECK (fecha_baja IS NULL OR fecha_inicio <= fecha_baja);
  END IF;
END;
$$;
CREATE UNIQUE INDEX IF NOT EXISTS idx_alumnos_dual_unico_activo
  ON public.alumnos_dual (matricula) WHERE activo IS TRUE;
CREATE INDEX IF NOT EXISTS idx_alumnos_dual_historia
  ON public.alumnos_dual (matricula, fecha_inicio DESC);

ALTER TABLE public.carreras ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.alumno_grupo_periodo ENABLE ROW LEVEL SECURITY;

DO $$
DECLARE role_name text;
BEGIN
  FOREACH role_name IN ARRAY ARRAY['anon','authenticated'] LOOP
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = role_name) THEN
      EXECUTE format('REVOKE ALL ON TABLE public.carreras FROM %I', role_name);
      EXECUTE format('REVOKE ALL ON TABLE public.alumno_grupo_periodo FROM %I', role_name);
    END IF;
  END LOOP;
END;
$$;

COMMIT;
