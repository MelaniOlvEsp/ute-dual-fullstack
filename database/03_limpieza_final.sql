-- DESTRUCTIVO: solo después de respaldo verificado, despliegue del backend
-- ajustado y comprobaciones 00-02. Nunca ejecutar automáticamente.
BEGIN;
SET LOCAL lock_timeout = '5s';

DO $$
BEGIN
 IF EXISTS (SELECT 1 FROM public.solicitudes LIMIT 1)
    OR EXISTS (SELECT 1 FROM public.convocatorias_becas LIMIT 1) THEN
   RAISE EXCEPTION 'Becas contiene datos. Respaldar/archivar primero; no se borrará nada.';
 END IF;
 IF EXISTS (SELECT 1 FROM public.buzon_mensajes WHERE area <> 'dual') THEN
   RAISE EXCEPTION 'Existen mensajes de otras áreas: archivarlos antes de continuar.';
 END IF;
END;
$$;

-- No utiliza CASCADE para evitar eliminar dependencias desconocidas.
DROP TABLE IF EXISTS public.solicitudes;
DROP TABLE IF EXISTS public.convocatorias_becas;

ALTER TABLE public.usuarios
 DROP COLUMN IF EXISTS email_verificado,
 DROP COLUMN IF EXISTS codigo_verificacion,
 DROP COLUMN IF EXISTS codigo_verificacion_exp,
 DROP COLUMN IF EXISTS verification_attempts,
 DROP COLUMN IF EXISTS verification_locked_until;

-- PK y UNIQUE(matricula) del esquema antiguo duplicaban la misma llave.
ALTER TABLE public.alumnos
 DROP CONSTRAINT IF EXISTS alumnos_matricula_key;

-- Los índices de la izquierda ya están cubiertos por UNIQUE de 2 columnas.
DROP INDEX IF EXISTS public.idx_alumnos_dual_matricula;
DROP INDEX IF EXISTS public.idx_reportes_dual_matricula;
DROP INDEX IF EXISTS public.idx_foro_reacciones_publicacion;

-- Una sola matrícula por cuenta. Mantener índice UNIQUE parcial de 02.
DROP INDEX IF EXISTS public.idx_usuarios_matricula;

-- El índice nuevo del ciclo sustituye al antiguo, no único.
DROP INDEX IF EXISTS public.idx_ciclos_dual_abierto;
DROP INDEX IF EXISTS public.idx_buzon_area_created;
DROP INDEX IF EXISTS public.idx_buzon_respuestas_mensaje;
COMMIT;
