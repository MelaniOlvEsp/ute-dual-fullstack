# C04 — Calendario y pendientes

Estado: IN_PROGRESS
Fecha: 2026-10-15
Responsable de aprobación: responsable del proyecto
Dependencias: C03 DONE (2026-10-15). DP-01 resuelta y DP-03/DP-04 resueltas en lo que C04 necesita el 2026-10-15. Sin decisiones bloqueantes: DRAFT → READY → IN_PROGRESS el 2026-10-15.

## Problema y resultado esperado

Hoy los pendientes y atrasos se calculan sobre reportes ya cargados y sobre un número de semana 1–18 dentro del período abierto: no existe una obligación semanal que exista aunque el alumno no entregue, no hay primera semana parcial, el ordinal depende del grado/período y los períodos se identifican por texto. Un alumno incorporado un miércoles, o que cruza períodos, no tiene un calendario propio, y alumno y tutor no ven de forma coherente qué semanas están pendientes, atrasadas o recibidas.

Resultado esperado: cada incorporación genera, de forma idempotente, una obligación por semana lunes–domingo desde su fecha real de inicio (la primera puede ser parcial) hasta la semana vigente o la baja. Cada obligación resuelve su período por fechas. El alumno y el tutor ven el mismo estado de cada semana (pendiente, atrasada, recibida) sin depender de aprobaciones anteriores, y una semana futura nunca se habilita por haber cerrado la anterior.

## Fuentes y alcance

- US: [US-07](../../docs/analysis/ESPECIFICACION_FUNCIONAL.md).
- RN: [RN-06, RN-07, RN-08, RN-09, RN-10, RN-23](../../docs/analysis/REGLAS_DE_NEGOCIO.md); RN-11 solo como dato de calendario (sin calificación).
- AC: [AC-06, AC-07, AC-08](../../docs/analysis/CRITERIOS_DE_ACEPTACION.md).
- Documentos enlazados: [plan maestro](../../docs/construction/PLAN_MAESTRO.md), [modelo de datos](../../docs/analysis/MODELO_DE_DATOS.md), [contrato API](../../docs/analysis/CONTRATO_API.md), [UX](../../docs/analysis/UX_Y_FLUJOS.md), [roles](../../docs/analysis/MATRIZ_DE_ROLES_Y_PERMISOS.md), [DP-01, DP-03 y DP-04](../../docs/analysis/DECISIONES_PENDIENTES.md), [C03](../C03-grupos-e-incorporacion/spec.md).

Incluye:

1. Períodos calendario identificados por ID y fechas (inicio/fin) en la zona operativa; apertura de período por el coordinador con validación de fechas. Reutiliza `ciclos_dual`; no une por texto de cuatrimestre.
2. Obligaciones semanales por incorporación: lunes–domingo, primera semana parcial desde la fecha real de inicio, última semana parcial por baja (DP-03), generación idempotente y concurrente-segura, período resuelto por fechas (DP-01), sin techo universal de 18 semanas.
3. Estado derivado de cada obligación (pendiente, atrasada, recibida; sin entrega hasta que C05 exista) y vista de pendientes para el alumno (solo lo propio) y el tutor (transversal), con grupo y empresa del período, no los vigentes.
4. Sustituir las consultas de pendientes/atrasados que dependen del número de semana 1–18 y del período abierto por las basadas en obligaciones; retirar `q009`, `q013` y `q014` sin uso y dejar de tratar el grado como período en estas vistas.
5. Contratos, cliente, fixtures, migración aditiva sobre C03, documentación, pruebas y preview de los recorridos afectados.

Excluye: carga de PDF, nota, versiones y reenvíos (C05); revisión, correcciones y firma (C06); cierre de recepción, etiquetas de obligación cortada por cierre, finalización y promedio (C07); expediente y visor (C08). No se corrige el grado-como-período de reportes/expedientes/exportaciones fuera de las vistas de pendientes.

## Decisiones

Confirmadas: semanas lunes–domingo; primera semana parcial desde la incorporación; el período de un reporte se determina por su fecha de fin y no por la fecha de subida ni por el período marcado como actual; se entrega durante la semana y desde el lunes siguiente lo no entregado se muestra atrasado; recibir una semana no depende de aprobar otras; sin techo universal de 18 semanas; fechas de actividad como fechas civiles; el cierre manual del coordinador existe pero su efecto sobre obligaciones es de C07.

Resueltas por el responsable del proyecto el 2026-10-15 (registradas en [DECISIONES_PENDIENTES](../../docs/analysis/DECISIONES_PENDIENTES.md)):

1. DP-01: el período de una obligación es el que contiene el domingo de la semana (`semana_fin`). Las fechas escritas en el PDF se guardan aparte en C05 y nunca reasignan la semana ni el período. Con 30/04/2027–02/05/2027 resulta Mayo–Agosto.
2. DP-03 (para C04): la baja es inclusiva; la última semana es parcial hasta la fecha de baja y no se generan semanas posteriores. Lo no entregado antes de la baja sigue siendo atraso mientras la recepción esté abierta. La etiqueta por cierre anticipado queda para C07.
3. DP-04 (para C04): períodos creados y abiertos manualmente por el coordinador con fechas explícitas, zona operativa America/Mexico_City y fechas de períodos distintos sin solapamiento. La recepción simultánea de dos períodos se decide en C07.
4. Ordinal visible: continuo desde el inicio de la incorporación; el período se muestra aparte y el ordinal no es identidad.

Propuestas técnicas incluidas para la futura aprobación de implementación:

- Tabla `obligaciones_semanales`: `id`, `incorporacion_id` (FK `alumnos_dual.id`), `semana_inicio` (lunes), `semana_fin` (domingo), `inicio_efectivo`, `fin_efectivo`, `parcial`, `periodo_id` (FK `ciclos_dual.id`, nullable si ninguna fecha de período contiene la fecha de atribución), `UNIQUE (incorporacion_id, semana_inicio)`. Nunca se borran filas; una baja ajusta `fin_efectivo` y no genera semanas posteriores.
- Generación idempotente por `INSERT … ON CONFLICT DO NOTHING` bajo `pg_advisory_xact_lock` por incorporación, invocada al crear la incorporación, al registrar la baja y al consultar pendientes (hasta la semana que contiene la fecha actual en la zona operativa). No se pre-generan semanas futuras: así no existe una semana "habilitable" anticipadamente.
- La fecha de hoy y el corte "a partir del lunes" se evalúan en la zona operativa, no en UTC ni en la zona del navegador.
- Estado derivado, no almacenado: PENDIENTE si hoy ≤ `semana_fin` y no hay entrega; ATRASADA si hoy > `semana_fin` y no hay entrega; RECIBIDA si existe un reporte asociado. Hasta C05, la asociación es provisional: un reporte de `reportes_dual` cuya fecha de fin declarada cae dentro de la semana; C05 la reemplaza por una FK a la obligación.
- El ordinal visible es información de presentación; la identidad son las fechas y el ID. Se calcula continuo desde el inicio de la incorporación (decisión 4), con el período mostrado aparte.
- El no solapamiento de fechas entre períodos se valida en la API y con una restricción de exclusión en la base (`EXCLUDE USING gist` sobre el rango de fechas, que requiere la extensión `btree_gist` o un rango `daterange`); períodos ya existentes con fechas solapadas hacen fallar la migración con diagnóstico, sin modificarlos.
- Un período sin fechas completas no resuelve obligaciones; se informa como "sin período" y no se adivina.
- Mantener 404 para objetos ajenos o inexistentes, 403 para rol sin permiso y autorización en servidor; el alumno solo consulta sus obligaciones.

Pendientes bloqueantes (DP): ninguna para C04. Quedan fuera de esta spec y no bloquean: etiqueta de obligación cortada por cierre anticipado (DP-03, C07) y recepción simultánea de dos períodos (DP-04, C07). Si durante la implementación aparece una decisión nueva que cambie calendario, atraso o conservación, se detiene solo esa conducta y se presenta la decisión concreta.

## Contratos y cambios

Métodos/rutas/DTO y compatibilidad: reutilizar `/dual/tutor/alumnos-sin-reporte` y `/dual/tutor/alumnos-atrasados` cambiando su origen a obligaciones sin alterar la forma que consume el frontend; añadir una consulta de obligaciones por alumno y período para el tutor y una de pendientes propias para el alumno. Documentar DTO/OpenAPI y actualizar cliente, contrato estático y fixtures en el mismo incremento.

Datos, restricciones y conservación: migración aditiva e idempotente sobre C03 (`004_obligaciones.sql`), con restricciones `inicio ≤ fin` y `semana_inicio` lunes, FK por identificador y sin cascadas que borren expediente. No se borran obligaciones por baja ni por desactivar la cuenta. Base nueva de pruebas; no hay datos productivos que migrar.

Permisos y estados: tutor consulta todas las obligaciones; coordinador gestiona períodos; alumno solo las propias. Estados derivados definidos arriba; sin transiciones de recepción ni evaluación (C07).

Archivos/módulos previstos (lista fijada al pasar a READY; puede ajustarse al implementar si el diff lo exige, sin ampliar el alcance):

- Base de datos: `database/migrations/004_obligaciones.sql`, `docker/init-db.sh` (aplicar 004 tras 003), `database/README.md`.
- Backend, dominio y casos de uso: `app/domain/calendar.py` (semanas lunes–domingo, parcialidad, período por domingo, zona America/Mexico_City con `zoneinfo`; `tzdata` ya está en `requirements.txt`), `app/application/use_cases/dual/obligaciones.py` y ajustes en `coordinador_dual.py` (incorporación/baja generan o recortan obligaciones; `alumnos_atrasados`, `alumnos_sin_reporte`, apertura de período) y `alumno_dual.py`.
- Backend, datos y API: `app/infrastructure/database/queries/dual_obligaciones.py` y `dual_coordinador_dual.py` (sustituir q015/q017; retirar q009, q013 y q014), routers `coordinador_dual.py` y `alumno_dual.py`, `app/application/dto/reportes.py`, `tests/route_contract.json`, `tests/test_route_contract.py` y `tests/test_query_catalog.py`.
- Pruebas y verificación: `tests/test_c04_calendar.py` y `scripts/smoke_c04.py` (reloj y zona controlables).
- Frontend: `dualRepository.js`, `CoordinadorDual.svelte` (pendientes y atrasados del tutor), la pantalla de pendientes del alumno y, por M1, `PeriodosDual.svelte` con su ruta en `App.svelte`, el enlace en `Navbar.svelte` y el ícono en `Icon.svelte` (apertura y cierre de períodos del coordinador, que salen de la página del tutor), más `tests/structure.test.js` e `integration-tests/api-contract.test.mjs`.
- Documentación: `CONTRATO_API.md`, `MODELO_DE_DATOS.md`, `REGLAS_DE_NEGOCIO.md` si cambia su redacción, `PLAN_MAESTRO.md`, `specs/README.md` y esta spec.

Comportamiento ante fallos/reintentos: la generación puede repetirse sin duplicar; dos consultas concurrentes no crean dos obligaciones para el mismo intervalo; una baja concurrente con la generación no deja semanas posteriores a la baja.

## Verificación

| AC | Prueba o recorrido | Nivel y datos | Resultado |
|---|---|---|---|
| C04-AC1 / AC-06 | Incorporación un miércoles: primera obligación parcial de miércoles a domingo; dos alumnos con inicios distintos tienen obligaciones correctas | HTTP + PostgreSQL reales; fixtures sintéticos | REAL: PASS (semana parcial de miércoles a domingo; dos alumnos con obligaciones propias); visible en la interfaz del tutor y del alumno |
| C04-AC2 / AC-07 | Semana que empieza en abril y termina en mayo pertenece a Mayo–Agosto; subir o consultar en junio no cambia el período | HTTP + PostgreSQL reales; períodos sintéticos | REAL: PASS con fechas reales (período por domingo) y con reloj inyectado en casos de uso sobre la BD real (30 de abril; consultar en junio no cambia el período) |
| C04-AC3 / AC-08 | Viernes de la semana vigente permite entregar; el lunes siguiente sin entrega aparece atrasada para alumno y tutor, en zona America/Mexico_City | HTTP + PostgreSQL reales con reloj controlado en el límite de zona | REAL (reloj inyectado): domingo PENDIENTE y lunes ATRASADA sobre la BD real; SIMULADA: corte con instantes UTC/México. NO_VERIFICADO: aceptación de la entrega (C05) |
| C04-AC4 / RN-06 | Baja a mitad de semana: última semana parcial; no se generan posteriores; la historia se conserva | HTTP + PostgreSQL reales | REAL: PASS (también baja retroactiva: las semanas posteriores se excluyen sin borrarse) |
| C04-AC5 / RN-10 | Una semana pendiente de revisión no bloquea otra; una semana futura no se habilita por cerrar la anterior | HTTP + PostgreSQL reales | REAL: PASS (una semana recibida no bloquea las demás; nunca hay semanas futuras). La revisión del tutor como tal es de C06 |
| C04-AC6 / RN-04 | Alumno solo ve lo propio; IDs ajenos 404; tutor transversal | Negativos HTTP reales | REAL: PASS (propio; ajeno 403; inexistente 404; sin token 401) |
| C04-AC7 | Pantallas de pendientes del alumno y del tutor explican estado y fechas; funcionan en escritorio y móvil con teclado | Preview visual del build desplegado | REAL parcial: alumno y ficha del tutor en móvil 375 px sin desbordamiento (claro y oscuro en el alumno). Bandeja de pendientes del tutor y pantalla de períodos del coordinador (apertura y cierre) verificadas después de la revisión. NO_VERIFICADOS: foco con Tab, tema oscuro de la pantalla de períodos, móvil físico |

## Evidencia de implementación

La implementación y su evidencia están registradas en [evidencia.md](evidencia.md): smoke C04 con HTTP y PostgreSQL reales, 73 pruebas de backend, 21 pruebas JS y 59/59 rutas de contrato, y preview visual parcial. Las integraciones excluidas siguen NO_VERIFICADAS.

## Revisión

Veredicto: tercera revisión del 2026-10-15 (con M1 y M2 corregidos): APPROVED, sin defectos materiales nuevos. Historial: primera revisión CHANGES_REQUESTED por M1; segunda CHANGES_REQUESTED por M2; ambos corregidos y verificados. Revisión técnica y visual del mismo agente (no independiente). Pendiente la aprobación humana de cierre. Observaciones no bloqueantes para C07 o un seguimiento: (1) `cerrar_cuatrimestre` cierra el período abierto aunque la etiqueta enviada sea otra y le reescribe `periodo_label` (`dual.coordinador_dual.q023`), de modo que elegir mal el período en el formulario de cierre cierra el período abierto con el nombre equivocado; es conducta heredada de C01/C02, fuera del alcance de C04 (cierre es de C07), pero la pantalla `/dual/periodos` la hace más accesible; (2) la fecha de inicio de una incorporación no tiene límite inferior.
- M2 (CORREGIDO 2026-10-15): la regla heredada `fecha_inicio >= hoy` se sustituyó por un validador de modelo en `CuatrimestreAbrir`: se acepta un período en curso (inicio anterior a hoy) o futuro y se rechaza uno ya terminado (`fecha_fin` anterior a hoy en America/Mexico_City) con 422 y el mensaje "El período terminó el … solo se pueden abrir períodos en curso o futuros"; orden de fechas y duración mínima siguen igual. El cliente HTTP quita el prefijo técnico "Value error," de los mensajes 422. Pruebas: 4 de reglas de apertura (en curso, futuro y último día, terminado, reglas previas), 1 de JS para el prefijo y el smoke C04 abre el período en curso y rechaza uno terminado contra la BD real. Verificado en la interfaz: abrir y cerrar Septiembre–Diciembre 2026 el 15 de octubre y rechazo claro de Mayo–Agosto 2026. Revisión focal del cambio: sin hallazgos nuevos; observación no bloqueante: la API no exige que las fechas coincidan con la etiqueta ni fija una duración máxima (la pantalla siempre envía fechas canónicas), regla heredada que no se amplió. Descripción original del hallazgo: no se podía abrir el período en curso. `CuatrimestreAbrir.fecha_inicio_no_pasada` (`app/application/dto/reportes.py`) rechaza fechas de inicio anteriores a hoy, y la pantalla `/dual/periodos` calcula las fechas canónicas del período, sin permitir elegirlas. Escenario verificado en la interfaz el 2026-10-15: el coordinador elige Septiembre–Diciembre 2026 y recibe "Value error, La fecha de inicio (2026-09-01) no puede ser anterior a hoy (2026-10-15)". Impacto: con el piloto a mitad de cuatrimestre el período actual no puede existir en la aplicación; sus obligaciones quedan "Sin período", el período no puede abrirse ni cerrarse y el atribuir por domingo (DP-01) no se cumple. El mensaje además muestra el prefijo técnico "Value error,". La spec pedía fechas explícitas con validación (no antepasadas por la regla heredada de C01).
Revisor y modalidad: el mismo agente que implementó (Claude), contra la spec, los requisitos enlazados y el diff; revisión técnica y visual (alumno y tutor en móvil, incluida la bandeja de pendientes). NO es una revisión independiente.
Hallazgos materiales:
- M1 (CORREGIDO 2026-10-15): `POST /dual/tutor/abrir-cuatrimestre` y `GET /dual/tutor/cuatrimestre-actual` pasaron a `get_coordinator`; tutor y alumno reciben 403. Como la apertura y el cierre vivían en la página del tutor (a la que el coordinador sin rol de tutor no entra), se creó la pantalla `/dual/periodos` (solo coordinador, con enlace "Períodos" en su menú; estado actual, apertura y cierre) y se retiraron de la página del tutor la tarjeta, las ventanas y el código de períodos, de modo que el tutor ya no ve el estado del período. Se actualizaron MP-18, `rutas.md`, `CONTRATO_API.md`, DP-04, `test_api_permissions.py` (prueba nueva) y `smoke_c04.py` (tutor y alumno 403, coordinador 200/409/200). Descripción original del hallazgo: la apertura de períodos seguía reservada al tutor, contra la decisión DP-04 (apertura manual por el coordinador) y la spec ("coordinador gestiona períodos"). `POST /dual/tutor/abrir-cuatrimestre` y `GET /dual/tutor/cuatrimestre-actual` usan `get_coordinador_dual` (solo tutor) en `coordinador_dual.py`; el coordinador recibe 403, mientras que el cierre sí es solo del coordinador. La matriz MP-18, el mapa de rutas de C02 (`rutas.md`) y `test_api_permissions.py` no se actualizaron, y no hay prueba de permiso para esta ruta; el smoke abre el período con el token del tutor. Impacto: el responsable no puede abrir los períodos que luego cierra y los tutores conservan una capacidad que DP-04 asigna al coordinador.
Correcciones y verificación focal (2026-10-15): M1 aplicado. Backend 74/74 (prueba de permisos nueva, SIMULADA); smoke C04 REAL con permisos de períodos por rol; smokes C02 y C03 REAL sin regresión; JS 21/21 y contrato 59/59 (rutas sin cambios); build web saludable. Verificación visual en el navegador integrado: el tutor ya no ve la tarjeta de períodos y es redirigido al abrir `/dual/periodos`; el coordinador ve "Períodos" en su menú y, en la pantalla nueva, abre el período 2030 (estado "Abierto" con fechas), recibe el mensaje de la API al intentar abrir un segundo período abierto y lo cierra ("Cerrado"), sin desbordamiento en móvil 375 px. NO_VERIFICADOS: foco con Tab en la pantalla nueva y tema oscuro de esa pantalla.
Verificado en esta revisión sin repetir pruebas válidas: instalación nueva (esquema base + 003 + 004) en PostgreSQL 16 vacío con segunda ejecución idempotente; q015/q017 ya no existen; bandeja "No entregado" del tutor en la interfaz (semana, parcial, fechas, grupo, empresa, Overdue/Pending; sin desbordamiento).
Observación no bloqueante: la fecha de inicio de una incorporación no tiene límite inferior; un año mal escrito (p. ej. 2006 por 2026) genera cientos de obligaciones atrasadas que no se borran. Requiere decidir un rango o una corrección de inicio (decisión de producto).
Limitaciones: el reloj del servidor no se puede mover, así que el límite del lunes se verificó con reloj inyectado en casos de uso sobre la BD real y con pruebas de dominio; la asociación "recibida" es provisional hasta C05 y la entrega real sigue usando el flujo heredado hasta C05; dos incorporaciones consecutivas que comparten semana generan dos obligaciones con fechas efectivas disjuntas; reportes, expedientes y el filtro por período del directorio siguen tratando el grado como período (C05–C10).

## Aprobaciones y cierre

Aprobación de READY: el responsable del proyecto confirmó el 2026-10-15 las cuatro decisiones (DP-01, DP-03, DP-04 y ordinal continuo) y pidió pasar C04 a READY sin implementarla.
Aprobación de implementación: recibida mediante `IMPLEMENT C04` en este chat el 2026-10-15. Autoriza el alcance de esta spec, contratos, fixtures y documentación afectados; no autoriza C05, commit ni push.
Aprobación de cierre: pendiente.
Resumen final: pendiente.
Siguiente spec: C05 solo después de implementar, revisar y cerrar C04.
Commit/push: no autorizados.
