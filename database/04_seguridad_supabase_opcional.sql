-- Opcional: ÚNICAMENTE si toda lectura/escritura pasa por FastAPI,
-- sin consumir las tablas mediante Supabase Data API en el navegador.
-- Comprobar antes los permisos del rol PostgreSQL usado por FastAPI.
BEGIN;
DO $$
DECLARE t text;
BEGIN
 FOREACH t IN ARRAY ARRAY[
   'grupos','empresas','alumnos','usuarios','ciclos_dual','alumnos_dual',
   'reportes_dual','tutor_firmas','foro_publicaciones','foro_reacciones',
   'buzon_mensajes','buzon_respuestas'
 ] LOOP
   EXECUTE format('ALTER TABLE public.%I ENABLE ROW LEVEL SECURITY', t);
   IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN
     EXECUTE format('REVOKE ALL ON TABLE public.%I FROM anon', t);
   END IF;
   IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
     EXECUTE format('REVOKE ALL ON TABLE public.%I FROM authenticated', t);
   END IF;
 END LOOP;
END;
$$;
COMMIT;
-- No crear políticas permisivas genéricas. Si más adelante se usa
-- Supabase Data API, definir GRANT + RLS por operación/usuario y probarlas.
