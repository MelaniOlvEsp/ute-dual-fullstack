-- C07: finalización de la evaluación y resultado congelado por alumno y período.
-- Aditiva e idempotente sobre C06. No borra ni reasigna historia. El cierre de recepción reutiliza
-- `abierto`, `cerrado`, `cerrado_por` y `cerrado_at` de `ciclos_dual`.
BEGIN;

SELECT pg_advisory_xact_lock(19866);

ALTER TABLE public.ciclos_dual ADD COLUMN IF NOT EXISTS evaluacion_finalizada_en timestamptz;
ALTER TABLE public.ciclos_dual
  ADD COLUMN IF NOT EXISTS evaluacion_finalizada_por uuid REFERENCES public.usuarios(id);

DO $$
BEGIN
  -- No se finaliza un período cuya recepción no se cerró (RN-20).
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ciclos_dual_finaliza_tras_cierre') THEN
    ALTER TABLE public.ciclos_dual ADD CONSTRAINT ciclos_dual_finaliza_tras_cierre
      CHECK (evaluacion_finalizada_en IS NULL OR cerrado);
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ciclos_dual_finaliza_con_autor') THEN
    ALTER TABLE public.ciclos_dual ADD CONSTRAINT ciclos_dual_finaliza_con_autor
      CHECK ((evaluacion_finalizada_en IS NULL) = (evaluacion_finalizada_por IS NULL));
  END IF;
END;
$$;

-- Resultado final por alumno y período: suma y cantidad exactas y promedio con dos decimales
-- (HALF_UP, DP-11). Sin aprobados el promedio es nulo ("Sin calificación"), nunca 0.00.
CREATE TABLE IF NOT EXISTS public.cierres_alumno_periodo (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  periodo_id uuid NOT NULL REFERENCES public.ciclos_dual(id),
  matricula text NOT NULL REFERENCES public.alumnos(matricula),
  suma integer NOT NULL CHECK (suma >= 0),
  cantidad integer NOT NULL CHECK (cantidad >= 0),
  promedio numeric(4, 2) CHECK (promedio BETWEEN 1 AND 10),
  cerrado_en timestamptz NOT NULL DEFAULT now(),
  cerrado_por uuid NOT NULL REFERENCES public.usuarios(id),
  CONSTRAINT cierres_alumno_periodo_unico UNIQUE (periodo_id, matricula),
  CONSTRAINT cierres_promedio_si_hay_aprobados CHECK ((cantidad = 0) = (promedio IS NULL)),
  CONSTRAINT cierres_suma_coherente CHECK (cantidad = 0 AND suma = 0 OR suma BETWEEN cantidad AND cantidad * 10)
);

-- Reportes y notas que componen cada resultado (auditable y reproducible).
CREATE TABLE IF NOT EXISTS public.cierre_alumno_notas (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  cierre_id uuid NOT NULL REFERENCES public.cierres_alumno_periodo(id),
  reporte_id uuid NOT NULL REFERENCES public.reportes_dual(id),
  nota smallint NOT NULL CHECK (nota BETWEEN 1 AND 10),
  CONSTRAINT cierre_alumno_notas_unica UNIQUE (cierre_id, reporte_id)
);

-- El resultado congelado no se modifica ni se borra.
CREATE OR REPLACE FUNCTION public.cierres_inmutables() RETURNS trigger AS $$
BEGIN
  RAISE EXCEPTION 'El resultado final de un período no se modifica ni se elimina';
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS cierres_alumno_inmutables ON public.cierres_alumno_periodo;
CREATE TRIGGER cierres_alumno_inmutables
  BEFORE UPDATE OR DELETE ON public.cierres_alumno_periodo
  FOR EACH ROW EXECUTE FUNCTION public.cierres_inmutables();

DROP TRIGGER IF EXISTS cierre_notas_inmutables ON public.cierre_alumno_notas;
CREATE TRIGGER cierre_notas_inmutables
  BEFORE UPDATE OR DELETE ON public.cierre_alumno_notas
  FOR EACH ROW EXECUTE FUNCTION public.cierres_inmutables();

-- Un período finalizado no vuelve a abrirse ni cambia: protege el resultado congelado.
CREATE OR REPLACE FUNCTION public.ciclos_finalizado_protegido() RETURNS trigger AS $$
BEGIN
  IF OLD.evaluacion_finalizada_en IS NOT NULL AND (
       NEW.abierto OR NOT NEW.cerrado
       OR NEW.evaluacion_finalizada_en IS DISTINCT FROM OLD.evaluacion_finalizada_en
       OR NEW.evaluacion_finalizada_por IS DISTINCT FROM OLD.evaluacion_finalizada_por
       OR NEW.fecha_inicio IS DISTINCT FROM OLD.fecha_inicio
       OR NEW.fecha_fin IS DISTINCT FROM OLD.fecha_fin) THEN
    RAISE EXCEPTION 'El período ya fue finalizado y no se modifica';
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS ciclos_finalizado_protegido ON public.ciclos_dual;
CREATE TRIGGER ciclos_finalizado_protegido
  BEFORE UPDATE ON public.ciclos_dual
  FOR EACH ROW EXECUTE FUNCTION public.ciclos_finalizado_protegido();

-- Defensa en profundidad: en un período finalizado no se registran versiones ni revisiones nuevas.
CREATE OR REPLACE FUNCTION public.rechaza_si_periodo_finalizado() RETURNS trigger AS $$
DECLARE
  reporte uuid;
BEGIN
  IF TG_TABLE_NAME = 'revisiones' THEN
    SELECT v.reporte_id INTO reporte FROM public.reporte_versiones v WHERE v.id = NEW.version_id;
  ELSE
    reporte := NEW.reporte_id;
  END IF;
  IF EXISTS (
    SELECT 1
    FROM public.reportes_dual r
    JOIN public.obligaciones_semanales o ON o.id = r.obligacion_id
    JOIN public.ciclos_dual p ON p.id = o.periodo_id
    WHERE r.id = reporte AND p.evaluacion_finalizada_en IS NOT NULL) THEN
    RAISE EXCEPTION 'El período ya fue finalizado: no se aceptan más entregas ni revisiones';
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS versiones_periodo_finalizado ON public.reporte_versiones;
CREATE TRIGGER versiones_periodo_finalizado
  BEFORE INSERT ON public.reporte_versiones
  FOR EACH ROW EXECUTE FUNCTION public.rechaza_si_periodo_finalizado();

DROP TRIGGER IF EXISTS revisiones_periodo_finalizado ON public.revisiones;
CREATE TRIGGER revisiones_periodo_finalizado
  BEFORE INSERT ON public.revisiones
  FOR EACH ROW EXECUTE FUNCTION public.rechaza_si_periodo_finalizado();

CREATE INDEX IF NOT EXISTS idx_cierre_notas_reporte ON public.cierre_alumno_notas (reporte_id);

ALTER TABLE public.cierres_alumno_periodo ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.cierre_alumno_notas ENABLE ROW LEVEL SECURITY;

DO $$
DECLARE role_name text;
BEGIN
  FOREACH role_name IN ARRAY ARRAY['anon','authenticated'] LOOP
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = role_name) THEN
      EXECUTE format('REVOKE ALL ON TABLE public.cierres_alumno_periodo FROM %I', role_name);
      EXECUTE format('REVOKE ALL ON TABLE public.cierre_alumno_notas FROM %I', role_name);
    END IF;
  END LOOP;
END;
$$;

COMMIT;
