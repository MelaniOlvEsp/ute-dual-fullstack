-- Requiere: 01, datos corregidos, roles migrados manualmente a v2.
-- Si alguna VALIDATE falla, corregir datos antes de reintentar.
BEGIN;
SET LOCAL lock_timeout = '5s';

ALTER TABLE public.reportes_dual VALIDATE CONSTRAINT reportes_dual_semana_rango;
ALTER TABLE public.reportes_dual VALIDATE CONSTRAINT reportes_dual_fechas_ordenadas;
ALTER TABLE public.ciclos_dual VALIDATE CONSTRAINT ciclos_dual_estados_excluyentes;
ALTER TABLE public.usuarios VALIDATE CONSTRAINT usuarios_credential_version_no_negativo;
ALTER TABLE public.tutor_firmas VALIDATE CONSTRAINT tutor_firmas_contenido_valido;

-- JSONB permanece temporalmente para compatibilidad con FastAPI.
-- 3 opciones EXACTAS, sin combinaciones que eleven privilegios.
ALTER TABLE public.usuarios ADD CONSTRAINT usuarios_roles_dual_validos
 CHECK (roles IN ('{"alumno":true}'::jsonb,
                  '{"tutor_academico":true}'::jsonb,
                  '{"coordinador_dual":true}'::jsonb)) NOT VALID;
ALTER TABLE public.usuarios ADD CONSTRAINT usuarios_rol_matricula
 CHECK ((roles = '{"alumno":true}'::jsonb AND matricula IS NOT NULL)
     OR (roles <> '{"alumno":true}'::jsonb AND matricula IS NULL))
 NOT VALID;
ALTER TABLE public.usuarios VALIDATE CONSTRAINT usuarios_roles_dual_validos;
ALTER TABLE public.usuarios VALIDATE CONSTRAINT usuarios_rol_matricula;

ALTER TABLE public.buzon_mensajes
 DROP CONSTRAINT IF EXISTS buzon_mensajes_area_check;
ALTER TABLE public.buzon_mensajes
 ADD CONSTRAINT buzon_mensajes_area_check CHECK (area = 'dual') NOT VALID;
ALTER TABLE public.buzon_mensajes
 VALIDATE CONSTRAINT buzon_mensajes_area_check;

-- No se fuerza FK (matricula,cuatrimestre) en reportes hasta resolver
-- la mezcla de periodos calendario y cuatrimestres numerados.
COMMIT;

-- Índices únicos solo después de resolver duplicados identificados en 00.
-- Cada comando CONCURRENTLY se ejecuta sin BEGIN/COMMIT explícitos.
CREATE UNIQUE INDEX CONCURRENTLY IF NOT EXISTS
 idx_dual_usuarios_email_lower ON public.usuarios (lower(email));
CREATE UNIQUE INDEX CONCURRENTLY IF NOT EXISTS
 idx_dual_usuarios_matricula_unica ON public.usuarios (matricula)
 WHERE matricula IS NOT NULL;
CREATE UNIQUE INDEX CONCURRENTLY IF NOT EXISTS
 idx_dual_ciclo_unico_abierto ON public.ciclos_dual (abierto)
 WHERE abierto IS TRUE;

-- No crear índice único sobre alumnos_dual.activo hasta normalizar
-- el ciclo de asignaciones; actualmente puede haber más de una activa.
