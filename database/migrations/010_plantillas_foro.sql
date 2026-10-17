-- C09: plantilla común versionada (pareja Word + PDF), política del buzón (DP-09 D1) y moderación de
-- anuncios (DP-09 D2). Aditiva e idempotente sobre C08B. No borra ni reasigna historia.
BEGIN;

SELECT pg_advisory_xact_lock(19868);

-- ---------- Plantillas: una versión es una pareja completa e inmutable; una sola vigente ----------
CREATE TABLE IF NOT EXISTS public.plantillas_version (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  numero integer NOT NULL UNIQUE CHECK (numero >= 1),
  publicada_por uuid NOT NULL REFERENCES public.usuarios(id),
  publicada_en timestamptz NOT NULL DEFAULT now(),
  vigente boolean NOT NULL DEFAULT FALSE,
  nota varchar(200),
  word_clave text NOT NULL UNIQUE CHECK (word_clave ~ '^[0-9a-f]{32}\.docx$'),
  word_tamano integer NOT NULL CHECK (word_tamano BETWEEN 1 AND 10485760),
  word_sha256 char(64) NOT NULL CHECK (word_sha256 ~ '^[0-9a-f]{64}$'),
  pdf_clave text NOT NULL UNIQUE CHECK (pdf_clave ~ '^[0-9a-f]{32}\.pdf$'),
  pdf_tamano integer NOT NULL CHECK (pdf_tamano BETWEEN 1 AND 10485760),
  pdf_sha256 char(64) NOT NULL CHECK (pdf_sha256 ~ '^[0-9a-f]{64}$'),
  pdf_paginas integer NOT NULL CHECK (pdf_paginas >= 1)
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_plantilla_vigente_unica ON public.plantillas_version ((TRUE)) WHERE vigente;

CREATE OR REPLACE FUNCTION public.plantillas_inmutables() RETURNS trigger AS $$
BEGIN
  IF TG_OP = 'DELETE' THEN
    RAISE EXCEPTION 'Las versiones de plantilla no se eliminan';
  END IF;
  IF (to_jsonb(NEW) - 'vigente') IS DISTINCT FROM (to_jsonb(OLD) - 'vigente')
     OR NOT (OLD.vigente AND NOT NEW.vigente) THEN
    RAISE EXCEPTION 'Una versión de plantilla solo deja de ser vigente; no se modifica';
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS plantillas_inmutables ON public.plantillas_version;
CREATE TRIGGER plantillas_inmutables
  BEFORE UPDATE OR DELETE ON public.plantillas_version
  FOR EACH ROW EXECUTE FUNCTION public.plantillas_inmutables();

ALTER TABLE public.plantillas_version ENABLE ROW LEVEL SECURITY;

-- ---------- Buzón: hilo cerrado de solo lectura, reapertura explícita y hilo nuevo enlazado ----------
ALTER TABLE public.buzon_mensajes ADD COLUMN IF NOT EXISTS hilo_anterior_id uuid REFERENCES public.buzon_mensajes(id);
ALTER TABLE public.buzon_mensajes ADD COLUMN IF NOT EXISTS reabierto_por uuid REFERENCES public.usuarios(id);
ALTER TABLE public.buzon_mensajes ADD COLUMN IF NOT EXISTS reabierto_en timestamptz;
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'buzon_hilo_anterior_distinto') THEN
    ALTER TABLE public.buzon_mensajes ADD CONSTRAINT buzon_hilo_anterior_distinto
      CHECK (hilo_anterior_id IS NULL OR hilo_anterior_id <> id);
  END IF;
END;
$$;
CREATE INDEX IF NOT EXISTS idx_buzon_hilo_anterior ON public.buzon_mensajes (hilo_anterior_id) WHERE hilo_anterior_id IS NOT NULL;

-- Defensa en profundidad: ninguna respuesta entra en un hilo cerrado, sin importar quién la envíe.
CREATE OR REPLACE FUNCTION public.buzon_respuesta_hilo_abierto() RETURNS trigger AS $$
BEGIN
  IF EXISTS (SELECT 1 FROM public.buzon_mensajes WHERE id = NEW.mensaje_id AND estado = 'Cerrado') THEN
    RAISE EXCEPTION 'El hilo está cerrado; el personal debe reabrirlo';
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS buzon_respuesta_hilo_abierto ON public.buzon_respuestas;
CREATE TRIGGER buzon_respuesta_hilo_abierto
  BEFORE INSERT ON public.buzon_respuestas
  FOR EACH ROW EXECUTE FUNCTION public.buzon_respuesta_hilo_abierto();

-- ---------- Anuncios: eliminación lógica conservada, sin edición ----------
ALTER TABLE public.foro_publicaciones ADD COLUMN IF NOT EXISTS eliminada_por uuid REFERENCES public.usuarios(id);
ALTER TABLE public.foro_publicaciones ADD COLUMN IF NOT EXISTS eliminada_en timestamptz;
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'foro_eliminacion_completa') THEN
    ALTER TABLE public.foro_publicaciones ADD CONSTRAINT foro_eliminacion_completa
      CHECK ((eliminada_por IS NULL) = (eliminada_en IS NULL));
  END IF;
END;
$$;
CREATE INDEX IF NOT EXISTS idx_foro_publicaciones_visibles ON public.foro_publicaciones (created_at DESC) WHERE eliminada_en IS NULL;

CREATE OR REPLACE FUNCTION public.foro_publicaciones_sin_edicion() RETURNS trigger AS $$
BEGIN
  IF (to_jsonb(NEW) - 'eliminada_por' - 'eliminada_en') IS DISTINCT FROM (to_jsonb(OLD) - 'eliminada_por' - 'eliminada_en') THEN
    RAISE EXCEPTION 'Los anuncios no se editan';
  END IF;
  IF OLD.eliminada_en IS NOT NULL
     AND (NEW.eliminada_en IS DISTINCT FROM OLD.eliminada_en OR NEW.eliminada_por IS DISTINCT FROM OLD.eliminada_por) THEN
    RAISE EXCEPTION 'Un anuncio eliminado no se restablece';
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS foro_publicaciones_sin_edicion ON public.foro_publicaciones;
CREATE TRIGGER foro_publicaciones_sin_edicion
  BEFORE UPDATE ON public.foro_publicaciones
  FOR EACH ROW EXECUTE FUNCTION public.foro_publicaciones_sin_edicion();

DO $$
DECLARE role_name text;
BEGIN
  FOREACH role_name IN ARRAY ARRAY['anon','authenticated'] LOOP
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = role_name) THEN
      EXECUTE format('REVOKE ALL ON TABLE public.plantillas_version FROM %I', role_name);
    END IF;
  END LOOP;
END;
$$;

COMMIT;
