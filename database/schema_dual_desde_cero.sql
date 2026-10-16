-- Esquema limpio para instalaciones NUEVAS, NO ejecutar sobre BD existente.
-- PostgreSQL / Supabase; conserva los nombres consultados por FastAPI v2.
-- Base canónica C01 para Docker Compose; modelo de calendario/versiones pendiente C04-C07.
-- Catálogo de carreras: TII, LOG y MER (C03). migrations/003 añade carreras, historia e incorporaciones.
BEGIN;

SELECT pg_advisory_xact_lock(19861);
DO $$
BEGIN
 IF EXISTS (
  SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
  WHERE n.nspname='public' AND c.relkind IN ('r','p','v','m','S','f')
 ) THEN
  RAISE EXCEPTION 'C01 requiere esquema public vacío. No se modifica una base existente.';
 END IF;
END;
$$;

CREATE TABLE public.grupos (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
 plan char(2) NOT NULL,
 carrera text NOT NULL CHECK (carrera IN (
  'ING.NME TEC DE LA INFORMACIÓN E INNOVACION DIGITAL',
  'ING. NME LOGISTICA','LIC. NME MERCADOTECNIA')),
 zona smallint NOT NULL,
 modalidad text NOT NULL CHECK (modalidad IN
  ('bis','intensivo','mixta','despresurizada')),
 cuatrimestre smallint NOT NULL CHECK (cuatrimestre BETWEEN 1 AND 12),
 letra char(1) NOT NULL,
 fecha_inicio date NOT NULL DEFAULT CURRENT_DATE,
 turno text CHECK (turno IN ('Matutino','Vespertino')),
 ciclo_ingreso text NOT NULL DEFAULT to_char(CURRENT_DATE, 'YYYY'),
 nomenclatura text GENERATED ALWAYS AS (
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
 ) STORED,
 CONSTRAINT grupos_identidad_unica UNIQUE
 (ciclo_ingreso,plan,carrera,zona,modalidad,cuatrimestre,letra)
);

CREATE TABLE public.empresas (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
 nombre text NOT NULL UNIQUE,
 created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE public.alumnos (
 matricula text PRIMARY KEY,
 nombre text NOT NULL,
 email text UNIQUE,
 grupo_id uuid REFERENCES public.grupos(id),
 registro_dual_autorizado boolean NOT NULL DEFAULT FALSE
);
CREATE INDEX idx_alumnos_grupo_id ON public.alumnos (grupo_id);

CREATE TABLE public.usuarios (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
 email text NOT NULL UNIQUE,
 password_hash text NOT NULL,
 roles jsonb NOT NULL,
 matricula text REFERENCES public.alumnos(matricula),
 created_at timestamptz NOT NULL DEFAULT now(),
 nombre varchar(150),
 must_change_password boolean NOT NULL DEFAULT FALSE,
 credential_version integer NOT NULL DEFAULT 0
   CHECK (credential_version >= 0),
 login_attempts integer NOT NULL DEFAULT 0 CHECK (login_attempts >= 0),
 login_locked_until timestamptz,
 activo boolean NOT NULL DEFAULT TRUE,
 CONSTRAINT usuarios_roles_validos CHECK (roles IN (
   '{"alumno":true}'::jsonb,
   '{"tutor_academico":true}'::jsonb,
   '{"coordinador_dual":true}'::jsonb)),
 CONSTRAINT usuarios_tipo_matricula CHECK (
   (roles = '{"alumno":true}'::jsonb AND matricula IS NOT NULL) OR
   (roles <> '{"alumno":true}'::jsonb AND matricula IS NULL))
);
CREATE UNIQUE INDEX idx_dual_usuarios_email_lower
 ON public.usuarios (lower(email));
CREATE UNIQUE INDEX idx_dual_usuarios_matricula_unica
 ON public.usuarios (matricula) WHERE matricula IS NOT NULL;

CREATE TABLE public.ciclos_dual (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
 cuatrimestre text NOT NULL UNIQUE
   CHECK (cuatrimestre ~ '^(Enero-Abril|Mayo-Agosto|Septiembre-Diciembre) [0-9]{4}$'),
 cerrado boolean NOT NULL DEFAULT FALSE,
 cerrado_por uuid REFERENCES public.usuarios(id),
 cerrado_at timestamptz,
 periodo_label text CHECK (
   periodo_label IS NULL OR
   periodo_label ~ '^(Enero-Abril|Mayo-Agosto|Septiembre-Diciembre) [0-9]{4}$'),
 fecha_inicio date,
 fecha_fin date,
 abierto boolean NOT NULL DEFAULT FALSE,
 created_at timestamptz NOT NULL DEFAULT now(),
 CONSTRAINT ciclos_dual_estado_consistente CHECK (NOT (abierto AND cerrado)),
 CONSTRAINT ciclos_dual_fecha_consistente CHECK (
   fecha_inicio IS NULL OR fecha_fin IS NULL OR fecha_inicio <= fecha_fin)
);
CREATE UNIQUE INDEX idx_dual_ciclo_unico_abierto ON public.ciclos_dual (abierto)
 WHERE abierto IS TRUE;

CREATE TABLE public.alumnos_dual (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
 matricula text NOT NULL REFERENCES public.alumnos(matricula),
 cuatrimestre text NOT NULL,
 empresa_id uuid REFERENCES public.empresas(id),
 activo boolean NOT NULL DEFAULT TRUE,
 created_at timestamptz NOT NULL DEFAULT now(),
 CONSTRAINT alumnos_dual_unico UNIQUE (matricula,cuatrimestre)
);
CREATE INDEX idx_alumnos_dual_empresa_id ON public.alumnos_dual (empresa_id);

CREATE TABLE public.reportes_dual (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
 matricula text NOT NULL REFERENCES public.alumnos(matricula),
 cuatrimestre text NOT NULL,
 semana integer NOT NULL CHECK (semana BETWEEN 1 AND 18),
 calificacion_alumno numeric NOT NULL
   CHECK (calificacion_alumno BETWEEN 1 AND 10),
 archivo_pdf_url text,
 estado text NOT NULL DEFAULT 'Pendiente'
   CHECK (estado IN ('Pendiente','Aprobada','Rechazada')),
 nota_agente text,
 created_at timestamptz NOT NULL DEFAULT now(),
 updated_at timestamptz NOT NULL DEFAULT now(),
 fecha_inicio date,
 fecha_fin date,
 archivo_pdf_local text,
 revisado_por uuid REFERENCES public.usuarios(id),
 revisado_en timestamptz,
 CONSTRAINT reportes_dual_unico UNIQUE (matricula,cuatrimestre,semana),
 CONSTRAINT reportes_dual_fechas CHECK (
   fecha_inicio IS NULL OR fecha_fin IS NULL OR fecha_inicio <= fecha_fin)
);
CREATE INDEX idx_dual_reportes_pendientes
 ON public.reportes_dual (created_at DESC) WHERE estado = 'Pendiente';
CREATE INDEX idx_dual_reportes_periodo_estado
 ON public.reportes_dual (cuatrimestre,estado);

CREATE TABLE public.tutor_firmas (
 tutor_id uuid PRIMARY KEY REFERENCES public.usuarios(id) ON DELETE CASCADE,
 imagen bytea NOT NULL,
 content_type varchar(25) NOT NULL
   CHECK (content_type IN ('image/png','image/jpeg')),
 actualizada_en timestamptz NOT NULL DEFAULT now(),
 CONSTRAINT tutor_firmas_tamano CHECK (
   octet_length(imagen) BETWEEN 1 AND 1048576)
);

CREATE TABLE public.foro_publicaciones (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
 autor_id uuid NOT NULL REFERENCES public.usuarios(id),
 autor_nombre varchar(255) NOT NULL,
 autor_rol varchar(50) NOT NULL,
 contenido text NOT NULL CHECK (length(btrim(contenido)) > 0),
 created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX idx_foro_publicaciones_created
 ON public.foro_publicaciones (created_at DESC);
CREATE INDEX idx_dual_foro_autor ON public.foro_publicaciones (autor_id);

CREATE TABLE public.foro_reacciones (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
 publicacion_id uuid NOT NULL REFERENCES public.foro_publicaciones(id)
   ON DELETE CASCADE,
 usuario_id uuid NOT NULL REFERENCES public.usuarios(id) ON DELETE CASCADE,
 tipo varchar(20) NOT NULL CHECK
   (tipo IN ('like','love','haha','wow','sad','angry')),
 created_at timestamptz NOT NULL DEFAULT now(),
 CONSTRAINT foro_reacciones_unica UNIQUE (publicacion_id, usuario_id)
);
CREATE INDEX idx_dual_foro_reaccion_usuario
 ON public.foro_reacciones (usuario_id);

CREATE TABLE public.buzon_mensajes (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
 alumno_id uuid NOT NULL REFERENCES public.usuarios(id),
 matricula varchar(20),
 correo varchar(255) NOT NULL,
 area varchar(20) NOT NULL DEFAULT 'dual' CHECK (area = 'dual'),
 asunto varchar(150) NOT NULL,
 mensaje varchar(500) NOT NULL,
 created_at timestamptz NOT NULL DEFAULT now(),
 estado varchar(10) NOT NULL DEFAULT 'Enviado'
   CHECK (estado IN ('Enviado','Leido','Cerrado')),
 cerrado_por uuid REFERENCES public.usuarios(id),
 cerrado_en timestamptz
);
CREATE INDEX idx_dual_buzon_alumno_fecha
 ON public.buzon_mensajes (alumno_id,created_at DESC);
CREATE INDEX idx_dual_buzon_orden ON public.buzon_mensajes (
 area,
 (CASE estado WHEN 'Enviado' THEN 0 WHEN 'Leido' THEN 1 ELSE 2 END),
 created_at DESC
);

CREATE TABLE public.buzon_respuestas (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
 mensaje_id uuid NOT NULL REFERENCES public.buzon_mensajes(id)
   ON DELETE CASCADE,
 autor_id uuid NOT NULL REFERENCES public.usuarios(id),
 autor_rol varchar(30) NOT NULL,
 texto varchar(1000) NOT NULL,
 created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX idx_dual_respuestas_fecha
 ON public.buzon_respuestas (mensaje_id,created_at);
CREATE INDEX idx_dual_respuestas_autor ON public.buzon_respuestas (autor_id);

-- Seguridad por defecto para una API que usa conexión PostgreSQL privada.
-- Activar políticas explícitas si posteriormente se expone Data API.
ALTER TABLE public.grupos ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.empresas ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.alumnos ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.usuarios ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.ciclos_dual ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.alumnos_dual ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.reportes_dual ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.tutor_firmas ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.foro_publicaciones ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.foro_reacciones ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.buzon_mensajes ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.buzon_respuestas ENABLE ROW LEVEL SECURITY;
DO $$
DECLARE table_name text;
BEGIN
 FOREACH table_name IN ARRAY ARRAY[
  'grupos','empresas','alumnos','usuarios','ciclos_dual','alumnos_dual',
  'reportes_dual','tutor_firmas','foro_publicaciones','foro_reacciones',
  'buzon_mensajes','buzon_respuestas'
 ] LOOP
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN
   EXECUTE format('REVOKE ALL ON TABLE public.%I FROM anon', table_name);
  END IF;
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
   EXECUTE format('REVOKE ALL ON TABLE public.%I FROM authenticated',
                  table_name);
  END IF;
 END LOOP;
END;
$$;

COMMIT;
