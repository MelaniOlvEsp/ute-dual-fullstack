# Contrato API: existente y objetivo

Estado: contrato vivo. C01–C09 describen rutas implementadas (C05 a C09 DONE); C10 no cambia el contrato (73 rutas; el respaldo y la restauración son órdenes del responsable, no rutas de la API). Fuentes ejecutables: routers en `ute-api-backend/app/presentation/api/routers`, `route_contract.json` y repositorios de `ute-dual-frontend/src/infrastructure/repositories`.

## Inventario actual

| Familia | Rutas principales existentes | Cambio requerido |
|---|---|---|
| Identidad | POST /auth/register, /login, /cambiar-password; GET /auth/me | Alinear esquema, sesiones y tres roles. |
| Tutores | POST/GET /auth/tutores; DELETE /auth/tutores/{usuario_id} | Baja lógica y revocación; confirmar contrato compatible. |
| Recuperación | POST /auth/alumnos/{matricula}/password-provisional | Conservar control tutor y cambio forzoso. |
| Alumno | GET /dual/alumno/expediente, /paquete, /obligaciones; POST /obligaciones/{id}/entrega; GET /reportes/{id}/versiones[/{n}/pdf] | Implementado en C04–C05 y C08: obligaciones independientes con versiones, expediente y paquete propios (retiradas `POST /dual/alumno/`, `GET /semana-actual` y `GET /mis-reportes`). |
| Revisión | GET /dual/tutor/reportes[/{reporte_id}]; POST /reportes/{id}/versiones/{n}/revision; GET /versiones/{n}/pdf | Implementado en C06: revisión por versión, correcciones trazables y firma (retirado el PATCH heredado). |
| Empresa | /dual/tutor/empresas, /asignaciones, /alumnos/{matricula} | Fecha real de inicio/baja y continuidad entre períodos. |
| Calendario | /dual/tutor/cuatrimestre-actual, /abrir-cuatrimestre, /periodos[/{id}/resumen, /cierre-recepcion, /finalizacion] | Implementado en C07: recepción y evaluación separadas del calendario, cierre y finalización del coordinador (retirado `/cierre`). |
| Firma | POST/GET /dual/tutor/firma | Versionar sin alterar firmados históricos. |
| Grupos/expediente | /dual/carrera/grupos, /alumnos, /periodos | Implementado en C08: directorio paginado con bajas, expediente por período con grupo histórico y consulta propia del alumno. |
| Descargas | /dual/*/reportes/{id}/versiones/{n}/pdf; /dual/carrera/paquetes/alumno/{m}, /paquetes/carrera/{c}; /dual/alumno/paquete | Implementado en C08: autorización de objeto, solo versiones aprobadas y paquete ZIP con manifiesto (retiradas las rutas `reporte/{id}/pdf` y `exportar-csv|zip`). |
| Foro | /foro/publicaciones y reacciones | Implementado en C09: foro como pantalla inicial y eliminación lógica de anuncios (autor o coordinador). |
| Buzón | /foro/buzon/, /mios, /{id}, respuestas, leído, cierre y reapertura | Implementado en C09: hilo cerrado de solo lectura, reapertura del personal e hilo nuevo enlazado. |

Los prefijos carrera/coordinador_dual heredados no representan roles nuevos. No renombrar todo sin beneficio: adaptar cliente y servidor en el mismo incremento.

## Contrato objetivo a concretar en cada spec

| Operación propuesta | Entrada esencial | Resultado/garantía | Spec |
|---|---|---|---|
| Consultar obligaciones | período opcional, identidad en sesión | ID, intervalo, estado, atraso (implementado en C04; permiso de entregar y motivo de bloqueo llegan con C05) | C04 |
| Entregar versión | obligación_id, fechas declaradas, nota entera, PDF multipart | reporte_id, version_id y pendiente de revisión; 201 solo tras persistencia (implementado en C05) | C05 |
| Revisar versión | version_id, acción, fechas/nota validadas, nota de rechazo, versión esperada | Revisión trazable, sin sobrescribir versión nueva por concurrencia (implementado en C06) | C06 |
| Cerrar recepción | periodo_id y confirmación del coordinador | Cierre idempotente con autor/instante, mantiene revisión (implementado en C07) | C07 |
| Finalizar evaluación | periodo_id | Falla si hay pendientes; congela resultados atómicamente (implementado en C07) | C07 |
| Consultar expediente | alumno autorizado, período opcional | Grupo histórico, aprobados, promedio, cantidad y carácter provisional/final | C08 |
| Descargar documento | ID autorizado, original/firmado según permisos | application/pdf y nombre seguro; nunca ruta del disco ni token Drive | C05/C08 |
| Publicar plantillas | Word/PDF y metadatos | Versión vigente completa, anterior conservada | C09 |

Estas son operaciones, no rutas definitivas. Antes de implementar cada spec debe fijar método, ruta, esquema, ejemplos y errores; actualizar OpenAPI/fixtures/repositorios y pruebas en el mismo cambio.

## Reglas de contrato

### Cambios implementados en C02 (DONE)

- `POST /auth/register`: solo email/password; campos adicionales (por ejemplo roles) devuelven 422. Matrícula no autorizada/correo discrepante: 403; cuenta duplicada, incluida alta concurrente: 409. Alta de tutor también controla conflicto con 409 y rechaza campos extra.
- Registro y cambio: 12–128 puntos de código, mayúscula/minúscula/dígito decimal Unicode (Lu/Ll/Nd), máximo 72 bytes UTF-8. Incumplimiento de política: 400. Login no acepta truncamiento bcrypt.
- Las claves provisionales de tutor y recuperación tienen 12 caracteres, cumplen la misma política y se muestran únicamente en la respuesta que las genera.
- `POST /auth/cambiar-password`: contraseña actual incorrecta es 400 (permite reintentar); sesión obsoleta/cuenta inactiva es 401. Éxito revoca todas las sesiones anteriores y exige nuevo login.
- `GET /dual/alumno/reporte/{id}/pdf` y detalle/respuesta de buzón ajeno: 404. El PDF se autoriza antes de invocar proveedor. `PATCH /foro/buzon/{id}/cerrar`: solo tutor/coordinador; alumno 403.
- `POST /dual/tutor/cierre`: solo coordinador (nombre de prefijo heredado). No acredita implementación del cierre objetivo de C07. Apertura de períodos conservaba entonces la conducta existente (tutor); DP-04 la asignó al coordinador y C04 lo implementó (ver C04 abajo).
- `DELETE /dual/carrera/alumnos/{matricula}`: solo tutor; ahora desactiva acceso y autorización de registro, revoca sesiones y conserva expediente/referencias. 200 con `mensaje`; inexistente 404. No es baja de incorporación Dual ni borrado físico. La UI consume esta semántica; no hay endpoint nuevo de reactivación.
- Métodos/rutas y parámetros del fixture `route_contract.json` permanecen compatibles. Cambian validaciones, guardas y semántica descritas arriba. [Mapa de permisos C02](../../specs/C02-identidad-y-accesos/rutas.md) y [evidencia](../../specs/C02-identidad-y-accesos/evidencia.md); smoke HTTP/PostgreSQL C02 PASS el 2026-10-15; preview aún pendiente.

### Cambios implementados en C03 (IN_PROGRESS)

- `GET /dual/carrera/carreras`: devuelve el catálogo activo cerrado a TII, LOG y MER.
- `POST /dual/carrera/grupos`: el tutor crea un grupo con carrera canónica; la base genera la nomenclatura institucional. Educación y valores fuera del catálogo devuelven 422. El coordinador puede consultar pero no crear grupos (403).
- `POST /dual/carrera/grupos/{grupo_id}/alumnos/preview`: multipart con `periodo_id` y CSV UTF-8 `matricula,nombre`; informa válidos, repetidos y conflictos sin escribir.
- `POST /dual/carrera/grupos/{grupo_id}/alumnos`: aplica el mismo lote de forma transaccional. Un conflicto devuelve 409 y revierte el lote; un reintento idéntico no duplica pertenencia.
- `POST /dual/carrera/grupos/{grupo_id}/alumnos/individual`: requiere `matricula`, `nombre` y `periodo_id`; autoriza el registro y crea una pertenencia por período.
- `GET /dual/carrera/alumnos/{matricula}/grupos`: devuelve el historial de período, grupo, grado, carrera y nomenclatura sin reescribir períodos anteriores.
- `POST /dual/carrera/grupos/promociones/preview` y `POST /dual/carrera/grupos/promociones`: origen y destino usan IDs explícitos de grupo/período; `matriculas` opcional limita la selección. Los conflictos cancelan el lote.
- `POST /dual/tutor/asignaciones` y `PATCH /dual/tutor/alumnos/{matricula}` requieren fecha real de inicio o baja según la operación. Solo existe una incorporación activa; cambiar empresa exige baja previa.
- `GET /dual/tutor/alumnos/{matricula}/incorporaciones`: conserva y devuelve las incorporaciones anteriores. La baja no desactiva usuario, autorización de registro, pertenencias ni expediente.
- El fixture contractual contiene 57 rutas. [Spec C03](../../specs/C03-grupos-e-incorporacion/spec.md) y [evidencia C03](../../specs/C03-grupos-e-incorporacion/evidencia.md).

### Cambios implementados en C04 (IN_PROGRESS)

- Obligaciones del alumno (ruta `GET /dual/alumno/obligaciones`, parámetro opcional `periodo`) y del tutor (ruta `GET /dual/tutor/alumnos/{matricula}/obligaciones`, mismo parámetro; matrícula inexistente 404; alumno 403): listan las semanas lunes–domingo de las incorporaciones del alumno, más recientes primero. Campos: `id`, `incorporacion_id`, `ordinal` (continuo desde el inicio de la incorporación, no es identidad), `semana_inicio`, `semana_fin`, `inicio_efectivo`, `fin_efectivo`, `parcial`, `periodo` y `periodo_label` (nulos si ningún período contiene el domingo), `empresa` y `estado`: `PENDIENTE` (hoy ≤ domingo, sin entrega), `ATRASADA` (desde el lunes siguiente, sin entrega) o `RECIBIDA`. El estado se deriva y no se almacena; "recibida" es provisional hasta C05 (existe un reporte cuya fecha de fin declarada cae en la semana). `periodo` filtra por etiqueta sin alterar el ordinal.
- Generación: idempotente y bajo bloqueo por incorporación, hasta la semana vigente en America/Mexico_City; nunca se generan semanas futuras. La primera semana es parcial desde la fecha real de inicio; la baja es inclusiva, recorta la última semana y excluye las posteriores (no se borran). El período de una semana es el que contiene su domingo (DP-01); al abrir un período se asigna a las semanas que aún no tenían período.
- `GET /dual/tutor/alumnos-atrasados`: ahora devuelve una fila por obligación sin entrega de incorporaciones activas. Conserva la forma anterior (`matricula`, `nombre`, `nomenclatura`, `empresa`, `semana_esperada` = ordinal, `ultima_semana`, `cuatrimestre`, `status` Overdue/Pending) y añade `periodo_label`, `semana_inicio`, `semana_fin`, `inicio_efectivo`, `fin_efectivo` y `parcial`. `nomenclatura` es la del grupo del período de la semana (con respaldo en el grupo vigente).
- `GET /dual/tutor/alumnos-sin-reporte` (`cuatrimestre`, `semana`): `semana` es ahora el ordinal de la obligación (1 o mayor, sin tope de 18) dentro del período indicado.
- `POST /dual/tutor/abrir-cuatrimestre` y `GET /dual/tutor/cuatrimestre-actual`: solo coordinador (DP-04; MP-18). Tutor y alumno reciben 403; antes eran del tutor. Se puede abrir el período en curso (inicio anterior a hoy) o uno futuro; un período ya terminado (fin anterior a hoy en America/Mexico_City) devuelve 422 con "solo se pueden abrir períodos en curso o futuros", y siguen vigentes el orden de fechas y la duración mínima de 110 días. La apertura rechaza con 409 fechas que se solapan con otro período (nombra el período en conflicto); la base lo garantiza con una restricción de exclusión. Las fechas se evalúan en America/Mexico_City. La interfaz de apertura y cierre está en `/dual/periodos` (coordinador); el tutor ya no ve el estado del período.
- `GET /dual/tutor/asignaciones` devuelve ahora `fecha_inicio` y `fecha_baja`; la incorporación ya no escribe `cuatrimestre`.
- El fixture contractual contiene 59 rutas. [Spec C04](../../specs/C04-calendario-y-pendientes/spec.md) y [evidencia C04](../../specs/C04-calendario-y-pendientes/evidencia.md).

### Cambios implementados en C05 (DONE)

- `POST /dual/alumno/obligaciones/{obligacion_id}/entrega` (multipart: `fecha_inicio`, `fecha_fin`, `calificacion_alumno`, `archivo`): entrega o reenvía una obligación propia como una versión nueva e inmutable. 201 con `mensaje`, `reporte_id`, `version` y `repetido`. Errores: 422 nota que no sea entero 1–10 (0, 11 y 8.5 incluidos), inicio posterior al fin (DP-12: solo esto se exige de las fechas; la correspondencia con la semana la verifica el tutor), extensión no PDF, archivo vacío, dañado, protegido o sin páginas; 413 si supera 10 MB; 409 si la recepción del período no está abierta o no hay período (DP-13), si el reporte ya fue aprobado (RN-17) o si hay una versión pendiente de revisión distinta; 404 si la obligación es ajena, inexistente o posterior a la baja; 403 para tutor y coordinador. Un reintento idéntico mientras la versión está pendiente devuelve 201 con `repetido: true` y no duplica nada. Dos envíos simultáneos para la misma obligación no crean dos reportes ni dos versiones.
- Reenvío: solo cuando el reporte está rechazado. La decisión anterior (rechazo y observación) se copia a la versión que la recibió y el reporte vuelve a "Pendiente" con la versión nueva vigente; las versiones anteriores se conservan y no se modifican ni se borran (la base lo impide con un disparador).
- `GET /dual/alumno/reportes/{reporte_id}/versiones`: historial propio (más reciente primero) con fechas y nota declaradas, instante de recepción, decisión y observación, tamaño, hash y páginas. `GET /dual/alumno/reportes/{reporte_id}/versiones/{numero}/pdf`: el original de esa versión (`application/pdf`, nombre generado). Ajenos o inexistentes 404.
- `GET /dual/alumno/obligaciones` agrega `reporte_id`, `entrega` (Pendiente, Rechazada, Aprobada o nulo), `version`, `observacion` (si está rechazada), `puede_entregar` y `motivo_bloqueo`. "Recibida" ahora significa que existe un reporte ligado a la obligación (ya no la coincidencia provisional por fecha).
- Retiradas: `POST /dual/alumno/` (entrega secuencial con semana 1–18 y borrado del rechazado) y `GET /dual/alumno/semana-actual`. `semana` de un reporte es el ordinal de la obligación (sin techo de 18). La aprobación heredada del tutor ya no borra el original.
- El fixture contractual contiene 60 rutas. [Spec C05](../../specs/C05-entregas-y-versiones/spec.md) y [evidencia C05](../../specs/C05-entregas-y-versiones/evidencia.md).

### Cambios implementados en C06 (DONE)

- `GET /dual/tutor/reportes/{reporte_id}`: detalle para el tutor (todas las carreras): ficha, semana (`semana_inicio`, `semana_fin`), `version_vigente`, `puede_revisar`, `firma_registrada` y `versiones` (más reciente primero) con fechas y nota declaradas, decisión, observación, valores validados (`validada_inicio`, `validada_fin`, `validada_nota`), `correcciones` (campo, previo, nuevo), `firmado` y `firma_modo` (`celda` u `hoja_adicional`). Inexistente 404; alumno y coordinador 403.
- `POST /dual/tutor/reportes/{reporte_id}/versiones/{numero}/revision` (JSON: `decision` Aprobada o Rechazada, `observacion`, `calificacion` entera, `fecha_inicio`, `fecha_fin`; todo salvo `decision` opcional): decide la versión indicada. 200 con `mensaje`, `estado`, `version`, `repetido` y `firma`. Errores: 422 rechazo sin observación, nota que no sea entero 1–10 (0, 11, 8.5, booleano y texto incluidos), inicio posterior al fin o decisión inválida; 409 si falta la firma registrada del tutor, si la versión ya fue revisada o ya existe una más reciente, o si el reporte ya fue decidido; 404 reporte o versión inexistente; 403 alumno y coordinador (MP-08); 401 sin sesión. Un reintento idéntico devuelve 200 con `repetido: true` sin duplicar. La revisión no depende de que la recepción del período esté abierta (RN-18/RN-19), y las correcciones nunca cambian la obligación, la semana ni el período (DP-02, DP-01).
- Aprobar guarda un documento firmado nuevo (rol `firmado`, clave del servidor, SHA-256) derivado del original, que se conserva intacto; la firma se estampa en la celda «Firma» de la fila «Tutor académico» (DP-07) y, si el formato no se reconoce o la celda está ocupada, en una hoja adicional. Si algo falla el reporte sigue pendiente y no queda archivo huérfano.
- `GET /dual/tutor/reportes/{reporte_id}/versiones/{numero}/pdf` y `GET /dual/alumno/reportes/{reporte_id}/versiones/{numero}/pdf`: parámetro `documento` (`original` por defecto o `firmado`; otro valor 422). El firmado de una versión no aprobada 404; el alumno solo accede a lo propio. Las rutas heredadas de lectura de PDF (`/dual/alumno/reporte/{id}/pdf`, `/dual/tutor/reporte/{id}/pdf`, carrera) devuelven el firmado cuando existe.
- `GET /dual/tutor/reportes` agrega `version` y `obligacion_id`; `GET /dual/alumno/reportes/{id}/versiones` agrega `firmado` y los valores validados.
- Retirada: `PATCH /dual/tutor/reportes/{reporte_id}` (revisión heredada que sobrescribía datos y subía el firmado a Drive).
- El fixture contractual contiene 62 rutas. [Spec C06](../../specs/C06-revision-y-firma/spec.md) y [evidencia C06](../../specs/C06-revision-y-firma/evidencia.md).

### Cambios implementados en C07 (DONE)

- `GET /dual/tutor/periodos` (tutor y coordinador): períodos con `id`, `periodo_label`, fechas calendario, `recepcion` (`sin_abrir`, `abierta`, `cerrada`), `evaluacion` (`en_curso`, `finalizada`), `cierre_efectivo` (fecha civil en America/Mexico_City, aparte de las fechas calendario), `cerrado_en` y `finalizada_en`. `GET /dual/tutor/periodos/{periodo_id}/resumen`: además `conteos` (semanas, recibidas, pendientes de revisión, aprobadas, rechazadas, sin entrega y no recibidas por cierre), `alumnos` con `aprobados`, `suma`, `promedio` (texto con dos decimales o nulo), `promedio_texto` («Sin calificación» si no hay aprobados) y `definitivo`, `puede_cerrar_recepcion`, `puede_finalizar` y `motivo_finalizar`. Provisional se calcula en vivo y final se lee del registro congelado. Período inexistente 404; alumno 403.
- `POST /dual/tutor/periodos/{periodo_id}/cierre-recepcion` y `POST /dual/tutor/periodos/{periodo_id}/finalizacion` (solo coordinador, MP-11; cuerpo `{"confirmar": true}`, otro valor 422; tutor y alumno 403; sin sesión 401). Cierre: 200 con `repetido`; 409 si el período nunca recibió; identifica el período por ID, no lo renombra y no cambia sus fechas; bloquea entregas y reenvíos (409) y el tutor sigue revisando (RN-18, RN-19). Finalización: 409 si la recepción no está cerrada o quedan reportes pendientes de revisión (RN-20); congela por alumno suma, cantidad de aprobados y promedio con dos decimales HALF_UP (RN-21, RN-22, DP-11) y es irreversible; 200 con `repetido` si ya estaba finalizada.
- La entrega y el reenvío toman el bloqueo compartido de la fila del período y el cierre el exclusivo: una entrega que compite con el cierre o gana y queda antes, o espera y recibe 409 (AC-15).
- `GET /dual/alumno/obligaciones` y las consultas del tutor: `estado` agrega `NO_RECIBIDA_POR_CIERRE` (semana sin entrega cuyo período se cerró antes de que terminara la semana, DP-03) y `cierre_efectivo`; una semana ya terminada antes del cierre sigue `ATRASADA`. La bandeja de atrasados del tutor devuelve `status` `NotReceived` para las cortadas.
- `POST /dual/tutor/abrir-cuatrimestre`: 409 si la etiqueta corresponde a un período ya cerrado (un período cerrado no se reabre).
- `GET /dual/carrera/alumnos`: `cuatrimestre` es la etiqueta del período y filtra a los alumnos con semanas en él; `reportes_aprobados` y `promedio` se calculan con los reportes de ese período, no con el grado. Un período sin alumnos devuelve lista vacía.
- Retirada: `POST /dual/tutor/cierre` (cierre por etiqueta que además renombraba el período).
- El fixture contractual contiene 65 rutas. [Spec C07](../../specs/C07-cierre-y-calificacion/spec.md) y [evidencia C07](../../specs/C07-cierre-y-calificacion/evidencia.md).

### Cambios implementados en C08 (DONE)

- Alumno (matrícula siempre de la sesión; ninguna ruta recibe una matrícula): `GET /dual/alumno/expediente` (períodos con semanas, `grupo` histórico del período, `aprobados` con semana, fechas, `nota` validada, `declarada_nota`, `corregida`, `firmado`, `version`, `resumen` con `aprobados`, `suma`, `promedio` y `definitivo`, y `paquete` con `disponible`, `hasta` y `motivo`) y `GET /dual/alumno/paquete?periodo_id=` (ZIP propio; 403 pasados 7 días desde la finalización; 409 si el período no está finalizado; 404 si no tuvo semanas en él). Descarga de versiones propias: `GET /dual/alumno/reportes/{id}/versiones/{n}/pdf` (C05/C06).
- Personal: `GET /dual/carrera/alumnos` ahora devuelve `{items, total, limite, desplazamiento}` (parámetros `cuatrimestre` = etiqueta de período, `grupo`, `q`, `situacion` = `todos|activos|baja`, `limite` 1–200, `desplazamiento` ≥ 0; orden estable por nombre y matrícula; incluye a los dados de baja con `activo` y `fecha_baja`; parámetros inválidos 422). `GET /dual/carrera/alumnos/{matricula}/expediente` (tutor y coordinador; alumno 403; matrícula inexistente 404). `GET /dual/carrera/reportes/{reporte_id}/versiones/{numero}/pdf?documento=original|firmado`: solo versiones aprobadas (otra cosa 404).
- Paquetes de archivo (solo tutor, DP-14): `GET /dual/carrera/paquetes/alumno/{matricula}?periodo_id=` y `GET /dual/carrera/paquetes/carrera/{codigo}?periodo_id=`. ZIP con `manifiesto.json` (SHA-256 y tamaño de cada archivo, orden estable), `resumen.csv` (UTF-8 con BOM, CRLF, celdas con `= + - @` protegidas con apóstrofo) y los PDF en `carrera/período/grupo/matrícula/S<n>-v<n>-firmado|original.pdf` con nombres generados por el servidor. 409 si el período no está finalizado o falta algún archivo (nunca se entrega un paquete incompleto); 404 si no hay alumnos o semanas; coordinador y alumno 403. Cada generación se registra en `paquetes_archivo` (inmutable; el registro acredita la generación, no la descarga).
- Retiradas: `GET /dual/alumno/mis-reportes`, `GET /dual/alumno/reporte/{id}/pdf`, `GET /dual/tutor/reporte/{id}/pdf`, `GET /dual/carrera/alumnos/{matricula}/reportes`, `GET /dual/carrera/reporte/{id}/pdf` y `GET /dual/carrera/alumnos/{matricula}/exportar-csv|exportar-zip`.
- El fixture contractual contiene 64 rutas. [Spec C08](../../specs/C08-expediente-y-visor/spec.md) y [evidencia C08](../../specs/C08-expediente-y-visor/evidencia.md).

### Cambios implementados en C08B (DONE)

- Depuración de los archivos PDF de un período finalizado (tutor y coordinador, D2; alumno 403, sin sesión 401): `GET /dual/carrera/periodos/{periodo_id}/archivo` (por carrera: alumnos, archivos y bytes vigentes, paquete vigente generado por el tutor después de la finalización, estado `sin_depurar|programada|parcial|depurado`, `puede_depurar` y `frase_esperada`; historial de purgas y `gracia_dias`) y `POST /dual/carrera/periodos/{periodo_id}/purgas` (`carrera` o `matricula`, `confirmar` estrictamente `true` y `frase` exacta; 200 con `repetido`; 409 sin período finalizado, sin paquete del mismo alcance, con un paquete que no coincide con los archivos actuales, con otra depuración programada que incluye los mismos archivos o ya depurado; 422 sin confirmar, con la frase distinta o con NUL; 404 carrera o alumno inexistente).
- `POST …/purgas/{purga_id}/cancelacion` (durante la gracia; repetir devuelve `repetido`; 409 si ya se eliminó) y `POST …/purgas/{purga_id}/ejecucion` (reintento manual de una purga ya vencida; 409 si aún no vence, está cancelada o se está ejecutando; 500 sin detalles internos si falla y queda registrada para reintento).
- La programación no elimina nada: marca los documentos «en depuración» y fija `ejecutar_en` = confirmación + 7 días. Una tarea de fondo de la API (intervalo `PURGA_INTERVALO_SEGUNDOS`, 60 s por omisión) ejecuta las purgas vencidas con bloqueo `SKIP LOCKED`: elimina los archivos de uno en uno (uno ausente cuenta como eliminado), marca las filas como archivadas y completa la purga en una transacción; un fallo deja la purga programada con `intentos` y `ultimo_error`.
- Se depuran los PDF que contiene el paquete (original y firmado de la versión aprobada vigente de cada reporte). Los originales de versiones rechazadas o reemplazadas, las notas, promedios, versiones, revisiones y el resultado congelado no se tocan.
- Expediente (`GET /dual/alumno/expediente` y `GET /dual/carrera/alumnos/{matricula}/expediente`): cada período incluye `archivo` (`estado` `normal|programada|archivado`, `eliminacion_en` y `archivado_en` como fechas civiles, `frase_esperada` y, solo para el personal, `purga_id`) y cada aprobado `archivado_en`; el `paquete` de un período depurado deja de estar disponible con el motivo.
- Descarga de un documento archivado (`…/versiones/{n}/pdf` de alumno, tutor y carrera): 410 con la fecha; la generación de paquetes de un período con archivos depurados responde 409.
- El fixture contractual contiene 68 rutas. [Spec C08B](../../specs/C08B-archivo-y-depuracion/spec.md) y [evidencia C08B](../../specs/C08B-archivo-y-depuracion/evidencia.md).

### Cambios implementados en C09 (DONE)

- Plantilla común (`/dual/plantillas`): `GET /vigente` (cualquier rol autenticado; `{"vigente": null}` si aún no hay), `GET /{numero}/{word|pdf}` (descarga autenticada con `Content-Disposition: attachment` y nombre generado `Plantilla_Reporte_Dual_v{n}.{docx|pdf}`; versión inexistente 404, tipo inválido 422), `GET /` (historial, solo coordinador) y `POST /` (multipart `word` + `pdf` + `nota` opcional, solo coordinador; 201 con la versión; 422 con el motivo si cualquiera de los dos no es válido, 413 sobre 10 MB; todo o nada). Las versiones son inmutables y la nueva pasa a ser la vigente en la misma transacción. Sin sesión 401; tutor y alumno 403 al publicar o consultar el historial. Se retira la descarga pública estática `/plantillas/*` del frontend.
- Buzón (DP-09 D1): responder a un hilo cerrado responde 409 para todos los roles y ya no lo reabre; `PATCH /foro/buzon/{id}/reabrir` (solo personal; devuelve `repetido`; el hilo pasa a «Leído» y registra autor e instante; alumno 403, sin sesión 401); `PATCH …/leido` no reabre un hilo cerrado; `POST /foro/buzon/` acepta `hilo_anterior_id` para enlazar un hilo propio cerrado (ajeno o inexistente 404, abierto 409) y el detalle devuelve `hilo_anterior_id`, `cerrado_en` y `reabierto_en`.
- Anuncios (DP-09 D2): `DELETE /foro/publicaciones/{id}` lo permite al autor y al coordinador (otro tutor 403, alumno 403); es una eliminación lógica que conserva el anuncio con autor e instante, deja de listarse y no admite reacciones (404); repetir devuelve 404. Los anuncios no se editan.
- Foro como pantalla inicial: tras el acceso obligatorio los tres roles aterrizan en `/foro` (frontend, `homeFor`).
- El fixture contractual contiene 73 rutas. [Spec C09](../../specs/C09-foro-buzon-y-plantillas/spec.md) y [evidencia C09](../../specs/C09-foro-buzon-y-plantillas/evidencia.md).

### Reglas objetivo generales


- Cliente no decide alumno propietario ni período escribiendo una etiqueta arbitraria.
- No inferir período objetivo de “único ciclo abierto”; usar obligación/período explícito.
- Fechas ISO YYYY-MM-DD; instantes con offset. Nota estrictamente entera, no truncar 8.5.
- Propuesta de error: código estable, mensaje y detalles de campos; nunca SQL, token ni stack al usuario.
- 401 sin sesión; 403 sin permiso; 404 objeto inexistente o ajeno según política consistente; 409 estado/conflicto; 413 tamaño; 422 datos inválidos.
- Reintento de cierre no duplica efectos. Doble click al entregar no crea dos versiones independientes aceptadas.
- Listados deben tener filtros y límites/paginación acordes al volumen; no descargar todos los PDFs al abrir tablero.
- Cambios incompatibles requieren actualización conjunta de backend/frontend y datos sintéticos.

Ejemplo conceptual de obligación: id, inicio_semana, fin_semana, periodo_id, estado_entrega, atrasado, puede_entregar, motivo_bloqueo. Diferenciar faltante de reporte pendiente de revisión; ningún “Pendiente” ambiguo en UI nueva.
