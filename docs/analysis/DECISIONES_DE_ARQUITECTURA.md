# Decisiones de arquitectura

## ADR-01 — Conservar stack y organización

CONFIRMADO: preferencia por FastAPI, PostgreSQL y frontend Svelte existente. Evolucionar el monolito por capas: dominio, aplicación, infraestructura y presentación. No migrar a NestJS/React por tomar PC-Refresh como referencia. No añadir microservicios ni frameworks sin necesidad demostrada.

## ADR-02 — Un calendario de dominio

PROPUESTO: una función/servicio de dominio define semanas, período, atraso y elegibilidad; frontend consume resultados de API. No duplicar lógica con fechas del navegador ni derivar próxima semana de última aprobación. Reloj inyectable en pruebas. Resolver DP-01/03/04 en C04.

## ADR-03 — Archivos privados y almacenamiento intercambiable

IMPLEMENTADO en C10A (2026-10-17): contrato mínimo guardar/leer/eliminar/existe/listar sobre claves del servidor con adaptador de Drive para el piloto (el responsable decidió que los archivos y los respaldos viven en Drive y no se guarda nada local); los adaptadores `local` y `memoria` quedan solo para desarrollo, regresión y pruebas. Autorizar descargas en API; visor usa respuesta binaria autenticada. No publicar documentos para resolver fallos de iframe.

Drive necesita credenciales renovadas y prueba real. Ninguna opción de alojamiento se considera gratuita garantizada ni elegida. Comparar costos/límites vigentes cuando se decida publicar; esta entrega no recomienda proveedor.

## ADR-04 — Original, versión y firmado

PROPUESTO: conservar bytes originales entregados, hash y metadatos. Generar firmado como derivado sin destruir original. Reducir tamaño únicamente si no perjudica legibilidad y sin reemplazar la evidencia original. No convertir fallos de firma/subida en aprobación.

## ADR-05 — Calendario civil y cierres manuales

CONFIRMADO: bloques enero–abril, mayo–agosto, septiembre–diciembre; cierre manual. PROPUESTO: instantes UTC y fechas civiles con zona configurada. Recepción y evaluación independientes; no tareas programadas que cierren por fecha. Apertura se decide en DP-04.

## ADR-06 — Seguridad proporcional

Autorización por rol/propietario en servidor, consultas parametrizadas, validación de contenido y tamaño, credenciales fuera de repositorio, CORS explícito. Desactivar cuentas y revocar sesiones preservando historia. No usar datos reales en fixtures ni incluir PDF personal en evidencia.

La configuración RLS de Supabase requiere verificar rol efectivo del backend; no ejecutar scripts de revocación por defecto. Local primero; RLS no sustituye autorización de API.

## ADR-07 — Validación por niveles

Pruebas de dominio con reloj fijo; integración real PostgreSQL para restricciones/transacciones; contratos frontend/API; navegador para upload, visor y buzón; recorrido integral local. Un test de rutas simulado no sustituye solicitudes reales ni lectura de documentos.

## ADR-08 — Simplicidad en operación

No introducir cola ni scheduler solo para mostrar pendientes: pueden derivarse o materializarse idempotentemente al configurar períodos/incorporaciones. Elegir en C04 según consistencia, no por patrón. Automatización de despliegue no es requisito inicial.

## ADR-09 — Base nueva

CONFIRMADO: no hay datos reales a conservar. Crear esquema reproducible en BD nueva y fixtures sintéticos. Mantener SQL heredado como referencia identificada, sin ejecutar limpiezas o migraciones sobre instancias ajenas.

Las propuestas se convierten en decisiones de implementación al aprobar la spec que las detalla. Registrar motivo si una alternativa conserva requisitos con menor complejidad.
