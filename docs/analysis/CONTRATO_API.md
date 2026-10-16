# Contrato API: existente y objetivo

Estado: contrato vivo. C01–C06 describen rutas implementadas (C05 y C06 DONE); C07–C10 siguen como diseño propuesto. Fuentes ejecutables: routers en `ute-api-backend/app/presentation/api/routers`, `route_contract.json` y repositorios de `ute-dual-frontend/src/infrastructure/repositories`.

## Inventario actual

| Familia | Rutas principales existentes | Cambio requerido |
|---|---|---|
| Identidad | POST /auth/register, /login, /cambiar-password; GET /auth/me | Alinear esquema, sesiones y tres roles. |
| Tutores | POST/GET /auth/tutores; DELETE /auth/tutores/{usuario_id} | Baja lógica y revocación; confirmar contrato compatible. |
| Recuperación | POST /auth/alumnos/{matricula}/password-provisional | Conservar control tutor y cambio forzoso. |
| Alumno | GET /dual/alumno/mis-reportes, /obligaciones; POST /obligaciones/{id}/entrega; GET /reportes/{id}/versiones[/{n}/pdf] | Implementado en C04–C05: obligaciones independientes con versiones (retiradas `POST /dual/alumno/` y `GET /semana-actual`). |
| Revisión | GET /dual/tutor/reportes[/{reporte_id}]; POST /reportes/{id}/versiones/{n}/revision; GET /versiones/{n}/pdf | Implementado en C06: revisión por versión, correcciones trazables y firma (retirado el PATCH heredado). |
| Empresa | /dual/tutor/empresas, /asignaciones, /alumnos/{matricula} | Fecha real de inicio/baja y continuidad entre períodos. |
| Calendario | /dual/tutor/cuatrimestre-actual, /abrir-cuatrimestre, /cierre | Separar recepción/evaluación y autorización coordinador. |
| Firma | POST/GET /dual/tutor/firma | Versionar sin alterar firmados históricos. |
| Grupos/expediente | /dual/carrera/grupos, /alumnos, /periodos | Historia por período y consulta propia del alumno. |
| Descargas | /dual/alumno/reporte/{id}/pdf; equivalentes tutor/carrera; exportar-csv, exportar-zip | Autorización de objeto y contenido binario privado. |
| Foro | /foro/publicaciones y reacciones | Validar lectura/publicación y navegación. |
| Buzón | /foro/buzon/, /mios, /{id}, respuestas, leído y cierre | Probar conversación completa y autorización. |

Los prefijos carrera/coordinador_dual heredados no representan roles nuevos. No renombrar todo sin beneficio: adaptar cliente y servidor en el mismo incremento.

## Contrato objetivo a concretar en cada spec

| Operación propuesta | Entrada esencial | Resultado/garantía | Spec |
|---|---|---|---|
| Consultar obligaciones | período opcional, identidad en sesión | ID, intervalo, estado, atraso (implementado en C04; permiso de entregar y motivo de bloqueo llegan con C05) | C04 |
| Entregar versión | obligación_id, fechas declaradas, nota entera, PDF multipart | reporte_id, version_id y pendiente de revisión; 201 solo tras persistencia (implementado en C05) | C05 |
| Revisar versión | version_id, acción, fechas/nota validadas, nota de rechazo, versión esperada | Revisión trazable, sin sobrescribir versión nueva por concurrencia (implementado en C06) | C06 |
| Cerrar recepción | periodo_id y confirmación del coordinador | Cierre idempotente con autor/instante, mantiene revisión | C07 |
| Finalizar evaluación | periodo_id | Falla si hay pendientes; congela resultados atómicamente | C07 |
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
