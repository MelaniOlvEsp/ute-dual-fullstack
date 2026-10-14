-- PLANTILLA para revisión de roles históricos; NO ejecutar ejemplos a ciegas.
-- 1. Consultar los usuarios y aprobar la equivalencia por persona.
SELECT id, email, matricula, roles FROM public.usuarios
 ORDER BY email;

-- 2. Tras verificar los identificadores reales, usar transacción controlada:
-- BEGIN;
-- UPDATE public.usuarios SET roles = '{"tutor_academico":true}'::jsonb
-- WHERE id = 'UUID_VERIFICADO' AND matricula IS NULL;
-- UPDATE public.usuarios SET roles = '{"coordinador_dual":true}'::jsonb
-- WHERE id = 'UUID_VERIFICADO' AND matricula IS NULL;
-- UPDATE public.usuarios SET roles = '{"alumno":true}'::jsonb
-- WHERE id = 'UUID_VERIFICADO' AND matricula IS NOT NULL;
-- COMMIT;

-- 3. Todos los usuarios deben tener EXACTAMENTE uno de estos tres roles
-- para que el endurecimiento de 02 sea validable. No reasignar cuentas
-- administrativas o de becas sin una autorización verificable.
