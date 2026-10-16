# Evidencia C03 — grupos e incorporación

Fecha de ejecución: 2026-10-15. Estado de la spec: IN_PROGRESS.

## Evidencia real

- Migración `003_grupos_incorporacion.sql` aplicada al volumen local C01 con PostgreSQL 16. La primera ejecución abortó completa al detectar dos incorporaciones activas del fixture C01. Se cerró únicamente la incorporación sintética anterior, conservando ambas filas, y la migración terminó correctamente.
- `docker compose up --build -d --wait api web`: API, web y PostgreSQL saludables.
- `docker compose --profile verification run --rm --build smoke python scripts/smoke_c03.py`: PASS con HTTP y PostgreSQL reales. Verificó catálogo cerrado, rechazo de Educación, creación transversal de grupos, nomenclaturas TII/MER, prohibición de escritura para coordinador/alumno, preview y aplicación CSV, reintento idempotente, conflicto sin escritura, promoción entre dos períodos, dos pertenencias históricas, alta/baja/cambio de empresa, una sola incorporación activa y cuenta del alumno conservada.
- `docker compose exec -T api python -m unittest tests.test_c03_organization tests.test_query_catalog tests.test_route_contract -v`: 7 pruebas PASS.
- `node --test integration-tests/api-contract.test.mjs`: 57 llamadas del repositorio frontend validadas contra 57 rutas backend.
- `node --test tests/*.test.js` en frontend: 21 pruebas PASS.
- Build Vite: 99 módulos transformados, build PASS. Conserva advertencias de accesibilidad/estilos anteriores en otras superficies y modales heredados; las etiquetas de los controles añadidos por C03 quedaron asociadas.

Los datos usados son sintéticos y se conservaron para inspección. El smoke no imprime contraseñas ni tokens.

## Evidencia simulada

- Las pruebas unitarias validan el catálogo cerrado, parser CSV, máximo de 500 filas, duplicados, contenido de migración y que un conflicto detenga el lote antes de ejecutar inserciones.
- El contrato estático comprueba las rutas, parámetros y llamadas del repositorio, pero no sustituye la ejecución HTTP real anterior.

## No verificado

- La fuente institucional externa que contendría el código exacto de Mercadotecnia no está incluida en el proyecto anterior ni en el volumen local C01: ese código todavía contenía Educación. La implementación usa `MER` y `LIC. NME MERCADOTECNIA`; TII/LOG y la fórmula completa sí se preservaron literalmente de la fuente disponible. Este punto debe compararse con la base institucional autoritativa durante la revisión.
- No se probaron integraciones externas (Drive, proveedor de correo, calendario, reportes/PDF), excluidas del alcance C03.
- No se hizo recorrido en dispositivo móvil físico.

## Preview visual parcial (2026-10-15, REAL)

Navegador integrado sobre el build desplegado (`127.0.0.1:5174`), sesión de un tutor sintético creado solo para el preview en la BD local. Verificado: login y menú del tutor; `?vista=grupos` en 616 px, 375 px (móvil emulado) y 1280 px (dos columnas); el selector de carrera ofrece exactamente LOG, MER y TII y no aparece Educación; formularios de grupo, gestión individual y promoción con vista previa; `?vista=empresas` en 375 px; sin desbordamiento horizontal en 375 px en ambas vistas.

Recorrido adicional en la UI (REAL, mismo entorno, datos sintéticos `99003000x`; el archivo se adjuntó por script porque el navegador integrado no tiene selector de archivos):
- CSV: vista previa "2 filas listas para aplicar" → "Confirmar lote completo" → "2 alumnos insertados". Mismo archivo otra vez: "0 filas listas… 2 filas ya pertenecen al grupo en este período" (idempotente). Matrícula existente con nombre distinto en otro grupo: "Fila 2 (990030001): La matrícula ya existe con un nombre diferente", con aviso de corregir conflictos y sin botón de confirmar.
- Incorporación: búsqueda por matrícula con Enter (teclado), perfil con carrera, grupo, estatus y empresa; empresa + fecha real de inicio → "Incorporación activa" con historial `2026-09-07 — Activa`.
- Baja: confirmación explícita ("la cuenta, los grupos por período y el expediente se conservan"), fecha de baja → historial `2026-09-07 — 2026-10-16`, estatus Inactivo, cuenta conservada.
- `26TII-1-I-1A` x2: NO es un duplicado. Son dos grupos distintos que difieren solo en `ciclo_ingreso` (`e1f789b0ef` y `e496cc7189`, de smokes distintos); el índice único `grupos_identidad_unica` incluye `ciclo_ingreso` y lo permite. Como la nomenclatura institucional no incluye el ciclo, el selector los muestra con la misma etiqueta.

Revisión y correcciones (2026-10-15): ver sección Revisión de la spec. Tras corregir H1/H2: `unittest discover` 48/48 (SIMULADA para las pruebas nuevas, que inspeccionan SQL) y `smoke_c03.py` PASS (REAL) con período anterior (`alumnos.grupo_id` no retrocede; tres pertenencias) y consulta real q000 que devuelve la empresa de la incorporación vigente. No se re-ejecutaron los tests JS (Node no disponible en el host).

M1 (2026-10-15): migración 003 reaplicada al volumen local con `-f` (`cuatrimestre` opcional, idempotente); `unittest discover` 51/51 (SIMULADA) y `smoke_c03.py` PASS (REAL) con aserciones HTTP sobre `asignaciones`, `alumnos-sin-reporte` (grupo por período), directorio sin filas duplicadas y `cuatrimestre IS NULL` en incorporaciones nuevas. Dos tropiezos del entorno, no del código: canalizar la migración por PowerShell altera las tildes (aborta por carrera desconocida) y el limitador de login en memoria devolvió 429 tras ejecuciones seguidas del smoke; se reinició la API local. Sin verificación visual de este cambio (solo backend). Tests JS no re-ejecutados.

H3/H4 (2026-10-15): esquema base + migración 003 sobre PostgreSQL 16 vacío y descartable (grupo MER válido, tres carreras, segunda ejecución idempotente) — REAL. Selectores con `· ingreso <ciclo>` comprobados en la interfaz — REAL. `unittest discover` 50/50 y `smoke_c03.py` PASS tras reconstruir.

Observaciones de UX (1, 2 y 3 corregidas; la 3 como H4):
1. Tras reintentar un CSV con 0 filas por aplicar, el botón "Confirmar lote completo" sigue visible.
2. Tras la baja, "Empresa actual" sigue mostrando la empresa de la incorporación finalizada junto a estatus Inactivo.
3. Dos grupos con igual etiqueta en selectores si coinciden plan/zona/modalidad/cuatrimestre/letra en ciclos distintos.

Aún no verificado: tab/foco visible en todos los controles nuevos más allá de la búsqueda con Enter, cambio de empresa con una incorporación vigente desde la UI, y dispositivo móvil físico.
- ~~Suite completa del backend 44/45~~: resuelto el 2026-10-15. Tras reconstruir la imagen de la API (el contenedor tenía código previo a la corrección de 51 a 57 rutas), `unittest discover` pasa 45/45 (REAL).

No se realizó commit ni push.

## Revisión y acta de cierre

La revisión técnica contra el diff y la spec concluyó APPROVED el 2026-10-15, incluido el cambio M1; antes hubo una revisión CHANGES_REQUESTED cuyo defecto (M1) y los hallazgos H1–H4 se corrigieron y verificaron. La parte visual recorrió grupos, CSV, incorporación, baja, promoción y selectores en el build desplegado (escritorio y móvil emulado). Fue revisión del mismo agente, no independiente. q015, q017 y q006 se ejecutaron de solo lectura contra la base local durante la última revisión.

El responsable del proyecto otorgó aprobación de cierre de C03 el 2026-10-15 con `CLOSE C03 + NEXT SPEC`, sujeta a revisión aprobada y evidencia suficiente. Se marca DONE con las limitaciones de la spec: código `MER` sin contrastar con la base institucional autoritativa, tests JS no re-ejecutados, foco con Tab y móvil físico sin verificar, e integraciones de C04–C10 NO_VERIFICADAS. No se hizo commit ni push. C04 queda solo documentada en DRAFT; no se implementó.
