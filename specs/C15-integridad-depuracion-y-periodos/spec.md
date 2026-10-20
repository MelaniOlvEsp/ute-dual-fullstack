# C15 — Integridad de depuración y selección de períodos

Estado: DONE
Fecha: 2026-10-19
Responsable de aprobación: responsable del proyecto
Dependencias: C07, C08B y C14; hallazgos H01/H02 de la auditoría del 2026-10-19.

## Problema y resultado esperado

Un fallo después de eliminar un PDF revierte el registro SQL de todos los documentos; cancelar después puede dejar archivos perdidos sin reintento. Una respuesta atrasada del resumen de períodos puede mostrar A mientras una acción se envía a B.

Resultado: una eliminación parcial conserva progreso y referencias y puede reanudarse; cancelar solo funciona durante la gracia y antes del primer intento. El resumen, la confirmación y el ID enviado siempre corresponden al mismo período.

## Fuentes y alcance

RN-18/19/20/23/25/29, DP-14, AC-14/15/19; [C07](../C07-cierre-y-calificacion/spec.md), [C08B](../C08B-archivo-y-depuracion/spec.md), [protocolo](../../docs/construction/PROTOCOLO_SDD_LITE.md).

Incluye exclusivamente H01/H02, pruebas de regresión, contratos afectados y evidencia. Excluye otros hallazgos, migración de kit, limpieza de Docker, datos históricos, cambios de permisos, calendario, notas o conservación y commit/push.

## Decisiones

La orden del responsable «empieza por corregir los dos hallazgos de prioridad alta [...] siguiendo las specs [...] agregando pruebas» autoriza este alcance. No hay DP bloqueantes ni se solicita aprobación repetida.

- Se conserva el esquema y los estados existentes. `programada` incluye trabajo pendiente de reintento; `intentos` contará ejecuciones iniciadas, persistidas antes del primer borrado. La cancelación se autoriza con reloj de PostgreSQL, dentro de la gracia y con cero intentos; al vencer devuelve 409, aunque el proceso aún no haya arrancado (DP-14).
- Cada documento eliminado se marca y confirma por separado. Se bloquea la fila de la purga durante cada documento con `SKIP LOCKED`; no se mantiene una transacción durante el lote completo. Un archivo ausente sigue contando como eliminado. Si se interrumpe entre borrado y commit, el reintento procesa ese archivo ausente. Las cifras finales representan el alcance completo, no solo lo pendiente del último intento.
- El frontend descarta éxitos, errores y finalizaciones de solicitudes obsoletas, incluidas A→B→A. Cambiar de período elimina el resumen y la confirmación anterior. Confirmar captura un objetivo inmutable; ejecutar vuelve a validar su identidad y evita doble envío. La selección y apertura se bloquean mientras se ejecuta la acción.

## Contratos y cambios

Sin rutas, permisos o estados nuevos ni migración SQL. Cancelación vencida/iniciada: 409 sin liberar documentos. `intentos`: ejecuciones iniciadas (antes solo fallos registrados). Respuestas de ejecución conservan cifras totales. Módulos: `purgas.py`, catálogo `dual_purgas.py`, controlador frontend de cierre y `PeriodosDual.svelte`, pruebas y documentación.

## Verificación

| AC | Prueba | Nivel/datos | Resultado |
|---|---|---|---|
| C15-AC1 | Fallar el segundo archivo, rechazar cancelación, conservar primer progreso y completar al reintentar | PostgreSQL nuevo y archivos sintéticos locales | REAL, fallo inyectado SIMULADO; pasa |
| C15-AC2 | Gracia, límite exacto, cancelación repetida, archivo ausente, fallo de commit y trabajadores concurrentes | Unitarias y PostgreSQL aislado | REAL + fallos/reloj de fixtures SIMULADOS; 8/8 |
| C15-AC3 | A/B y A/B/A fuera de orden, error antiguo y carga pendiente; ningún resumen equivocado | Promesas controladas | SIMULADA; 11/11 regresiones frontend |
| C15-AC4 | Cierre y finalización usan el objetivo confirmado; cambio de selección, doble clic y fallo no envían otra acción | Pruebas de controlador y preview del componente | REAL en navegador con API SIMULADA; pasa |
| C15-AC5 | Regresión backend/frontend, build y contrato; revisión del diff | Suites y revisión del mismo agente | 324/324 backend, 59/59 frontend, contrato 1/1 y build OK; revisión APPROVED |

## Evidencia de implementación

Detalle reproducible en [evidencia.md](evidencia.md). Solo datos sintéticos y servicios aislados para pruebas que escriben. API y web del entorno local reconstruidos; archivos verificados por SHA-256. Sin migraciones ni SQL de corrección sobre el piloto.

## Revisión

Veredicto: APPROVED (2026-10-19). Mismo agente; no es revisión independiente. Se revisaron permisos conservados, fechas con reloj SQL tras el bloqueo, progreso por documento, recuperación tras interrupciones, contratos, selección/confirmación y diff final. Sin defectos materiales pendientes dentro de H01/H02. Limitaciones en evidencia; aprobación humana de cierre pendiente.

## Aprobaciones y cierre

Implementación autorizada por el responsable el 2026-10-19 en este chat. Se documenta DRAFT antes de código; después READY → IN_PROGRESS por esa orden explícita. Cierre humano aprobado el 2026-10-19: «apruebo el cierre de C15». Commit autorizado en el mismo mensaje; push no autorizado.

Cierre: 2026-10-19. Aprobación humana recibida tras revisión APPROVED y evidencia. Siguiente incremento: C16, correcciones de prioridad media H03–H09, autorizado por el responsable.
