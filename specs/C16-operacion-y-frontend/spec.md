# C16 — Operación multiusuario y frontend

Estado: IN_PROGRESS
Fecha: 2026-10-19
Dependencia: C15 DONE, cierre humano aprobado en este chat.

## Problema, alcance y autorización

Corrige H03–H09 de prioridad media de la auditoría: login detrás de NAT, carrera/grupo filtrados sobre una sola página, CSV vacío por encabezados y lectura sin límite, salud síncrona de Drive, foco del buzón y dependencias/servidor web de desarrollo. El responsable autorizó implementación, pruebas y commit: «sigue con los hallazgos de prioridad media siguiendo las specs y agregando sus pruebas y haz el commit». No requiere otra aprobación del alcance.

Referencias: RN-01/04/05/25/27/28/29; C02 (acceso), C03 (CSV y pertenencia histórica), C08 (directorio), C09/C12 (buzón/accesibilidad), C10A (salud Drive), C14 (límites y dependencias). No cambia permisos, notas, calendario o conservación. No hay DP bloqueantes. Excluye H10 (autofill, prioridad baja), kit UX, rediseño general, limpieza histórica y push.

## Decisiones y contratos

- H03: ocho fallos por identidad normalizada cada cinco minutos, sin cobrar accesos exitosos; reservar intentos concurrentes y liberar la reserva al terminar. Mantener bloqueo persistente por cuenta (cinco fallos/15 minutos) y límites agregados C14 por IP con resolución de proxies ya centralizada. Respuestas 429 con Retry-After. Estado temporal acotado, sin correos en claves/logs.
- H04: filtrar carrera en SQL antes de contar/paginar. Con período se usa grupo histórico si existe y, como en expediente, grupo actual como respaldo; sin período se usa actual. Carreras del catálogo institucional completo y grupos del catálogo, no de la página. `GET /dual/carrera/alumnos` añade `carrera` opcional y `grupos` en la respuesta, manteniendo items/total/limite/desplazamiento. Carrera acepta código/nombre institucional validado. Conteo correcto incluso fuera de la última página. Evitar respuestas obsoletas del directorio.
- H05/H06: normalizar las claves de encabezados; rechazar archivo vacío, columnas extra, UTF-8/CSV inválido y filas sin datos. Máximo 500 filas, nombre 150 caracteres, archivo 512 KiB; ambos endpoints leen como máximo límite+1. Middleware ASGI previo a multipart limita solicitud CSV a 600 KiB, incluso sin Content-Length. Errores 413/422, sin aplicar lotes inválidos.
- H07: consulta de almacenamiento en hilo, compartida entre solicitudes concurrentes y con espera máxima de un segundo; si tarda, reportar almacenamiento no disponible sin detener el event loop ni multiplicar hilos. Mantener HTTP 503 si falla PostgreSQL y 200 con almacenamiento degradado cuando corresponde.
- H08: reutilizar `<dialog>` y `modalFocus` para foco inicial, Tab/Shift+Tab, Escape y devolución al botón de apertura, incluyendo carga/error. Ninguna modificación del hilo durante el preview.
- H09: versiones oficiales compatibles de Svelte/Vite/plugin, lockfile reproducible, conservar sintaxis legacy de componentes; usar `mount` en entradas. Imagen web multietapa con nginx y fallback SPA, sin servidor Vite en ejecución. Configuración de URL de API al arrancar para conservar puertos configurables; conservar 127.0.0.1:5174. No introducir kit o SvelteKit.

## Aceptación y pruebas

| AC | Verificación | Estado |
|---|---|---|
| C16-1 | Nueve accesos correctos misma IP; fallos, concurrencia, expiración y 429/Retry-After | NO_VERIFICADA |
| C16-2 | Carrera fuera de página inicial, grupo histórico, combinación de filtros, total fuera de rango; catálogo y navegación | NO_VERIFICADA |
| C16-3 | Encabezados variantes, vacío, CSV defectuoso, columnas, bytes/filas/campos; multipart declarado y streaming | NO_VERIFICADA |
| C16-4 | Tarea lenta de salud no bloquea otras solicitudes, timeout y una consulta compartida | NO_VERIFICADA |
| C16-5 | Preview real del buzón: carga/error, Tab/Shift+Tab, Escape y foco restaurado | NO_VERIFICADA |
| C16-6 | Suites, build, auditoría npm, rutas SPA estáticas, URL API y preview tras migración | NO_VERIFICADA |

SQL solo en base nueva aislada con datos sintéticos; no ejecutar smokes de escritura sobre el piloto. Revisar diff y evidencia REAL/SIMULADA. No afirmar revisión independiente.

## Ejecución y cierre

DRAFT antes de código; autorización explícita anterior permite READY → IN_PROGRESS. Commit autorizado. Cierre de C16 pendiente de aprobación humana posterior a pruebas y revisión; no marcar DONE automáticamente. Evidencia en `evidencia.md`.
