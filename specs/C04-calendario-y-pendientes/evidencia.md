# Evidencia C04 — calendario y pendientes

Fecha de ejecución: 2026-10-15. Estado de la spec: IN_PROGRESS. Entorno: Docker Compose local (PostgreSQL 16, API, web), datos sintéticos.

## Evidencia real

- Migración `004_obligaciones.sql` aplicada dos veces al volumen local con `-f` (segunda ejecución solo avisos "ya existe": idempotente). Antes, los 27 períodos sintéticos de smokes anteriores (todos con fechas relativas a "hoy" y solapadas entre sí) se alinearon a las fechas canónicas de su etiqueta con una única sentencia sobre la BD local de pruebas verificada; sin esa alineación la migración aborta por diseño. No se tocó ningún otro dato.
- `docker compose --profile verification run --rm smoke python scripts/smoke_c04.py`: PASS con HTTP y PostgreSQL reales.
  - Parte 1 (fecha de hoy real, America/Mexico_City): incorporación en miércoles con primera semana parcial (A) y en lunes sin parcial (B), obligaciones propias por incorporación; primer, segundo y tercer ordinal; semanas anteriores ATRASADA y la vigente PENDIENTE, sin ninguna semana futura; período de cada semana igual al del domingo; reporte recibido marca RECIBIDA sin bloquear las demás; bandeja del tutor con las semanas de A y B (no las de alumnos dados de baja) y grupo del período; baja a mitad de semana con última semana parcial y baja retroactiva que excluye (sin borrar) semanas ya generadas; 6 lecturas y 4 bandejas concurrentes sin duplicar obligaciones (3 filas para A, ningún intervalo duplicado en toda la tabla); alumno solo ve lo propio, ajeno 403, inexistente 404, sin token 401; apertura de período solapado 409 sin fila creada; restricción de exclusión de la base rechaza un período solapado.
  - Parte 2 (casos de uso reales sobre la misma BD con reloj inyectado, porque el reloj del servidor no se puede mover): incorporación el 30 de abril con semana que termina en mayo → período Mayo–Agosto, no cambia al consultar en junio (AC-07); el domingo la semana sigue PENDIENTE y el lunes pasa a ATRASADA (AC-08); ordinal continuo y estable al filtrar por período; obligaciones generadas sin período lo reciben cuando el período se abre por la API, y el período se cierra después.
- `docker compose exec -T api python -m unittest discover -s tests`: 73 pruebas PASS.
- Regresión real: smokes C01, C02 y C03 PASS tras las correcciones (ver abajo).
- Node de la imagen web: `node --test integration-tests/api-contract.test.mjs` (59 llamadas del cliente validadas contra 59 rutas del backend) y `node --test tests/*.test.js` (21 PASS). Build Vite de Compose saludable.
- Preview visual en el navegador integrado, build desplegado, usuarios sintéticos (tutor y alumno creados solo para el preview):
  - Tutor, "Empresas y asignaciones": la fecha por defecto del formulario es 2026-10-15 (hoy en México; antes mostraba la fecha UTC un día adelantada). Tras activar una incorporación el 2026-09-30 (miércoles), "Semanas del alumno" muestra Semana 1 parcial (30 sep – 4 oct), Semana 2 atrasada y Semana 3 pendiente, con fechas correctas (sin desfase de zona) y período Septiembre–Diciembre 2026. Móvil 375 px sin desbordamiento horizontal.
  - Alumno, "Reportes Dual": panel "Mis semanas" con las mismas tres semanas; el estado se comunica con texto además de color; móvil 375 px sin desbordamiento; tema oscuro legible.

## Evidencia simulada

- Pruebas unitarias del dominio (semanas, parcialidad, baja inclusiva, ausencia de semanas futuras, corte del lunes con instantes UTC/México, instantes sin zona rechazados), casos de uso con cursores controlados (bloqueo previo, repetición idempotente, sincronización que omite lo vigente, 404 sin generar, solapamiento rechazado antes de insertar) y verificaciones sobre el texto SQL y la migración (ordinal calculado antes del filtro, exclusión de semanas posteriores a la baja, grupo por pertenencia, restricciones de unicidad y exclusión, consultas heredadas retiradas).
- El reloj del límite del lunes se controla de forma inyectada; el servidor siempre usa la fecha real.

## No verificado

- Entrega real de un reporte en la semana vigente: la carga sigue usando el flujo heredado (semana 1–18 del período abierto) hasta C05. C04 verifica el estado derivado (PENDIENTE el viernes y el domingo, ATRASADA desde el lunes), no la aceptación del archivo.
- La asociación "recibida" por fecha de fin declarada es provisional y solo se probó con un reporte sintético insertado en la base.
- (Resuelto después de la revisión del 2026-10-15) La bandeja de pendientes del tutor ("No entregado") se vio en la interfaz durante la revisión, y la apertura y el cierre de períodos se verificaron en la nueva pantalla del coordinador; ver "Corrección de M1".
- Foco con Tab en los elementos nuevos (no son controles interactivos), escritorio ancho (1280 px) de las vistas nuevas y dispositivo móvil físico.
- Integraciones externas (Drive, correo, PDF) y todo lo de C05–C10.
- `local_admin.py seed-demo` se corrigió (ver abajo) pero no se ejecutó, porque exige tablas académicas vacías.

## Correcciones a fixtures heredados

`local_admin.seed_demo`, `smoke_c01` y `smoke_c02` insertaban grupos sin `carrera_id` y vigencias sin `fecha_inicio`, obligatorios desde C03; C02 fallaba con la base actual. Se añadieron ambos valores. `smoke_c03` usaba fechas de período relativas a hoy, que la restricción de no solapamiento rechaza; ahora usa fechas canónicas con año aleatorio único y su verificación de pendientes se movió a `smoke_c04`.

## Incidentes del entorno (no del código)

- El limitador de login en memoria devolvió 429 tras varias ejecuciones seguidas de smokes; se reinició la API local entre ellas.
- Un nombre de archivo temporal largo superó el límite de ruta de Windows y obligó a restablecer la contraseña del alumno sintético de preview (por la vía del tutor).

No se realizó commit ni push.

## Corrección de M1 (revisión del 2026-10-15)

La revisión CHANGES_REQUESTED encontró que abrir períodos seguía siendo del tutor contra DP-04. Corrección: `abrir-cuatrimestre` y `cuatrimestre-actual` exigen coordinador; nueva pantalla `/dual/periodos` para el coordinador y retiro del código de períodos de la página del tutor; MP-18, `rutas.md`, `CONTRATO_API.md`, DP-04 y la spec actualizados.

- REAL: `smoke_c04.py` PASS con imagen reconstruida (tutor y alumno 403 en abrir y en estado actual; coordinador 200 en estado actual, 409 con fechas solapadas y 200 al abrir y cerrar el período posterior). Un intento previo con una imagen de smoke sin reconstruir falló justamente con 403 al usar el token del tutor, lo que confirma el cambio. Smokes C02 y C03 PASS tras reconstruir. Contrato estático 59/59 y JS 21/21 (Node de la imagen web); build Vite saludable.
- SIMULADA: `test_api_permissions.py` (nueva `test_only_coordinator_manages_periods`; las consultas de pendientes y obligaciones siguen siendo del tutor) y suite de backend 74/74.
- Visual REAL (navegador integrado, coordinador sintético creado solo para el preview): enlace "Períodos" en el menú; estado actual; abrir Enero–Abril 2030 → "Abierto" con fechas; intentar abrir otro mientras hay uno abierto → mensaje de la API en una alerta; cerrar → "Cerrado"; sin desbordamiento en 375 px. Como tutor: la página no muestra la tarjeta de períodos y `/dual/periodos` redirige a su bandeja. La base local conserva el período sintético "Enero-Abril 2030" cerrado.
- NO_VERIFICADOS: foco con Tab y tema oscuro de la pantalla nueva; móvil físico.

## Corrección de M2 (segunda revisión del 2026-10-15)

La segunda revisión encontró que no se podía abrir el período en curso: la regla heredada rechazaba cualquier inicio anterior a hoy, y las pruebas no lo detectaron porque creaban los períodos directamente en la base. Corrección: validador de modelo en `CuatrimestreAbrir` (en curso o futuro sí; terminado no, con mensaje claro) y el cliente HTTP quita el prefijo técnico "Value error,".

- REAL: `smoke_c04.py` PASS con imagen reconstruida; abre por la API el período en curso (inicio anterior a hoy), lo consulta como abierto, lo cierra, y rechaza con 422 un período terminado.
- SIMULADA: `unittest discover` 78/78 (cuatro pruebas nuevas de reglas de apertura con la fecha de hoy inyectada) y JS 22/22 (una prueba nueva del prefijo). Contrato estático 59/59 (sin rutas nuevas).
- Visual REAL (navegador integrado, coordinador sintético): el 2026-10-15 la pantalla de períodos abre Septiembre–Diciembre 2026 (estado "Abierto" con fechas), lo cierra ("Cerrado") y rechaza Mayo–Agosto 2026 con "El período terminó el 2026-08-31 y hoy es 2026-10-15; solo se pueden abrir períodos en curso o futuros", sin el prefijo técnico.
- Revisión focal (mismo agente): el cambio se limita al validador, al cliente HTTP y a sus pruebas; no toca rutas, permisos, migraciones ni obligaciones. Sin hallazgos nuevos. Observación no bloqueante, heredada: la API no valida que las fechas correspondan a la etiqueta ni limita la duración máxima; la pantalla siempre envía las fechas canónicas.
- Estado de la base local: el período sintético "Septiembre-Diciembre 2026" quedó cerrado tras la prueba.

## Revisión y acta de cierre

La revisión técnica y visual contra el diff y la spec concluyó APPROVED el 2026-10-15 en su tercera pasada. Las dos primeras fueron CHANGES_REQUESTED (M1: la apertura de períodos seguía siendo del tutor contra DP-04; M2: no se podía abrir el período en curso); ambos defectos se corrigieron y verificaron. Fue revisión del mismo agente, no independiente. La revisión visual recorrió alumno, ficha y bandeja de pendientes del tutor, y la pantalla de períodos del coordinador (móvil, escritorio, tema oscuro y teclado).

El responsable del proyecto otorgó aprobación de cierre de C04 el 2026-10-15 con `CLOSE C04 + NEXT SPEC`, sujeta a revisión aprobada y evidencia suficiente. Se marca DONE con las limitaciones de la spec: entrega real de reportes y asociación "recibida" provisional hasta C05, cierre que renombra el período (C07), fecha de inicio de incorporación sin límite inferior, períodos sin validación de coherencia con la etiqueta, grado como período en reportes y expedientes, móvil físico e integraciones NO_VERIFICADOS. Los commits locales por spec se hicieron aparte (el de C04 es `03b5a15`); este cierre no hizo commit ni push. C05 queda solo documentada en DRAFT; no se implementó.
