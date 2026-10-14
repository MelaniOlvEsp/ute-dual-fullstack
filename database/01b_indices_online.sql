-- CREATE INDEX CONCURRENTLY debe ejecutarse FUERA de una transacción;
-- se recomienda después del diagnóstico y en ventana de mantenimiento.
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_dual_reportes_pendientes
 ON public.reportes_dual (created_at DESC) WHERE estado = 'Pendiente';
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_dual_reportes_periodo_estado
 ON public.reportes_dual (cuatrimestre, estado);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_dual_buzon_alumno_fecha
 ON public.buzon_mensajes (alumno_id, created_at DESC);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_dual_buzon_orden
 ON public.buzon_mensajes (
  area,
  (CASE estado WHEN 'Enviado' THEN 0 WHEN 'Leido' THEN 1 ELSE 2 END),
  created_at DESC
 );
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_dual_respuestas_fecha
 ON public.buzon_respuestas (mensaje_id, created_at);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_dual_foro_autor
 ON public.foro_publicaciones (autor_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_dual_foro_reaccion_usuario
 ON public.foro_reacciones (usuario_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_dual_respuestas_autor
 ON public.buzon_respuestas (autor_id);
