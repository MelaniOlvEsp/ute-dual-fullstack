# C05 — Entregas y versiones

Estado: DONE
Fecha: 2026-10-15 (cierre: 2026-10-15)
Responsable de aprobación: responsable del proyecto
Dependencias: C04 DONE (2026-10-15). DP-08, DP-12 y DP-13 resueltas por el responsable el 2026-10-15; DP-06 no bloquea. Sin decisiones bloqueantes: DRAFT → READY → IN_PROGRESS el 2026-10-15.

## Problema y resultado esperado

Hoy el alumno entrega con un selector secuencial: la API exige un período abierto, un número de semana 1–18 y, tras un rechazo, borra el reporte anterior y su archivo para guardar el nuevo, de modo que se pierde la historia. La nota se acepta como decimal, el PDF solo se verifica por extensión y los primeros bytes, el cliente limita a 2 MB y la API a 10 MB, el servidor recomprime las imágenes del PDF (altera la evidencia) y la entrega no está ligada a la obligación semanal de C04: "recibida" es solo una coincidencia provisional por fecha.

Resultado esperado: el alumno entrega cualquier semana vigente o atrasada de su propia lista de obligaciones, sin depender de aprobaciones anteriores ni de otras semanas; cada entrega crea una versión inmutable (PDF original, fechas y nota enteras declaradas) ligada a su obligación; un reenvío tras rechazo agrega una versión nueva y conserva las anteriores; dos envíos simultáneos para la misma obligación no duplican el reporte; el PDF se valida de verdad y se guarda privado y sin alterarlo.

## Fuentes y alcance

- US: [US-06 y US-09](../../docs/analysis/ESPECIFICACION_FUNCIONAL.md).
- RN: [RN-09, RN-10, RN-12, RN-13, RN-14 y RN-17](../../docs/analysis/REGLAS_DE_NEGOCIO.md); RN-23 solo en la condición de recepción abierta.
- AC: [AC-09, AC-10 y AC-11](../../docs/analysis/CRITERIOS_DE_ACEPTACION.md).
- Documentos enlazados: [plan maestro](../../docs/construction/PLAN_MAESTRO.md), [modelo de datos](../../docs/analysis/MODELO_DE_DATOS.md), [archivos e importaciones](../../docs/analysis/CONTRATO_DE_ARCHIVOS_E_IMPORTACIONES.md), [contrato API](../../docs/analysis/CONTRATO_API.md), [UX](../../docs/analysis/UX_Y_FLUJOS.md), [roles](../../docs/analysis/MATRIZ_DE_ROLES_Y_PERMISOS.md), [DP-06, DP-08, DP-12 y DP-13](../../docs/analysis/DECISIONES_PENDIENTES.md), [C04](../C04-calendario-y-pendientes/spec.md).

Incluye:

1. Entrega y reenvío por obligación (`obligacion_id` de C04): `POST` multipart con inicio y fin declarados, nota entera 1–10 y PDF. Reemplaza el flujo secuencial (`semana-actual`, semana 1–18 y borrado del rechazado).
2. Reporte lógico único por obligación con versiones numeradas e inmutables; la versión vigente es la última recibida. Un reenvío solo se acepta cuando el reporte está rechazado; un reporte aprobado no se reemplaza (RN-17).
3. Validación real de la nota (entero 1–10; rechaza 0, 11 y 8.5) y de las fechas (solo inicio ≤ fin, DP-12; la correspondencia con la semana la verifica el tutor en C06), con los mismos límites en cliente y API.
4. Validación real del PDF: extensión, tipo, firma `%PDF`, tamaño durante la lectura (límite único, DP-08), apertura con el motor PDF, al menos una página, rechazo claro de corruptos, vacíos o protegidos que no se puedan revisar. El original se conserva sin recompresión.
5. Almacenamiento privado con clave generada por el servidor, hash y tamaño; sin URL pública ni ruta del cliente. Escritura y base de datos con preparación y confirmación: un fallo nunca borra un original válido anterior y los huérfanos se limpian por referencia.
6. Lista de entregas del alumno por obligación con estado (sin entrega, pendiente de revisión, rechazado con observación, aprobado), versión vigente y su historial; descarga de sus propias versiones.
7. Estado "recibida" de C04 basado en la entrega real (sustituye la coincidencia provisional por fecha) y la bandeja del tutor sigue funcionando con la versión vigente.
8. Contratos, cliente, fixtures, migración aditiva sobre C04, documentación, pruebas y preview de los recorridos afectados.

Excluye: revisión, corrección de fechas y nota por el tutor, aprobación con firma y rechazo (C06; el rechazo heredado se usa solo para probar el reenvío); cierre de recepción, finalización y promedio (C07); expediente y visor integral (C08); plantillas (C09); tratamiento especial de períodos vacacionales (DP-06); integración real con Drive (adaptador opcional NO_VERIFICADO).

## Decisiones

Confirmadas: se puede entregar durante la semana (por ejemplo el viernes) y desde el lunes siguiente lo no entregado aparece atrasado (C04); recibir una semana no depende de aprobar otras; nota entera 1–10; el alumno adjunta el PDF firmado por la empresa y el sistema no valida esa firma; el reenvío conserva archivo, datos y decisiones anteriores y no crea dos reportes lógicos por obligación; después de aprobar el alumno no reemplaza el archivo; no hay reapertura ni rectificación posterior en V1; las fechas declaradas nunca reasignan la semana ni el período (DP-01); tutor y coordinador conservan acceso solo según la matriz; alumno solo accede a lo propio.

Propuestas técnicas incluidas para la futura aprobación de implementación:

- Modelo aditivo: `reportes_dual` pasa a ser el reporte lógico con `obligacion_id` único (nulo solo en filas heredadas) y puntero a la versión vigente; nueva tabla `reporte_versiones` (reporte, número único por reporte, inicio y fin declarados, nota entera con CHECK 1–10, documento, instante de recepción, autor) y `documentos` (clave privada, hash SHA-256, tamaño, tipo, estado). Las columnas heredadas de archivo y nota se derivan de la versión vigente mientras C06 migra la revisión.
- Una obligación, un reporte: `INSERT … ON CONFLICT` sobre `obligacion_id` y número de versión bajo `pg_advisory_xact_lock` por obligación; la segunda solicitud simultánea recibe 409 o el resultado de la primera, nunca una fila duplicada.
- Escritura en dos fases: el archivo se guarda con clave temporal, la transacción crea documento, versión y puntero, y solo entonces se confirma el archivo; si la transacción falla se elimina el archivo nuevo, nunca uno anterior.
- Límite único de PDF (propuesto 10 MB, DP-08) aplicado en cliente y API, y leído en bloques con corte al exceder.
- Sin recompresión del PDF; el nombre del archivo descargado se genera (`<matricula>-S<ordinal>-v<n>.pdf`), nunca se toma del cliente.
- Mantener 404 para objetos ajenos o inexistentes, 403 para rol sin permiso y autorización en servidor; el alumno no entrega por otro alumno ni sobre obligaciones ajenas.
- Un reporte rechazado solo se reenvía mientras se cumpla la condición de recepción abierta (DP-13).

Resueltas por el responsable del proyecto el 2026-10-15 (registradas en [DECISIONES_PENDIENTES](../../docs/analysis/DECISIONES_PENDIENTES.md)):

1. DP-08 — tamaños y almacenamiento: PDF de 10 MB en cliente y API (antes 2 MB y 10 MB), firma de tutor de 1 MB (ya vigente), almacenamiento privado local para el piloto y Drive solo como adaptador opcional que queda NO_VERIFICADO.
2. DP-12 — fechas declaradas: solo se exige inicio ≤ fin (se eligió la alternativa a la propuesta de solape); la correspondencia con la semana la verifica el tutor en C06. Las fechas del alumno nunca reasignan semana ni período (DP-01).
3. DP-13 — recepción abierta: una obligación acepta entrega y reenvío solo si su período está abierto y no cerrado; sin período no se entrega. La recepción simultánea de dos períodos sigue en DP-04 para C07.

Pendientes bloqueantes (DP): ninguno. No bloquean: DP-06 (sin tratamiento especial de períodos vacacionales; el alumno captura la nota que recibió de la empresa) y DP-09 a DP-11. Si durante la implementación aparece una decisión nueva que cambie calendario, permisos, notas o conservación, se detiene solo esa conducta y se presenta la decisión concreta.

## Contratos y cambios

Métodos/rutas/DTO y compatibilidad: nueva ruta de entrega por obligación para el alumno y consulta de entregas propias con versiones; descarga de la versión vigente o de una versión propia; la lista de reportes del tutor y la descarga de PDF usan la versión vigente. La ruta heredada `POST /dual/alumno/` y `GET /dual/alumno/semana-actual` se retiran o se redirigen a la nueva semántica en el mismo cambio, con cliente, contrato estático (`route_contract.json`), OpenAPI y fixtures actualizados juntos.

Datos, restricciones y conservación: migración `005_entregas.sql`, aditiva e idempotente sobre C04, con unicidad por obligación, número de versión único por reporte, nota entera con CHECK 1–10, FK por identificador y sin cascadas que borren expediente. Ninguna versión se actualiza ni se borra. Base nueva de pruebas; no hay datos productivos que migrar. Retirar la compresión destructiva y el borrado del rechazado en el reenvío.

Permisos y estados: alumno entrega y reenvía solo lo propio; tutor y coordinador consultan según la matriz (MP-07); sin cambio en la revisión (C06). Estados: sin entrega, pendiente de revisión, rechazado, aprobado; "atrasada" sigue siendo un indicador de C04 y no un estado de archivo.

Archivos/módulos previstos (se fijan al pasar a READY tras inspeccionar el diff base): `database/migrations/005_entregas.sql` e `init-db.sh`; dominio y casos de uso de entrega (`app/domain/reports.py`, `app/application/use_cases/dual/entregas.py`) y retiro de `subir_reporte` y `obtener_semana_actual`; validación y almacenamiento (`app/infrastructure/documents/dual_reports.py` y un adaptador de almacenamiento privado); consultas, routers de alumno y tutor, DTO y pruebas (`test_c05_entregas.py`, contrato de rutas); frontend (`report.js`, repositorio, `ReportesDual.svelte` por obligación con entrega, reenvío e historial) y documentación.

Comportamiento ante fallos/reintentos: entrega y reenvío son transaccionales; un reintento idéntico no duplica versión; dos solicitudes concurrentes no crean dos reportes ni dos versiones con el mismo número; un fallo de almacenamiento o de base de datos no deja un reporte sin archivo ni un archivo sin referencia, y nunca elimina un original válido.

## Verificación

| AC | Prueba o recorrido | Nivel y datos | Resultado |
|---|---|---|---|
| C05-AC1 / AC-09 | Semana anterior pendiente de revisión: el alumno entrega otra semana válida sin bloqueo; una semana futura no existe como obligación | HTTP + PostgreSQL reales; obligaciones sintéticas | REAL: PASS (se entrega la semana vigente con otra pendiente de revisión y una tercera sigue entregable) |
| C05-AC2 / AC-10 | Nota 1 y 10 aceptadas; 0, 11 y 8.5 rechazadas; fechas con inicio ≤ fin (DP-12); PDF corrupto, vacío, protegido, no PDF con extensión `.pdf` y mayor al límite rechazados; mismos límites en cliente y API | HTTP real; PDF sintéticos | REAL: PASS (notas 1 y 10 aceptadas; 0, 11, 8.5, 8,5, texto, negativo y vacío 422; inicio > fin 422; PNG, vacío, texto, cabecera falsa, truncado y protegido 422; 10 MB + 1 → 413; sin documentos, reportes ni archivos nuevos tras cada rechazo). Límite del cliente igual al de la API: JS SIMULADA |
| C05-AC3 / AC-11 | Rechazado con nota: el reenvío conserva la versión anterior y crea una nueva vigente; dos envíos simultáneos no duplican reporte ni versión | HTTP + PostgreSQL reales con concurrencia | REAL: PASS (rechazo con observación, reenvío como versión 2 con la decisión conservada en la versión 1, un solo reporte lógico; seis envíos simultáneos distintos → un 201 y cinco 409 sin duplicados ni archivos extra; reintento idéntico estable). La revisión del rechazo se hizo con la ruta heredada del tutor |
| C05-AC4 / RN-17 | Un reporte aprobado no se reemplaza; el original se conserva byte a byte (hash) y no se recomprime | HTTP + PostgreSQL + almacenamiento real | REAL: PASS (el archivo almacenado, la descarga del alumno y la del tutor coinciden byte a byte con lo enviado y con el SHA-256 registrado; el aprobado devuelve 409 y se conserva; la base rechaza actualizar o borrar versiones) |
| C05-AC5 / RN-13, DP-13 | Obligación con período cerrado o sin período no acepta entrega ni reenvío | HTTP + PostgreSQL reales | REAL: PASS (sin período 409; tras cerrar el período, entrega y reenvío de un rechazado 409 y `puede_entregar` falso con motivo) |
| C05-AC6 / RN-04 | Alumno solo ve y descarga lo propio; IDs ajenos 404; rol incorrecto 403; sin URL pública | Negativos HTTP reales | REAL: PASS (obligación y versiones ajenas 404; tutor y coordinador 403; sin token 401; UUID inválido 422; rutas heredadas retiradas; descarga con nombre generado y sin URL pública) |
| C05-AC7 | Fallo simulado de almacenamiento o de base de datos no deja huérfanos ni borra un original válido | Pruebas con fallos inyectados + verificación real | REAL: PASS (fallo inyectado al confirmar la transacción contra la BD real: sin documento, reporte ni archivo nuevos y el original anterior intacto; limpieza de huérfanos por referencia sin tocar los referenciados). Casos de uso con dobles: SIMULADA |
| C05-AC8 | Pantalla del alumno: entrega, reenvío, observación e historial funcionan en escritorio y móvil con teclado; el estado "recibida" de C04 refleja la entrega real | Preview visual del build desplegado | REAL: PASS en móvil 375 px y escritorio 1280 px, tema oscuro y teclado (entrega, errores del cliente y de la API, reenvío con observación, historial de versiones; se corrigió un desbordamiento horizontal del historial). NO_VERIFICADOS: descarga del PDF en el navegador (la petición responde 200 pero el guardado no se pudo observar), móvil físico |

## Evidencia de implementación

La implementación y su evidencia están registradas en [evidencia.md](evidencia.md): smoke C05 con HTTP, PostgreSQL y almacenamiento reales, 105 pruebas de backend, 25 pruebas JS, 60/60 rutas de contrato, migración 005 verificada en base nueva e idempotente, regresión de los smokes C01–C04 y preview visual. Drive y la revisión del tutor (C06) siguen NO_VERIFICADOS.

Cambios adyacentes necesarios: la aprobación heredada del tutor ya no borra el original entregado (RN-14/RN-16; la revisión se rehace en C06); el volumen `dual-uploads` y el directorio con propietario no root en la imagen de la API; `smoke_c04.py` liga el reporte provisional a la obligación y cierra cualquier período abierto antes de probar el solapamiento.

## Revisión

Veredicto: APPROVED (2026-10-15, primera revisión), sin defectos materiales.
Revisor y modalidad: el mismo agente que implementó (Claude), contra la spec, los requisitos enlazados y el diff real; revisión técnica. La visual no se repitió: se apoyó en el preview de la implementación, con el build desplegado posterior a la última edición del frontend. NO es una revisión independiente.
Hallazgos materiales: ninguno.
Observaciones no bloqueantes: (1) `limpiar_huerfanos` (`dual_reports.py`) solo se invoca desde el smoke y las pruebas; ningún proceso del sistema la ejecuta, de modo que un archivo guardado cuyo proceso muere antes de confirmar la transacción queda sin referencia hasta una limpieza manual; (2) en `entregar`, el `except BaseException` borra el archivo nuevo también ante un COMMIT ambiguo (conexión cortada tras confirmar), caso estrecho que dejaría una versión sin archivo; comprobar la referencia en `documentos` antes de borrar lo evita; (3) el nombre de descarga es `<matricula>-v<n>.pdf`, no `<matricula>-S<ordinal>-v<n>.pdf` como proponía el texto.
Correcciones y verificación focal: no aplica.
Limitaciones: Drive y cualquier proveedor externo quedan NO_VERIFICADOS salvo que se usen; no hay validación de la firma de la empresa ni OCR; la revisión y la firma del tutor son de C06.

## Aprobaciones y cierre

Aprobación de READY: el responsable confirmó el 2026-10-15 (por respuesta a las tres preguntas) DP-08 con 10 MB y almacenamiento local privado, DP-12 con solo inicio ≤ fin y DP-13 con entrega solo con período abierto.
Aprobación de implementación: recibida mediante `IMPLEMENT C05` en este chat el 2026-10-15. Autoriza el alcance de esta spec, contratos, fixtures y documentación afectados; no autoriza C06, commit ni push.
Aprobación de cierre: otorgada por el responsable del proyecto el 2026-10-15 mediante `CLOSE C05 + NEXT SPEC`, sujeta a revisión aprobada y evidencia suficiente. Se verificó: revisión técnica APPROVED sin defectos materiales y evidencia REAL para C05-AC1 a AC7 y REAL parcial para AC8 (ver [evidencia.md](evidencia.md)).
Resumen final: entrega y reenvío por obligación (`POST /dual/alumno/obligaciones/{id}/entrega`); un reporte lógico por obligación con versiones numeradas e inmutables (trigger de la base) y decisión anterior conservada al reenviar; nota entera 1–10, fechas con inicio ≤ fin (DP-12) y recepción solo con período abierto (DP-13); PDF de 10 MB validado con el motor PDF (vacío, cabecera, dañado, protegido, sin páginas) y guardado privado sin recompresión, con clave del servidor, SHA-256 y escritura atómica; historial de versiones y descarga propia; "recibida" de C04 basada en la entrega real; pantalla del alumno por obligación con entrega, reenvío, observación del tutor e historial; migración `005_entregas.sql`, volumen `dual-uploads`, contratos, fixtures y documentación actualizados.
Pruebas: backend 105/105 (27 nuevas, SIMULADA); JS 25/25; contrato estático 60/60; smokes C01–C05 REAL con HTTP, PostgreSQL y almacenamiento reales (C05 con concurrencia, hash, inmutabilidad y fallo inyectado); migración verificada en base nueva e idempotente; preview visual en móvil 375 px, escritorio 1280 px, tema oscuro y teclado. Detalle en [evidencia.md](evidencia.md).
Limitaciones aceptadas al cierre: (1) Drive y cualquier proveedor externo NO_VERIFICADOS; (2) la revisión, corrección y firma del tutor son de C06: la aprobación heredada sigue exigiendo Drive y la revisión heredada no comprueba el estado ni bloquea contra un reenvío simultáneo; (3) la descarga del PDF en el navegador y el móvil físico NO_VERIFICADOS; (4) los reportes heredados sin `obligacion_id` ya no se ligan a obligaciones; (5) la limpieza de huérfanos no corre automáticamente y el COMMIT ambiguo puede borrar un archivo recién confirmado (observaciones de la revisión); (6) cierre de período, expediente y promedios siguen tratando el grado como período hasta C07–C08; (7) revisión del mismo agente, no independiente.
Siguiente spec: [C06 — Revisión y firma](../C06-revision-y-firma/spec.md), en DRAFT; DP-02 y DP-07 bloquean pasar a READY.
Commit/push: no autorizados salvo indicación explícita; este cierre no hizo commit ni push.
