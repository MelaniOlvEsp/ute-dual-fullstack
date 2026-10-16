# C03 — Grupos e incorporación

Estado: DONE
Fecha: 2026-10-15 (cierre: 2026-10-15)
Responsable de aprobación: responsable del proyecto
Dependencias: C02 DONE. DP-05 resuelta por el responsable del proyecto el 2026-10-15. Sin decisiones bloqueantes: DRAFT → READY → IN_PROGRESS el 2026-10-15.

## Problema y resultado esperado

La base actual permite crear grupos, cargar alumnos y asociar empresa, pero guarda el grupo actual directamente en `alumnos.grupo_id` y la incorporación en `alumnos_dual` por un texto de cuatrimestre. Cambiar estos valores puede reescribir la situación actual sin representar de forma estable el grupo, grado e incorporación que correspondían a cada período. El esquema canónico del refactor contiene Educación donde la base institucional ya definía Mercadotecnia; C03 debe corregir esa divergencia y conservar literalmente los nombres, abreviaciones y nomenclaturas institucionales existentes.

Resultado esperado: el tutor crea grupos con las tres carreras oficiales, autoriza matrículas por carga individual o CSV, registra la pertenencia del alumno por período y administra empresa, fecha real de inicio y baja de Dual. Cada cambio conserva el historial anterior; terminar la incorporación detiene su vigencia sin desactivar la cuenta ni borrar expediente.

## Fuentes y alcance

- US: [US-02 y US-04](../../docs/analysis/ESPECIFICACION_FUNCIONAL.md).
- RN: [RN-02, RN-04, RN-05, RN-06 y RN-29](../../docs/analysis/REGLAS_DE_NEGOCIO.md).
- AC: [AC-05](../../docs/analysis/CRITERIOS_DE_ACEPTACION.md).
- Documentos enlazados: [plan maestro](../../docs/construction/PLAN_MAESTRO.md), [modelo de datos](../../docs/analysis/MODELO_DE_DATOS.md), [UX](../../docs/analysis/UX_Y_FLUJOS.md), [contrato API](../../docs/analysis/CONTRATO_API.md), [archivos e importaciones](../../docs/analysis/CONTRATO_DE_ARCHIVOS_E_IMPORTACIONES.md), [roles](../../docs/analysis/MATRIZ_DE_ROLES_Y_PERMISOS.md) y [DP-05](../../docs/analysis/DECISIONES_PENDIENTES.md).

Incluye:

1. Catálogo cerrado a exactamente tres carreras: Tecnologías de la Información e Innovación Digital (TIC), Logística y Mercadotecnia, conservando los nombres y abreviaciones ya definidos en la base institucional. Educación y cualquier otra carrera se eliminan del esquema, formularios, filtros y fixtures.
2. Creación y consulta de grupos con la nomenclatura institucional ya definida en la base; tutor transversal a las tres carreras. No rediseñar su fórmula, campos, formato ni separadores.
3. Alta individual y carga CSV `matricula,nombre` sobre un grupo seleccionado, con vista previa, validación, conflictos explícitos, aplicación transaccional e idempotencia. La carga autoriza el registro institucional pero no implica incorporación laboral.
4. Historia de pertenencia alumno–grupo por período. Un cambio agrega una nueva pertenencia y no altera grupo, grado ni nomenclatura de períodos anteriores.
5. Catálogo de empresas e incorporación del alumno con empresa y fecha real de inicio. La incorporación puede cruzar períodos sin duplicarse por cada uno.
6. Baja de Dual con fecha y resumen de efecto. Conserva incorporación, pertenencias, cuenta y referencias históricas; no se implementa mediante borrado ni mediante la desactivación de acceso de C02.
7. Contratos, migración aditiva para instalaciones C01, fixtures, documentación, pruebas y preview de los recorridos afectados.

Excluye: cálculo de obligaciones o semanas parciales, apertura/cierre de períodos y su zona, reportes/archivos, versiones, firma, promedio, expediente integral y producción. Esos comportamientos pertenecen a C04–C10 y conservan sus DP propias.

## Decisiones

Confirmadas: el catálogo admite exclusivamente Tecnologías de la Información e Innovación Digital (TIC), Logística y Mercadotecnia. Educación y cualquier otra carrera quedan fuera. Sus abreviaciones y nomenclaturas son exactamente las ya definidas en la base institucional y no están sujetas a rediseño. Tutor transversal; carga de matrícula/nombre habilita registro; una pertenencia de grupo por alumno y período; incorporación con fecha real de inicio; baja sin borrar historia ni desactivar cuenta; no migrar datos productivos porque la base aprobada parte vacía.

Propuestas técnicas incluidas para la futura aprobación de implementación:

- Usar identificadores para carrera, grupo, período, empresa e incorporación; evitar relaciones por textos de cuatrimestre o nomenclatura.
- Crear historia alumno–grupo con unicidad `(matricula, periodo_id)` y auditoría básica; mantener `alumnos.grupo_id` solo como compatibilidad transitoria si el diff de implementación demuestra que aún es necesario.
- Permitir como máximo una incorporación activa por alumno. Un cambio de empresa cierra explícitamente la incorporación anterior con fecha y crea otra; nunca sobrescribe empresa histórica.
- CSV UTF-8 con encabezados exactos `matricula,nombre`, matrícula textual, máximo propuesto de 500 filas, preview antes de aplicar y lote atómico. Un reintento idéntico no duplica; una matrícula existente con datos incompatibles se reporta como conflicto y no se sobrescribe silenciosamente.
- Promoción individual y masiva con vista previa y confirmación. El tutor selecciona período y grupo destino; el grado resulta del grupo destino. Repetidores permanecen en su grupo salvo selección manual y cualquier conflicto cancela el lote completo antes de aplicar cambios.
- Mantener 404 para objetos ajenos/inexistentes, 403 para rol sin permiso y autorización en servidor. Proteger exportaciones contra fórmulas de hoja de cálculo si se agrega una salida tabular.

Pendientes bloqueantes: ninguna. DP-05 quedó resuelta el 2026-10-15: la base institucional es la fuente autoritativa del catálogo, abreviaciones y nomenclatura, y el responsable aprobó la regla de promoción descrita arriba. Antes de modificar el esquema, la implementación deberá obtener y fijar esos valores existentes en una migración y pruebas de regresión; no inferir ni sustituir abreviaciones.

## Contratos y cambios

Métodos/rutas/DTO y compatibilidad: reutilizar las rutas existentes de grupos, carga individual/CSV, empresas y asignaciones cuando expresen el contrato aprobado; crear rutas explícitas de pertenencia por período o incorporación solo donde la semántica actual obligue a ello. No cambiar silenciosamente la forma que consume el frontend. Documentar DTO/OpenAPI y actualizar cliente en el mismo incremento.

Datos, restricciones y conservación: reemplazar la dependencia funcional de `alumnos.grupo_id` y `alumnos_dual.cuatrimestre` por relaciones históricas con FK e identificadores. La migración elimina Educación y cualquier otra carrera del catálogo permitido y sustituye las opciones correspondientes en cliente/API. Si encuentra grupos, alumnos o expediente vinculados a una carrera excluida, falla con diagnóstico antes de modificar datos; no borra ni reasigna historia silenciosamente. Migración aditiva e idempotente sobre el esquema C01; no borrar reportes, mensajes, usuarios ni asociaciones previas. No usar cascadas que eliminen expediente.

Permisos y estados: tutor crea/edita grupos, matrículas, pertenencias e incorporaciones; coordinador y tutor consultan según la matriz vigente; alumno solo consulta su información cuando exista una ruta de perfil. La baja de Dual es distinta de la baja de cuenta. Estados deben distinguir incorporación activa/finalizada y carga preparada/aplicada/fallida.

Archivos/módulos previstos: esquema y migración C03; casos de uso, consultas, DTO y routers de carrera/tutor; consumidor y pantallas de organización; contratos, fixtures, pruebas y documentación relacionada. La lista definitiva se fija al pasar a READY después de inspeccionar el diff base.

Comportamiento ante fallos/reintentos: operaciones individuales y por lote deben ser transaccionales. Duplicados o conflictos devuelven resultado estable sin reasignar silenciosamente; dos solicitudes concurrentes no crean dos pertenencias para el mismo período ni dos incorporaciones activas. Si falla una fila del lote aprobado, no queda aplicación parcial.

## Verificación

| AC | Prueba o recorrido | Nivel y datos | Resultado |
|---|---|---|---|
| C03-AC1 / US-02 | Tutor crea grupos válidos únicamente para TIC, Logística y Mercadotecnia; nombres, abreviaciones y nomenclatura coinciden literalmente con la base institucional. Educación u otra carrera se rechazan y no aparecen en la interfaz | HTTP + PostgreSQL reales; fixtures sintéticos y comparación con la fuente institucional | REAL local: catálogo, rechazo y fórmula PASS. Comparación externa del código MER: NO_VERIFICADA |
| C03-AC2 / RN-02 | Alta individual y CSV muestran preview; autorizan registro; duplicado, conflicto, formato inválido, reintento y concurrencia no sobrescriben ni duplican | HTTP + PostgreSQL reales; CSV sintético | REAL: PASS en smoke y en la interfaz (vista previa, aplicación, reintento idempotente, conflicto sin botón de confirmar); reglas de formato/atomicidad adicionales SIMULADAS |
| C03-AC3 / AC-05 | Alumno cambia de grupo en un nuevo período y el anterior conserva grupo, grado y nomenclatura | HTTP + consultas PostgreSQL antes/después | REAL: PASS, dos pertenencias conservadas |
| C03-AC4 / RN-06 | Empresa e inicio reales persisten entre períodos; cambio conserva empresa previa; baja con fecha conserva cuenta e historial | HTTP + PostgreSQL reales | REAL: PASS, dos incorporaciones y una activa; asignación a períodos por fechas verificada por HTTP (M1) y baja/alta recorridas en la interfaz |
| C03-AC5 / RN-04/29 | Alumno no modifica organización; tutor opera las tres carreras; IDs ajenos y operaciones no autorizadas se rechazan | Negativos HTTP reales | REAL: permisos PASS; IDs inexistentes cubiertos por contratos/casos existentes |
| C03-AC6 | Flujos de grupos, importación, incorporación y baja explican efectos y funcionan en escritorio/móvil con teclado | Preview visual del build desplegado | REAL: build PASS y preview visual en el navegador integrado (escritorio 1280 px, móvil emulado 375 px sin desbordamiento) de grupos, CSV, incorporación, baja, promoción y selectores; búsqueda por teclado con Enter. NO_VERIFICADOS: foco con Tab en todos los controles nuevos y dispositivo móvil físico |

## Evidencia de implementación

La implementación y su evidencia están registradas en [evidencia.md](evidencia.md). El smoke C03 ejecuta HTTP y PostgreSQL reales; las pruebas del parser/atomicidad usan dobles controlados. Las integraciones excluidas siguen NO_VERIFICADAS.

## Revisión

Veredicto: CHANGES_REQUESTED en la revisión del 2026-10-15 por M1; M1 corregido y verificado después (ver abajo). H1–H4 también corregidos. Sin hallazgos abiertos conocidos. Nueva revisión técnica del 2026-10-15 contra el diff y la spec, incluido M1: APPROVED, sin defectos materiales nuevos; q015, q017 y q006 se ejecutaron de solo lectura contra la base local (columnas correctas, 9/9/13 filas, ninguna incorporación sin período). Observación no bloqueante: q009, q013 y q014 de `dual_coordinador_dual.py` quedaron sin uso y q009/q013 apuntan a la restricción `alumnos_dual_unico` ya eliminada; retirarlas en C04. Aprobación humana de cierre recibida el 2026-10-15 (ver abajo). Las revisiones fueron hechas por el mismo agente, no independientes.
- M1 (CORREGIDO 2026-10-15): la incorporación guardaba el grado del grupo (p. ej. `2`) en `alumnos_dual.cuatrimestre`, columna que `asignaciones`, `alumnos-sin-reporte` y `alumnos-atrasados` comparaban con etiquetas de período, por lo que esas incorporaciones nunca aparecían. Ahora: (a) la incorporación ya no escribe `cuatrimestre` y la migración 003 vuelve la columna opcional (dato heredado); (b) q005, q006, q015 y q017 asignan la incorporación a un período por solapamiento de fechas (inicio/baja contra inicio/fin del período; si el período no tiene fechas, solo cuenta si sigue activa) y q015/q017 toman el grupo de la pertenencia de ese período; (c) el directorio de alumnos (q003) une la incorporación más relevante (activa primero) en lugar de todas, para no duplicar alumnos con historial; (d) q005 y q006 ahora devuelven `fecha_inicio` y `fecha_baja`, que `AsignacionOut` exigía y las consultas anteriores omitían. Alcance restante para C04–C10 (no se tocó): el filtro por período del directorio (`g.cuatrimestre::text`), los reportes y expedientes (q003 aprobados, q009/q012 del alumno y exportaciones) siguen tratando el grado como período.
Revisor y modalidad: el mismo agente que implementó (Claude, contra el diff y la spec). NO es una revisión independiente.
Hallazgos materiales:
- H1 (CORREGIDO 2026-10-15): `dual.organization.set_current_group` actualizaba `alumnos.grupo_id` en cada inserción de pertenencia, también al registrar un período anterior, por lo que el "grupo actual" podía retroceder. Ahora se deriva de la historia: la pertenencia del período más reciente (año; luego Enero-Abril < Mayo-Agosto < Septiembre-Diciembre; desempate por `asignado_en`). El orden por etiqueta es válido porque `ciclos_dual.cuatrimestre` y `periodo_label` tienen restricción de formato.
- H2 (CORREGIDO 2026-10-15, alcance acotado): la bandeja de reportes (`dual.coordinador_dual.q000`) ya ordenaba por `created_at`, pero ignoraba la vigencia y su respaldo `LIMIT 1` carecía de orden. Ahora es una sola subconsulta determinista: incorporación activa primero, luego mayor `fecha_inicio`, `created_at` e `id`. Fuera de alcance y abierto para C04–C10: reportes, expedientes y las consultas q015/q017 siguen leyendo el grupo vigente (`alumnos.grupo_id`) y relacionan la incorporación por el texto `cuatrimestre`, no por el grupo ni la empresa del período del reporte.
- H3 (CORREGIDO 2026-10-15): `schema_dual_desde_cero.sql` ya define solo TII, LOG y MER (sin Educación ni `'EDU'`). Verificado en un PostgreSQL 16 descartable y vacío: el esquema base acepta un grupo MER (`26MER-1-I-2B`), la migración 003 se aplica encima, deja las tres carreras y una segunda ejecución es idempotente (REAL). Los volúmenes ya instalados siguen cubiertos por la migración 003.
- H4 (CORREGIDO 2026-10-15): el listado de grupos devuelve `ciclo_ingreso` y los selectores de grupo activo, origen y destino de promoción muestran `nomenclatura · ingreso <ciclo>`. La nomenclatura institucional no se modificó. Verificado en la interfaz: los dos `26TII-1-I-1A` aparecen como `… · ingreso e496cc7189` y `… · ingreso e1f789b0ef` (REAL; los ciclos con formato hexadecimal vienen de smokes anteriores).
- La migración no rellena `alumno_grupo_periodo` para alumnos existentes en instalaciones C01 con datos (aceptado: la base aprobada parte vacía).
Correcciones y verificación focal (2026-10-15): (1) `puede_aplicar` ahora exige filas válidas, de modo que un reintento sin cambios no ofrece "Confirmar lote completo" (UX 1); (2) "Empresa actual" muestra "Sin asignar" cuando la incorporación está finalizada (UX 2; el historial conserva la empresa); (3) la matrícula exige dígitos ASCII, no Unicode. Tras reconstruir: backend 45/45, build web y smoke C03 PASS (REAL). Corrección de H1/H2: tres pruebas nuevas (matrícula ASCII, solo repetidos no aplicable, consultas de grupo vigente y empresa) → backend 48/48 (SIMULADA); el smoke ahora registra un período anterior y verifica en PostgreSQL que `alumnos.grupo_id` no retrocede, que hay tres pertenencias y que la consulta real de la bandeja de reportes devuelve la empresa de la incorporación vigente → PASS (REAL). Corrección de M1: una prueba nueva (la incorporación no escribe `cuatrimestre`; q005/q006/q015/q017 usan fechas de período y q015/q017 la pertenencia) → backend 51/51 (SIMULADA); migración 003 reaplicada al volumen local (idempotente; `cuatrimestre` ahora acepta NULL) y smoke C03 REAL ampliado: `asignaciones` devuelve 2 incorporaciones en el período 1 y 1 activa (empresa B) en el período 2, `alumnos-sin-reporte` muestra el grupo de cada período (origen y destino), el directorio devuelve una fila por alumno y ninguna incorporación nueva guarda `cuatrimestre` → PASS (REAL). Corrección de H3/H4: dos pruebas nuevas (esquema base sin Educación; el listado expone `ciclo_ingreso`) → backend 50/50, smoke C03 PASS y build web (Compose) saludable tras reconstruir. Tests de frontend/contrato JS: NO re-ejecutados (Node no disponible en el host); verificación visual de las correcciones UX: NO_VERIFICADA.
Limitaciones: el valor `MER` y el nombre `LIC. NME MERCADOTECNIA` siguen sin contrastarse con la base institucional autoritativa. Foco con Tab, móvil físico e integraciones: NO_VERIFICADOS.

## Aprobaciones y cierre

Aprobación de implementación: recibida mediante `IMPLEMENT C03` en este chat el 2026-10-15. Autoriza el alcance de esta spec, contratos, fixtures y documentación afectados; no autoriza C04, commit ni push.
Aprobación de cierre: otorgada por el responsable del proyecto el 2026-10-15 mediante `CLOSE C03 + NEXT SPEC`, sujeta a revisión aprobada y evidencia suficiente. Se verificó: revisión técnica APPROVED (2026-10-15, incluido M1; mismo agente, no independiente) y evidencia REAL para el núcleo funcional de C03-AC1 a AC6. Cierre con las limitaciones listadas abajo.
Resumen final: catálogo cerrado a TII, LOG y MER (esquema base y migración 003, sin Educación); grupos con la nomenclatura institucional y ciclo de ingreso visible en selectores; alta individual y CSV `matricula,nombre` con vista previa, conflictos, idempotencia y lote atómico; pertenencia alumno–grupo por período con grupo vigente derivado de la historia; promoción con vista previa y confirmación; incorporación con empresa y fecha real de inicio, una sola activa, baja con fecha que conserva cuenta e historial, y asignación a períodos por fechas (consultas de asignaciones y pendientes, directorio sin duplicados); contratos, cliente, fixtures, smoke C03 y documentación actualizados.
Pruebas: backend 51/51 (SIMULADA para parser, atomicidad y consultas); smoke C03 sobre HTTP y PostgreSQL reales; migración y esquema base verificados en PostgreSQL 16 vacío; preview visual en escritorio y móvil emulado. Detalle en [evidencia.md](evidencia.md).
Limitaciones aceptadas al cierre: (1) el código `MER` y el nombre `LIC. NME MERCADOTECNIA` no se contrastaron con la base institucional autoritativa (la fuente disponible solo confirma TII, LOG y la fórmula); (2) tests JS y de contrato no re-ejecutados tras las últimas correcciones (Node no disponible en el host; el build web de Compose sí pasa); (3) foco con Tab y dispositivo móvil físico; (4) integraciones externas, PDF, calendario, reportes y expediente, que pertenecen a C04–C10; (5) reportes, expedientes y el filtro por período del directorio aún tratan el grado como período; (6) q009, q013 y q014 sin uso, por retirar en C04.
Siguiente spec: [C04 — Calendario y pendientes](../C04-calendario-y-pendientes/spec.md), que pasó a READY el 2026-10-15 tras resolver DP-01, DP-03 y DP-04 en lo que necesita.
Commit/push: no autorizados; no se hicieron.
