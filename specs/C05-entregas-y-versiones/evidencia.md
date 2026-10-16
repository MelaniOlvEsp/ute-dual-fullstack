# Evidencia C05 — Entregas y versiones

Fecha: 2026-10-15. Estado de la spec: DONE (cerrada el 2026-10-15; sin commit ni push).
Clases: REAL = HTTP, PostgreSQL y almacenamiento reales del Compose local; SIMULADA = pruebas con dobles; NO_VERIFICADA = no observado.

## Resumen por criterio

| Criterio | Clase | Fuente |
|---|---|---|
| C05-AC1 entrega por obligación sin bloquear otras semanas | REAL | `scripts/smoke_c05.py` |
| C05-AC2 validaciones de nota, fechas y PDF sin rastro | REAL + SIMULADA (límite JS) | smoke C05, `tests/test_c05_entregas.py`, `report.test.js` |
| C05-AC3 rechazo, reenvío como versión 2, idempotencia, concurrencia | REAL | smoke C05 |
| C05-AC4 original byte a byte, hash, inmutabilidad | REAL | smoke C05 (archivo, descargas, trigger) |
| C05-AC5 período cerrado o ausente | REAL | smoke C05 |
| C05-AC6 permisos y rutas retiradas | REAL | smoke C05 + contrato estático 60/60 |
| C05-AC7 fallos inyectados y huérfanos | REAL (transacción, limpieza) + SIMULADA (dobles) | smoke C05, pruebas unitarias |
| C05-AC8 preview visual | REAL parcial | navegador embebido, 375 y 1280 px, tema oscuro, teclado |

## Ejecuciones

- Backend `python -m unittest discover -s tests` en el contenedor `api`: 105 pruebas OK (27 nuevas de C05). SIMULADA.
- JS (`report.test.js` y demás): 25/25. SIMULADA. Contrato estático de rutas: 60/60.
- Vite build sin avisos para `ReportesDual`.
- Smokes C01, C02, C03, C04 y C05 en PASS contra HTTP/PostgreSQL reales (C05 también sobre el sistema de archivos real).
- Migración `005_entregas.sql`: instalación en base nueva (esquema + 003 + 004 + 005) sin errores; reaplicación idempotente; un disparador de inmutabilidad; tablas `documentos` y `reporte_versiones` presentes.

## NO_VERIFICADO / limitaciones

- Drive y cualquier proveedor externo.
- Revisión y firma del tutor: es C06. La aprobación heredada sigue subiendo a Drive y vacía `archivo_pdf_local`; el original queda preservado en `documentos` y ya no se borra.
- Descarga del PDF en el navegador: la petición responde 200 pero no se observó el guardado.
- Dispositivo móvil físico; el preview móvil fue emulado a 375 px.
- La validación del cliente (no PDF, vacío, > 10 MB) se ejerció adjuntando archivos por script, pues el panel no tiene selector de archivos.
- Reportes heredados con `obligacion_id` nulo ya no se ligan a obligaciones.
- Queda una fila de `documentos` residual de una corrida defectuosa anterior del smoke (archivo ya borrado); sin efecto funcional, no se tocó.
- Cierre de período, expediente y promedios siguen tratando la nota como en el diseño anterior hasta C06–C10. Pendientes heredadas de C04 sin cambios.

## Revisión y acta de cierre

La revisión técnica contra el diff y la spec concluyó APPROVED el 2026-10-15 en su primera pasada, sin defectos materiales. Fue del mismo agente, no independiente; la revisión visual no se repitió y se apoya en el preview anterior (build desplegado posterior a la última edición). Observaciones no bloqueantes: la limpieza de huérfanos no se ejecuta automáticamente (solo smoke y pruebas), el COMMIT ambiguo podría borrar un archivo recién confirmado, y el nombre de descarga es `<matricula>-v<n>.pdf`.

El responsable otorgó aprobación de cierre el 2026-10-15 con `CLOSE C05 + NEXT SPEC`, sujeta a revisión aprobada y evidencia suficiente. C05 queda DONE con las limitaciones de la spec. Sin commit ni push.

## Decisiones aplicadas

DP-08: PDF máximo 10 MB, almacenamiento local privado. DP-12: solo inicio ≤ fin. DP-13: solo con período abierto y no cerrado. Registradas en `docs/analysis/DECISIONES_PENDIENTES.md`.
