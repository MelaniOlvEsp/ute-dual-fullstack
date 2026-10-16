# Evidencia C07 — Cierre y calificación

Fecha: 2026-10-16. Estado de la spec: DONE (cerrada el 2026-10-16; sin push).
Clases: REAL = HTTP, PostgreSQL y almacenamiento reales del Compose local (datos sintéticos); SIMULADA = pruebas con dobles; NO_VERIFICADA = no observado.

## Resumen por criterio

| Criterio | Clase | Fuente |
|---|---|---|
| C07-AC1 cierre por ID con efectos inmediatos | REAL | `smoke_c07.py` |
| C07-AC2 permisos, idempotencia y orden transaccional con la entrega | REAL (bloqueos de fila reales en ambos órdenes) | smoke C07 |
| C07-AC3 promedio 9.00, «Sin calificación» y 8.50 | REAL; empates de redondeo SIMULADA | smoke C07, `test_c07_cierre.py` |
| C07-AC4 pendiente impide finalizar; resultado congelado e inmutable | REAL | smoke C07 |
| C07-AC5 otro período recibiendo mientras se finaliza | REAL | smoke C07 |
| C07-AC6 etiqueta «No recibida por cierre» | REAL parcial (instante de cierre movido por SQL) + SIMULADA (frontera) | smoke C07, pruebas de dominio |
| C07-AC7 promedio provisional y final por período | REAL (directorio por HTTP tras corregir M1) | smoke C07 |
| C07-AC8 panel y avisos | REAL parcial | navegador integrado |

## Ejecuciones

- Backend `python -m unittest discover -s tests`: 158 pruebas OK (26 nuevas de C07, dos de ellas del directorio por período tras M1: promedio con `Decimal`, etiqueta por cierre, casos de uso de cierre y finalización con dobles, bloqueo compartido en la entrega, contratos SQL). SIMULADA.
- JS: 29/29 (textos de confirmación). Contrato estático y de integración: 65 llamadas contra 65 rutas.
- Smoke C07 PASS con HTTP, PostgreSQL y almacenamiento reales: cierre por ID sin renombrar y con fecha civil; entrega y reenvío bloqueados; revisión con la recepción cerrada; finalización rechazada con un pendiente y luego aceptada; promedios 9.00 (8, 9, 10 y un rechazo), «Sin calificación» (sin aprobados) y 8.50 congelados con su detalle; inmutabilidad y protección del período finalizado en la base; orden transaccional en ambos sentidos con bloqueos de fila reales (entrega en vuelo hace esperar al cierre; cierre confirmado primero deja la entrega con 409); otro período recibiendo mientras se finaliza; etiqueta «No recibida por cierre» con el instante de cierre movido por SQL; permisos; período cerrado que no se reabre.
- Regresión: smokes C01 a C06 PASS (C02, C04, C05 y C06 se adaptaron a la ruta nueva y al ayudante `smoke_periodos.py`).
- Migración `007_cierre.sql`: instalación en base nueva (esquema + 003 a 007) sin errores; reaplicación idempotente; cinco disparadores y dos tablas presentes.
- Vite build: sin avisos en `PeriodosDual`, `CoordinadorDual` ni `ReportesDual`.

## Visual REAL (navegador integrado, datos sintéticos)

Coordinador en escritorio: el panel muestra estados de recepción y evaluación, calendario, conteos y promedios provisionales por alumno; «Cerrar recepción» muestra la consecuencia con el período exacto y pide confirmación; tras cerrar, «Finalizar evaluación» queda deshabilitada con el motivo «Quedan N reportes pendientes de revisión»; con cero pendientes la finalización muestra la consecuencia, finaliza y deja los promedios como finales sin botones de acción. En 375 px no hay desborde horizontal. Alumna: la semana en curso del período cerrado aparece como «No recibida por cierre» con el motivo de bloqueo.

## Revisión y corrección (2026-10-16)

La primera revisión (técnica, del mismo agente) concluyó CHANGES_REQUESTED: M1, el directorio de alumnos respondía 500 al filtrar por período porque el filtro contenía « AND » y `resolve_query` lo rechazaba («Filtro no permitido»); lo había pasado por alto porque mi prueba y mi smoke ejecutaban el SQL directamente. Se corrigió con un filtro sin « AND » definido una sola vez, dos pruebas que pasan por `resolve_query`, una llamada HTTP en el smoke C07 y se agregó el aviso del período para el tutor. Verificación: 158 pruebas de backend, smokes C02, C03 y C07 PASS, JS 29/29, contrato 65/65 y Vite sin avisos; visual: el aviso del tutor y el directorio con período cargan. Revisión focal del mismo agente sin hallazgos nuevos.

## NO_VERIFICADO / limitaciones

- Teclado completo, tema oscuro y móvil físico del panel; la lista de períodos no se paginó.
- Cierre anticipado real (se movió el instante de cierre con SQL); empates de redondeo solo en pruebas de dominio.
- El directorio excluye a quienes ya tienen baja (C08), por lo que los promedios de los alumnos de baja de la prueba se comprobaron por SQL y por el resumen del período.
- Un cierre sin finalizar puede revertirse con SQL directo: la base solo protege a los períodos finalizados.
- Drive y cualquier proveedor externo. Revisión del mismo agente (no independiente).

## Acta de cierre

La segunda revisión técnica (tras corregir M1) concluyó APPROVED el 2026-10-16 sin defectos materiales; la visual se limitó a lo cambiado tras el preview. El responsable otorgó aprobación de cierre el 2026-10-16 con `CLOSE C07 + NEXT SPEC`, sujeta a revisión aprobada y evidencia suficiente. C07 queda DONE con las limitaciones de la spec. El commit local de implementación se hizo con el cierre; no hay push.

## Decisiones aplicadas

DP-04 (un solo período con recepción abierta; el anterior se revisa y finaliza mientras el nuevo recibe), DP-03 («No recibida por cierre» para semanas cortadas, «Atrasada» para las ya terminadas) y DP-11 (dos decimales, HALF_UP en el tercero, resultado congelado), resueltas el 2026-10-16 y registradas en `docs/analysis/DECISIONES_PENDIENTES.md`.
