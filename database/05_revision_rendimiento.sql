-- Consultas ilustrativas; ajustar la matrícula y el periodo de PRUEBAS.
-- Requiere filas representativas; correr solo en staging.
EXPLAIN (ANALYZE, BUFFERS)
SELECT id, estado, semana FROM public.reportes_dual
WHERE matricula = 'MATRICULA_FICTICIA'
 AND cuatrimestre = 'Septiembre-Diciembre 2026'
ORDER BY semana;

EXPLAIN (ANALYZE, BUFFERS)
SELECT id, estado, created_at FROM public.buzon_mensajes
WHERE area = 'dual'
ORDER BY CASE estado WHEN 'Enviado' THEN 0 WHEN 'Leido' THEN 1 ELSE 2 END,
 created_at DESC LIMIT 50;

SELECT schemaname, relname, indexrelname, idx_scan, idx_tup_read
FROM pg_stat_user_indexes WHERE schemaname = 'public'
ORDER BY relname, idx_scan DESC;
