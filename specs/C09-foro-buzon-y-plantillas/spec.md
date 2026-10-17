# C09 — Foro, buzón y plantillas

Estado: DONE
Cierre: 2026-10-17
Fecha: 2026-10-17
Responsable de aprobación: responsable del proyecto
Dependencias: C08 y C08B DONE (2026-10-17). D1 a D3 resueltas por el responsable el 2026-10-17 (ver Decisiones); DRAFT → READY → IN_PROGRESS el 2026-10-17 con la orden `IMPLEMENT C09`. Lo demás está confirmado en RN-26, RN-27 y RN-28.

## Problema y resultado esperado

- **Plantillas.** Las plantillas de reporte son tres archivos estáticos dentro del frontend (`public/plantillas/plantilla_word.docx`, `plantilla_excel.xlsx`, `plantilla_pdf.pdf`) que cualquiera puede pedir sin sesión y que solo cambian con un despliegue: el coordinador no puede publicarlas (US-13, MP-12), no hay versiones ni historial y no existe la pareja Word/PDF como una unidad.
- **Entrada al foro.** Tras el login, `homeFor` envía a cada rol a su pantalla de trabajo (`/dual/tutor`, `/dual/carrera` o `/dual/reportes`); el foro no es la pantalla inicial (RN-27, AC-22).
- **Buzón.** Existe la conversación alumno/personal (crear, listar, responder, marcar leído y cerrar), con la privacidad ya probada en C02. Pero responder a un hilo cerrado lo reabre solo, el cierre es de cualquier miembro del personal y no hay forma explícita de reabrir ni una política para los hilos cerrados (DP-09).
- **Anuncios.** Tutores y coordinador publican (alumno 403, probado en C02) y solo el autor puede eliminar lo suyo; no hay moderación ni conservación de lo eliminado (DP-09).

Resultado esperado: el coordinador publica una nueva pareja Word/PDF como una unidad atómica con historial de versiones y todos descargan la vigente con su sesión; el foro es la pantalla inicial de todos los roles tras completar el acceso obligatorio y desde él se llega a las herramientas de cada rol; el buzón sigue una política de cierre y reapertura explícita; los anuncios tienen la moderación decidida.

## Fuentes y alcance

- US/RN/AC: [US-05, US-13 y US-14](../../docs/analysis/ESPECIFICACION_FUNCIONAL.md), [RN-26, RN-27 y RN-28](../../docs/analysis/REGLAS_DE_NEGOCIO.md), [AC-21, AC-22 y AC-23](../../docs/analysis/CRITERIOS_DE_ACEPTACION.md).
- Documentos enlazados: [plan maestro](../../docs/construction/PLAN_MAESTRO.md), [modelo de datos (versiones_plantilla, foro, buzón)](../../docs/analysis/MODELO_DE_DATOS.md), [archivos e importaciones](../../docs/analysis/CONTRATO_DE_ARCHIVOS_E_IMPORTACIONES.md), [contrato API](../../docs/analysis/CONTRATO_API.md), [UX (foro y buzón)](../../docs/analysis/UX_Y_FLUJOS.md), [roles (MP-12 a MP-16)](../../docs/analysis/MATRIZ_DE_ROLES_Y_PERMISOS.md), [DP-09](../../docs/analysis/DECISIONES_PENDIENTES.md), [C02](../C02-identidad-y-accesos/spec.md), [C08](../C08-expediente-y-visor/spec.md).

Incluye:

1. Plantilla común versionada (RN-26): solo el coordinador publica (MP-12); una versión es una pareja Word + PDF completa o no existe; las versiones publicadas son inmutables y se conserva el historial (número, autor, instante, hashes y tamaños); la vigente es la última. Publicar una versión nueva no altera reportes ni documentos ya entregados.
2. Descarga autenticada de la versión vigente (y de las anteriores por número) para todos los roles (MP-13), por identificador y con nombres generados por el servidor; se retira la descarga estática pública y las pantallas dejan de enlazar `/plantillas/…`.
3. Pantalla del coordinador para publicar la pareja (carga de los dos archivos, validación visible, historial) y enlaces de descarga de la vigente para el alumno y el personal.
4. Foro como pantalla inicial de todos los roles tras el acceso obligatorio (RN-27, AC-22): el cambio de contraseña obligatorio sigue yendo primero; las herramientas de cada rol se alcanzan desde la navegación.
5. Buzón conforme a D1 (cierre y reapertura solo del personal, hilo cerrado de solo lectura y hilo nuevo enlazado) y comprobación de la conversación completa alumno, tutor, coordinador, alumno (AC-23) sin acceso de otros alumnos.
6. Anuncios conforme a D2 (el coordinador modera, eliminación lógica conservada, sin edición).
7. Contratos, cliente, fixtures, documentación, pruebas y preview de los recorridos afectados.

Excluye: cambios al reporte o a su revisión (C05 a C07), expediente, paquetes y depuración (C08, C08B), notificaciones por correo o push, adjuntos en el foro y el buzón, edición de anuncios (D2 propone no editar), respaldo y restauración (C10, DP-11) y reapertura o rectificación de períodos (DP-10).

## Decisiones

Confirmadas: la plantilla común sirve a las tres carreras y se versiona sin alterar reportes históricos (RN-26); el foro es la pantalla inicial de todos tras el acceso obligatorio y los tutores y el coordinador publican mientras los alumnos consultan (RN-27); el buzón es una conversación del alumno con todos los tutores y el coordinador y otros alumnos no la ven (RN-28); alumno 403 al publicar anuncios por API (AC-22); tutor y coordinador ven todo el buzón y el alumno solo sus hilos (MP-15, MP-16).

Resueltas por el responsable el 2026-10-17 (se registran en DP-09):

- D1 (DP-09): solo el personal (tutor y coordinador) cierra y reabre un hilo; un hilo cerrado es de solo lectura para todos, así que responder a él devuelve 409 con el motivo y el alumno, si necesita seguir, abre un hilo nuevo (la pantalla lo indica y puede enlazarlo con el anterior). Se retira la reapertura automática al responder; se añade la reapertura explícita del personal.
- D2 (DP-09): el autor elimina sus anuncios y el coordinador puede eliminar cualquiera; lo eliminado se conserva (eliminación lógica con autor e instante de la eliminación) y deja de mostrarse; los anuncios no se editan; las reacciones se mantienen.
- D3: la plantilla administrable es la pareja Word + PDF (RN-26). El Excel de asistencia deja de servirse como archivo público del frontend y queda fuera del sistema (el coordinador lo conserva y lo distribuye por su cuenta); si más adelante se quiere administrar, será otro incremento.

Propuestas técnicas (conformes con esas decisiones):

- Tabla `plantillas_version` con `numero` único y creciente, `publicada_por`, `publicada_en`, `vigente` (índice único parcial: una sola vigente), clave, tamaño y SHA-256 del Word y del PDF y número de páginas del PDF; disparadores que impiden modificar o borrar versiones salvo el cambio del indicador `vigente` hecho por la propia publicación. Los archivos se guardan con claves generadas por el servidor fuera de la carpeta pública, como los documentos de C05.
- Publicación atómica: se validan los dos archivos, se escriben ambos con claves nuevas y, en una sola transacción con bloqueo, se inserta la versión y se pasa la vigencia; si algo falla, se eliminan los archivos escritos y no queda pareja incompleta. El lector resuelve un único puntero (la versión vigente), nunca archivos sueltos.
- Validación de carga (OWASP): lista blanca de tipos, firma real del archivo (el PDF con el mismo inspector de C05; el DOCX como contenedor ZIP con `[Content_Types].xml` y `word/document.xml`), límite de tamaño en el servidor, límite de entradas y de tamaño descomprimido contra bombas ZIP, nombre del cliente ignorado y macros no permitidas (sin `vbaProject.bin`).
- Rutas: `GET /dual/plantillas/vigente` (metadatos y enlaces para cualquier rol autenticado), `GET /dual/plantillas/{numero}/{tipo}` (`tipo` `word|pdf`), `GET /dual/plantillas` (historial, coordinador) y `POST /dual/plantillas` (multipart con los dos archivos, solo coordinador, 409 sin cambios si cualquiera falla).
- Inicio: la primera versión la publica el coordinador con la interfaz; hasta entonces las pantallas muestran que no hay plantilla vigente en lugar de caer a un archivo público; los archivos estáticos actuales se retiran del frontend en el mismo incremento (C10 documenta la carga inicial en la guía de operación).
- Foro como inicio: `homeFor` devuelve `/foro` para los tres roles salvo cambio de contraseña obligatorio; la navegación ya existente lleva a «Mis reportes» y a las pantallas de personal.

### Referencias de buenas prácticas consultadas

Consultadas el 2026-10-17 (resúmenes de terceros y patrones de documentación de productos, no normas; criterio de diseño, no requisito):

- [OWASP File Upload Cheat Sheet, resumida en una guía de OPSWAT](https://www.opswat.com/solutions/file-security/compliance/owasp-file-upload-cheat-sheet), [Secure File Uploads (Guidewire)](https://docs.guidewire.com/security/secure-coding-guidance/file-upload-vulnerabilities) y [referencia sobre carga de archivos](https://knowledgelib.io/software/security/file-upload-security/2026.md): validar extensión y firma real (no solo el encabezado ni el nombre), límites de tamaño en el servidor, límites de descompresión para formatos ZIP como DOCX, nombres generados por el servidor y almacenamiento fuera de la raíz web. La búsqueda no devolvió la guía primaria de OWASP ni validación específica de OOXML: leer la hoja original al implementar.
- [Publicación atómica con un puntero a la versión vigente (nota de diseño)](https://fablepool.com/artifacts/888) y [intercambio atómico de dos ranuras (Instatic)](https://instagit.com/CoreBunch/Instatic/instatic-two-slot-symlink-swap-atomic-publishing-work/): escribir completa la versión nueva e inmutable y cambiar un único puntero en un solo paso; el lector solo ve la versión anterior completa o la nueva completa; volver atrás es apuntar a una versión anterior.
- [Reabrir o no un ticket cerrado (Hornbill)](https://community.hornbill.com/topic/19529-customersusers-reopening-ticket-via-employee-portal/), [responder a un ticket cerrado (VIU)](https://ithelp.viu.ca/TDClient/169/ITPortal/KB/Article/2733/How-do-I-re-open-an-old-or-closed-ticket), [reapertura por ventana de tiempo (HubSpot)](https://knowledge.hubspot.com/help-desk/manage-reopened-tickets-in-help-desk?data=data) y [avisar al personal en lugar de reabrir (Atlassian)](https://community.atlassian.com/forums/Jira-Service-Management/Allowing-customer-to-reopen-an-issue-from-Closed-or-Resolved/qaq-p/1024316): una respuesta a un hilo cerrado se pierde porque el hilo cerrado sale de las vistas del personal; hay que elegir y documentar una política (reabrir, abrir un hilo nuevo enlazado o dejar cerrado y avisar) y evitar que respuestas de cortesía reabran hilos.

## Contratos y cambios

Propuesta mínima, a concretar al aprobar las decisiones:

- Migración `010_plantillas.sql` (versiones de plantilla inmutables con vigencia única) y, según D1 y D2, columnas de cierre y reapertura en el buzón y de eliminación conservada en los anuncios.
- Rutas de plantillas (arriba), `PATCH /foro/buzon/{id}/reabrir` y la regla de respuesta en hilos cerrados según D1, y la eliminación de anuncios según D2.
- Cliente, rutas protegidas, `homeFor` y navegación del frontend; fixtures contractuales y pruebas actualizados juntos.

Permisos y estados: publicar plantillas solo el coordinador; descargarlas todos los roles autenticados, sin sesión 401; publicar anuncios tutor y coordinador (alumno 403); buzón con hilos propios para el alumno y todos para el personal; objeto ajeno 404.

## Verificación

| AC | Prueba o recorrido | Nivel y datos | Resultado |
|---|---|---|---|
| C09-AC1 / AC-21 | El coordinador publica una pareja Word/PDF: todos descargan la vigente; si falla la validación o el guardado de cualquiera de los dos archivos no se publica nada y quedan limpios; las versiones anteriores siguen disponibles e inmutables | HTTP + PostgreSQL + almacenamiento reales con fallos inyectados | REAL: `smoke_c09.py` (publicación todo o nada, descargas byte a byte, vigente única, anteriores inmutables y disponibles; rechazos sin filas ni archivos sueltos); fallos del almacenamiento con dobles SIMULADA |
| C09-AC2 | Carga maliciosa rechazada (tipo falso, DOCX con macros, ZIP sobredimensionado, PDF dañado, nombre con rutas); tutor y alumno 403 al publicar; sin sesión 401 | Negativos HTTP reales | REAL: tipo falso, DOCX con macros o tipo macro, rutas con `..`, bomba ZIP, `.doc`, PDF dañado o falso, falta uno de los archivos y 413; tutor y alumno 403 y sin sesión 401 |
| C09-AC3 / AC-22 | El login termina en el foro para los tres roles y el cambio obligatorio ocurre antes; el alumno no publica anuncios por API | HTTP real + preview visual | REAL parcial: el alumno no publica anuncios (403); el login de coordinador y alumno termina en `/foro` en el navegador integrado y el cambio obligatorio va antes (pruebas JS de `homeFor`); el login de tutor no se recorrió en pantalla |
| C09-AC4 / AC-23 | Alumno envía, tutor responde, coordinador consulta y alumno responde: la conversación persiste y otro alumno recibe 404 | HTTP + PostgreSQL reales | REAL: alumno, tutor, coordinador y alumno conversan y el hilo persiste en orden; otro alumno 404 al ver, responder y 403 al reabrir |
| C09-AC5 | La política del hilo cerrado de D1: quién cierra, qué pasa al responder, reapertura y límites | HTTP real | REAL: cierre solo del personal, 409 al responder (alumno, tutor y coordinador), marcar leído no reabre, la base rechaza respuestas en un hilo cerrado, reapertura explícita idempotente, hilo nuevo enlazado (ajeno 404, abierto 409) |
| C09-AC6 | Moderación de anuncios de D2: quién elimina, qué se conserva y qué ve cada rol | HTTP + PostgreSQL reales | REAL: el autor y el coordinador eliminan, otro tutor y el alumno 403, el anuncio se conserva con autor e instante y deja de listarse, la base rechaza editar o restablecer |
| C09-AC7 | Plantilla, foro y buzón en escritorio y móvil con teclado | Preview visual del build desplegado | REAL parcial: plantilla (coordinador y alumno), buzón con hilo cerrado y enlace, foro con moderación y navegación en el navegador integrado a 623 px; teclado, tema oscuro y móvil físico NO_VERIFICADA |

## Evidencia de implementación

Implementación 2026-10-17 con Compose local; detalle en [evidencia.md](evidencia.md). Backend 237 pruebas OK (23 nuevas); JS 40/40 y contrato 75 llamadas contra 73 rutas; Vite build sin avisos nuevos propios; `smoke_c09.py` PASS (dos corridas) y smokes C01–C08B PASS; migración `010_plantillas_foro.sql` aplicada dos veces. Entregado: plantilla común Word + PDF versionada y atómica con validación real de la carga, descarga autenticada y pantalla del coordinador (se retiran los archivos estáticos públicos), foro como pantalla inicial de los tres roles, política del buzón de D1 (hilo cerrado de solo lectura, reapertura del personal, hilo nuevo enlazado) y moderación de anuncios de D2 (eliminación lógica conservada). Revisada (APPROVED) y cerrada el 2026-10-17.

## Revisión

Veredicto: APPROVED (revisión técnica, 2026-10-17).
Revisor y modalidad: mismo agente; técnica (diff completo, migración, consultas, permisos, contratos y evidencia) y visual reutilizando el preview de la implementación más el login de tutor en pantalla; no es revisión independiente.
Hallazgos materiales: ninguno.
Correcciones y verificación focal: no aplica; los defectos hallados durante la implementación están en [evidencia](evidencia.md).
Limitaciones: no se subieron archivos desde el formulario del navegador (el navegador integrado no permite elegir archivos; la publicación se probó por HTTP real) y el estado «aún no hay plantilla vigente» solo está cubierto por pruebas; teclado completo, tema oscuro y móvil físico; apertura de la plantilla en Word real u otros editores; la validación del DOCX no revisa relaciones externas ni objetos incrustados más allá de macros, rutas, tamaño y compresión, y no hay antivirus; la plantilla inicial la publica el coordinador (los archivos antiguos siguen en el historial de git) y el Excel de asistencia queda fuera del sistema (D3); sin notificaciones por correo; respaldos y restauración son de C10 (DP-11); Drive y cualquier proveedor externo siguen NO_VERIFICADOS.

## Aprobaciones y cierre

D1 a D3 aprobadas por el responsable el 2026-10-17 (tal como se recomendaron). Con `IMPLEMENT C09` autorizó pasar a READY y a IN_PROGRESS el 2026-10-17.

Aprobación de cierre: el responsable otorgó aprobación de cierre el 2026-10-17 con `CLOSE C09 + NEXT SPEC`, sujeta a revisión aprobada y evidencia suficiente. Con la revisión APPROVED y la evidencia registrada, C09 queda DONE con las limitaciones anteriores. El commit local de implementación se hizo con el cierre; no hay push.
