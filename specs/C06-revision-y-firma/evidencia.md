# Evidencia C06 — Revisión y firma

Fecha: 2026-10-16. Estado de la spec: DONE (cerrada el 2026-10-16; sin push).
Clases: REAL = HTTP, PostgreSQL y almacenamiento reales del Compose local (datos sintéticos); SIMULADA = pruebas con dobles; NO_VERIFICADA = no observado.

## Resumen por criterio

| Criterio | Clase | Fuente |
|---|---|---|
| C06-AC1 corrección trazable de fechas y nota | REAL + SIMULADA (dominio y casos de uso) | `smoke_c06.py`, `test_c06_revision.py`, `report.test.js` |
| C06-AC2 la corrección no mueve período; revisión con recepción cerrada | REAL | smoke C06 |
| C06-AC3 rechazo con observación, reenvío y versión obsoleta | REAL | smoke C06 |
| C06-AC4 original y firmado conservados byte a byte | REAL | smoke C06 (archivos, hashes, descargas) |
| C06-AC5 fallos inyectados sin aprobación a medias | REAL (BD real) + SIMULADA | smoke C06, pruebas unitarias |
| C06-AC6 concurrencia entre tutores | REAL | smoke C06 |
| C06-AC7 permisos y negativos | REAL | smoke C06 + contrato estático 62/62 |
| C06-AC8 firma en la celda del tutor | REAL; muestra sintética aceptada por el responsable el 2026-10-16 | réplica sintética, ejemplo local, muestra |
| C06-AC9 preview visual | REAL parcial | navegador integrado |

## Ejecuciones

- Backend `python -m unittest discover -s tests` en el contenedor `api`: 132 pruebas OK (27 nuevas de C06, incluido el estampado real con PyMuPDF sobre PDF sintéticos: celda, varias páginas, respaldo, celda ocupada, página girada, firma inválida). SIMULADA para casos de uso con dobles.
- JS: 28/28 (3 nuevas: validación de revisión, cuerpo de la solicitud y caso de uso). Contrato estático y de integración: 62 llamadas contra 62 rutas.
- Smoke C06 PASS con HTTP, PostgreSQL y almacenamiento reales: corrección de nota y fecha con previo/nuevo, lo declarado intacto, obligaciones sin cambios, firmado en la celda, hashes, descargas de tutor y alumno, reintento idéntico, inmutabilidad en la base, rechazo con observación y reenvío, versión obsoleta, respaldo con hoja adicional, tutor sin firma 409, fallos inyectados (confirmar y estampar), dos tutores simultáneos, permisos y revisión con el período cerrado.
- Regresión: smokes C01, C02, C03, C04 y C05 PASS (el de C05 se adaptó a la nueva ruta de rechazo).
- Migración `006_revisiones.sql`: instalación en base nueva (esquema + 003 a 006) sin errores; reaplicación idempotente; tres disparadores de inmutabilidad y las cuatro tablas presentes.
- Vite build: sin avisos en `CoordinadorDual`, `ReportesDual` ni `FirmaTutor` (los avisos existentes son de `CoordinadorCarrera` y `BuzonDetalleModal`, fuera del alcance).
- Estampado sobre el reporte de ejemplo del responsable (una hoja, tabla de firmas al final): celda localizada (≈102×30 pt) y firma dentro de ella sin tocar lo demás; se revisó visualmente un recorte. El archivo no se copió al repositorio.

## Visual REAL (navegador integrado, datos sintéticos)

Tutor en escritorio: el rechazo sin observación y la nota 8.5 se bloquean con mensaje claro; la nota corregida de 10 a 9 se aprueba y firma; el visor ofrece pestañas «Original del alumno» y «Firmado»; el historial muestra «Nota: 10 → 9» y «Firmado (en la celda del tutor)». En 375 px no hay desborde horizontal. Alumno: «Mis semanas» con estados, historial con «Corregida por el tutor: 9», rechazo con observación y enlaces a original y firmado (la petición responde 200). Se corrigió un espacio faltante en «Rechazada · observación».

## NO_VERIFICADO / limitaciones

- Formatos de reporte distintos al ejemplo (usan el respaldo de hoja adicional). La muestra sintética ya fue aceptada por el responsable el 2026-10-16.
- Drive y cualquier proveedor externo (la aprobación ya no los usa).
- Guardado real de la descarga en el navegador, tema oscuro y navegación completa por teclado de la pantalla de revisión, y móvil físico.
- Tutores de otra carrera (se probó con dos tutores sobre el mismo alumno); revisión y reenvío simultáneos no son alcanzables por diseño.
- Revisión del mismo agente (no independiente).

## Revisión y acta de cierre

La revisión técnica contra el diff y la spec concluyó APPROVED el 2026-10-16 en su primera pasada, sin defectos materiales; la visual se limitó a lo cambiado tras el preview. Fue del mismo agente, no independiente. Observaciones no bloqueantes, ahora limitaciones: falta de filtro por período en la bandeja del tutor, COMMIT ambiguo que podría borrar un firmado recién confirmado y limpieza de huérfanos sin ejecución automática.

El responsable otorgó aprobación de cierre el 2026-10-16 con `CLOSE C06 + NEXT SPEC`, sujeta a revisión aprobada y evidencia suficiente, y aceptó antes la muestra de firma sintética. C06 queda DONE con las limitaciones de la spec. El commit local de implementación se hizo con el cierre; no hay push.

## Decisiones aplicadas

DP-02 (la corrección nunca mueve obligación ni período) y DP-07 (firma en la celda «Firma» de la fila «Tutor académico», con hoja adicional como respaldo), resueltas el 2026-10-16 y registradas en `docs/analysis/DECISIONES_PENDIENTES.md`.
