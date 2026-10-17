# C08 — Expediente y visor

Estado: DONE
Cierre: 2026-10-16
Fecha: 2026-10-16
Responsable de aprobación: responsable del proyecto
Dependencias: C07 DONE (2026-10-16). Alcance de la exportación y enfoque del visor decididos el 2026-10-16 (ver Decisiones); la depuración de archivos queda registrada como DP-14 y se implementa en C08B. Sin decisiones bloqueantes pendientes: DRAFT → READY → IN_PROGRESS el 2026-10-16 con la orden `IMPLEMENT C08`.

## Problema y resultado esperado

El expediente que existe es el de la demo: `GET /dual/carrera/alumnos/{matricula}/reportes` lee `reportes_dual` por `cuatrimestre` (texto) y por semana, con consultas que tratan el grado como período y ordenan por semana; el alumno no tiene pantalla "Mi expediente" (solo la lista de semanas de C05) y las lecturas de PDF (`/dual/alumno/reporte/{id}/pdf`, tutor y carrera) leen un puntero heredado (`archivo_pdf_local` o Drive) en lugar de los documentos versionados de C05 y C06. La exportación ZIP usa el grado como período por omisión, nombra los archivos por `semana_N` y, si un archivo falla, escribe un `_ERROR.txt` dentro del ZIP sin avisar; el CSV no protege valores interpretables como fórmulas. El directorio excluye a quienes ya tienen baja, contra RN-29. El visor embebido no ofrece alternativa clara si el navegador no muestra el PDF.

Resultado esperado: cada alumno consulta su expediente por período (grupo y carrera históricos del período, reportes aprobados con su nota validada, versión, firmado y original descargables, suma, cantidad y promedio provisional o final) y descarga sus aprobados de cualquier período; el personal (tutor y coordinador, las tres carreras) consulta el de cualquier alumno, incluidos los dados de baja; todas las descargas leen los documentos privados por identificador con autorización de objeto; el visor muestra el PDF autenticado, permite acercar, leer y descargar y, si falla, lo dice con una acción de reintento y sin ruta pública alternativa.

## Fuentes y alcance

- US: [US-10 y US-11](../../docs/analysis/ESPECIFICACION_FUNCIONAL.md).
- RN: [RN-04, RN-16, RN-22, RN-24, RN-25 y RN-29](../../docs/analysis/REGLAS_DE_NEGOCIO.md).
- AC: [AC-04 (parte de C08), AC-19 y AC-20](../../docs/analysis/CRITERIOS_DE_ACEPTACION.md).
- Documentos enlazados: [plan maestro](../../docs/construction/PLAN_MAESTRO.md), [modelo de datos](../../docs/analysis/MODELO_DE_DATOS.md), [archivos e importaciones (descarga y visor)](../../docs/analysis/CONTRATO_DE_ARCHIVOS_E_IMPORTACIONES.md), [contrato API](../../docs/analysis/CONTRATO_API.md), [UX (expediente)](../../docs/analysis/UX_Y_FLUJOS.md), [roles (MP-10)](../../docs/analysis/MATRIZ_DE_ROLES_Y_PERMISOS.md), [DP-10 y DP-11](../../docs/analysis/DECISIONES_PENDIENTES.md), [C03](../C03-grupos-e-incorporacion/spec.md), [C06](../C06-revision-y-firma/spec.md), [C07](../C07-cierre-y-calificacion/spec.md).

Incluye:

1. Expediente por alumno y período: períodos en los que el alumno tuvo semanas, con grupo y carrera históricos del período (`alumno_grupo_periodo`), estado de recepción y de evaluación, reportes aprobados (semana, fechas y nota validadas, versión, si tiene firmado), cantidad, suma y promedio con la etiqueta "provisional" o "final" (el final se lee del registro congelado de C07). Rutas propias del alumno y rutas del personal.
2. Descarga de aprobados por identificador de documento versionado: firmado (por defecto) y original, para el alumno propio y para el personal; objeto ajeno o inexistente 404, rol sin permiso 403 (AC-04). Reemplaza las lecturas heredadas por puntero; se retiran `GET /dual/alumno/mis-reportes` y las tres rutas `…/reporte/{id}/pdf` (alumno, tutor y carrera) con cliente, contrato y fixtures actualizados juntos.
3. Pantalla "Mi expediente" del alumno (selector de períodos, descarga de los suyos) y expediente del personal sobre el mismo contrato; el directorio del personal incluye a los dados de baja con un indicador, filtra por período, grupo y búsqueda y pagina por servidor (RN-29, MP-10).
4. Visor de PDF fiable (AC-20): carga autenticada con URL temporal de objeto que se libera al cerrar, zoom y lectura, descarga siempre visible, error claro con reintento y sin acceso público alternativo; verificado con PDF de una y varias páginas, escaneado y firmado, en escritorio y móvil.
5. Paquete de archivo en ZIP (decisión del 2026-10-16): el asesor académico (tutor) lo genera cuando el período está finalizado, por alumno o por carrera y período; incluye el firmado y el original de cada reporte aprobado y un manifiesto (matrícula, semana, fechas, nota validada, promedio y SHA-256 de cada archivo) con un resumen CSV protegido contra fórmulas. Nombres generados por el servidor, solo documentos del expediente autorizado y fallo explícito si no se puede leer un documento (sin archivos de error dentro del ZIP). Cada descarga queda registrada (quién, cuándo, alcance, hash del manifiesto): ese registro es el que habilita la depuración de C08B. El alumno descarga solo su propio ZIP durante una ventana de una semana desde que se finaliza la evaluación; la pantalla le avisa la fecha límite y, pasada, ya no lo ofrece (sus notas, promedios y el historial siguen visibles). No se borra ningún archivo en C08.
6. Dejar de tratar el grado como período en las lecturas de expediente, CSV y ZIP; contratos, cliente, fixtures, documentación, pruebas y preview de los recorridos afectados.

Excluye: depuración de archivos tras el archivo (DP-14, incremento C08B), plantillas (C09), foro y buzón (C09), restauración y recorrido integral (C10), respaldos (DP-11), reapertura o rectificación (DP-10), correcciones del tutor o firma (C06) y cierre o promedio (C07, solo se leen).

## Decisiones

Confirmadas: el alumno solo ve y descarga lo propio y el personal de las tres carreras consulta todo (MP-10, RN-04); el expediente conserva reportes aprobados, firma, notas, fechas, período y grupo histórico y el alumno descarga los suyos de cualquier período (RN-25); las bajas no borran expedientes (RN-29); el promedio es provisional hasta finalizar y final después, con dos decimales HALF_UP y "Sin calificación" sin aprobados (RN-22, DP-11); el original y el firmado son documentos distintos y ambos se conservan (RN-16); no se expone ninguna URL pública ni token de almacenamiento (contrato de archivos).

Propuestas técnicas incluidas para la futura aprobación de implementación (con las referencias de abajo):

- Rutas por identificador con autorización en el servidor sobre el objeto: por ejemplo `GET /dual/alumno/expediente`, `GET /dual/carrera/alumnos/{matricula}/expediente` y `GET …/versiones/{numero}/pdf?documento=firmado|original` ya existentes en C05 y C06 reutilizadas; consultas con alcance al alumno propio para que un identificador ajeno devuelva 404; sin recibir la matrícula del propietario en el cuerpo.
- El expediente se calcula de las tablas de C03 a C07 (pertenencias por período, obligaciones, versiones, revisiones y cierres), no del texto `cuatrimestre`; los reportes heredados sin obligación no se cuentan (limitación ya aceptada).
- Directorio con `limite` y `desplazamiento`, orden estable y total; filtro de bajas con indicador en lugar de ocultarlas; el filtro de período no usa « AND » en su texto (lección de C07: `resolve_query`).
- Documentos autorizados a la descarga tanto en línea (visor) como adjunto, con `Content-Disposition` y nombre generado (`<matricula>-S<ordinal>-<periodo>-firmado.pdf`), nunca el nombre del archivo del alumno.
- CSV: prefijo de protección para celdas que empiezan con `=`, `+`, `-`, `@`, tabulador o retorno de carro y comillas dobladas, probado en una hoja de cálculo real (OWASP advierte que no hay una estrategia universal y que Excel puede deshacer el prefijo al guardar y reabrir).
- ZIP generado con nombres que produce el servidor a partir de identificadores (sin texto del cliente), sin separadores de ruta ni `..`, nombres únicos y lectura de los documentos de uno en uno para no cargar todo el expediente en memoria cuando el volumen lo pida.

### Referencias de buenas prácticas consultadas

- Visor de PDF: los visores nativos (`<iframe>`, `<embed>`, `<object>`) funcionan bien en escritorio, pero en móvil el soporte es desigual (en varios Android descargan en vez de mostrar) y cambia con las versiones del navegador; las guías recomiendan un enlace visible de abrir o descargar como respaldo y reservan PDF.js autoalojado y fijado para cuando se necesita lectura embebida en móvil, a costa de construir la interfaz de navegación ([PDFObject](https://pdfobject.com/api/), [guía de Dynamsoft](https://dynamsoft.com/codepool/how-to-embed-pdf-in-html.html), [limitaciones del iframe según Syncfusion](https://www.syncfusion.com/blogs/post/iframe-pdf-embedding-limitations)). Las fuentes son de fechas mixtas: hay que probar en los dispositivos reales.
- Autorización de objeto: IDOR es la combinación de un objeto, su referencia y la falta de una comprobación de autorización en el servidor; la defensa es derivar el propietario de la base, acotar las consultas al usuario para que un identificador ajeno devuelva "no encontrado", aplicar lo mismo a los objetos anidados y negar por omisión; los identificadores aleatorios ayudan pero no sustituyen la comprobación ([OWASP IDOR Prevention Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Insecure_Direct_Object_Reference_Prevention_Cheat_Sheet.html)).
- CSV: la inyección de fórmulas se mitiga prefijando las celdas que empiezan con `=`, `+`, `-`, `@`, tabulador o retorno de carro y doblando las comillas, pero OWASP indica que no existe una estrategia segura para todas las hojas de cálculo y que Excel puede deshacer el prefijo al guardar y reabrir; la alternativa del tabulador altera los datos para quien los importe con código ([OWASP CSV Injection](https://owasp.org/www-community/attacks/CSV_Injection), [WSTG: pruebas de inyección CSV](https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/07-Input_Validation_Testing/21-Testing_for_CSV_Injection), [Symfony CVE-2021-41270](https://symfony.com/cve-2021-41270)).
- ZIP: los nombres dentro del archivo deben generarlos el servidor o salir de una lista de identificadores, normalizando separadores (también la barra invertida, causa de una vulnerabilidad real en File Browser) y descartando `..`; construir el ZIP completo en memoria consume tanta RAM como el archivo, por lo que existen generadores en flujo ([safezip](https://safezip.readthedocs.io), [aviso de File Browser](https://vulert.com/vuln-db/file-browser-archive-builder-turns-backslash-filenames-into-path-traversal-zip-slip-in-github-com-), [python-zipstream](https://github.com/DISCO-team/python-zipstream)). Los resultados no incluían el código de los proyectos, solo sus descripciones.

Resueltas por el responsable del proyecto el 2026-10-16 (registradas en [DECISIONES_PENDIENTES](../../docs/analysis/DECISIONES_PENDIENTES.md)):

1. **Exportación:** el ZIP es un paquete de archivo para que los asesores guarden los reportes fuera del sistema. Lo genera el asesor académico (tutor) con el período finalizado, por alumno o por carrera y período, con manifiesto y hashes; el alumno solo descarga el suyo durante una semana desde la finalización y se le avisa. Las notas, los promedios, las versiones y las decisiones se conservan siempre.
2. **Depuración (DP-14):** después de descargar el paquete, el asesor podrá depurar los archivos del período con una advertencia, una confirmación de que ya guardó la copia y la opción «Conservar todo». Solo se eliminan los archivos PDF; el resto del expediente se conserva. Se implementa en C08B, no aquí.
3. **Visor de PDF (delegado al agente por el responsable):** visor nativo sin dependencias nuevas, con descarga y «abrir en pestaña nueva» siempre visibles y, en móvil, el enlace de abrir o descargar como acción principal si el navegador no muestra el PDF; PDF.js autoalojado queda como alternativa solo si el preview o el responsable lo piden. Motivo: los visores nativos fallan de forma desigual en móvil y las guías recomiendan el respaldo de descarga antes que una dependencia (ver referencias).

Pendientes bloqueantes (DP): ninguno. Propuesta a confirmar al pasar a READY, sin bloquear: la ventana de una semana del alumno se cuenta desde la finalización de la evaluación (cuando el paquete ya es definitivo) y no desde el cierre de la recepción, porque el tutor aún puede aprobar reportes entre ambos.

No bloquean: DP-06, DP-09, DP-10 y DP-11 (retención, borrado y respaldos son de C10). Si durante la implementación aparece una decisión nueva que cambie permisos, notas o conservación, se detiene solo esa conducta y se presenta la decisión concreta.

## Contratos y cambios

Métodos/rutas/DTO y compatibilidad: expediente propio y del personal por período; descarga por documento versionado con autorización de objeto; directorio paginado con bajas; retiro de `GET /dual/alumno/mis-reportes` y de las rutas heredadas de lectura de PDF; exportación según la decisión; cliente, contrato estático (`route_contract.json`), OpenAPI y fixtures actualizados juntos.

Datos, restricciones y conservación: solo lecturas sobre las tablas existentes; sin migración de datos. Si el rendimiento lo exige se agregan índices en la migración `008_expediente.sql`, aditiva e idempotente. No se borra ni se reescribe historia. Base nueva de pruebas.

Permisos y estados: alumno solo lo propio; tutor y coordinador todas las carreras; objeto ajeno 404, rol sin permiso 403, sin sesión 401. El promedio mostrado es provisional o final según la evaluación del período.

Archivos/módulos previstos (se fijan al pasar a READY tras inspeccionar el diff base): `app/application/use_cases/dual/expediente.py` y retiro de las lecturas heredadas de `alumno_dual.py` y `coordinador_carrera.py`; `app/infrastructure/database/queries/dual_expediente.py`; routers y DTO; `app/infrastructure/documents` para la exportación; frontend: página "Mi expediente", expediente del personal, `VisorPDF.svelte`, directorio con paginación; pruebas (`test_c08_expediente.py`, contrato, smoke C08) y documentación.

Comportamiento ante fallos/reintentos: las descargas y el expediente son lecturas idempotentes; un documento que falta en el almacenamiento devuelve un error claro y no un archivo vacío; una exportación que no puede leer un documento falla completa.

## Verificación

| AC | Prueba o recorrido | Nivel y datos | Resultado |
|---|---|---|---|
| C08-AC1 / AC-19 | Alumno con dos períodos: cada uno muestra su grupo histórico, sus aprobados con documentos correctos y su promedio (provisional o final); descarga de firmado y original coincide byte a byte con lo guardado | HTTP + PostgreSQL + almacenamiento reales | REAL: `smoke_c08.py` (alumno con dos períodos y grupos distintos; promedios finales 9.00 y 9.50; original y firmado coinciden en SHA-256 con lo guardado); casos de uso con dobles SIMULADA |
| C08-AC2 / AC-04, RN-04 | Alumno cambia identificadores de expediente, reporte, versión o documento: 404; tutor de cualquier carrera y coordinador consultan; rol sin permiso 403; sin sesión 401; las rutas heredadas retiradas | Negativos HTTP reales | REAL: IDOR 404/403/401 y rutas heredadas retiradas en `smoke_c08.py` y smokes C02, C05, C06 |
| C08-AC3 / RN-29 | Un alumno dado de baja conserva su expediente, aparece en el directorio con indicador y sus aprobados se descargan | HTTP + PostgreSQL reales | REAL: alumnos de baja en el directorio (`situacion=baja`), expediente y descarga de aprobados |
| C08-AC4 | El directorio pagina con orden estable y total, filtra por período, grupo y búsqueda y no responde 500 con ninguna combinación (regresión de C07) | HTTP real | REAL: paginación con total, filtros por período, grupo, búsqueda y situación, comodines escapados, parámetros inválidos 422; regresión de C07 cubierta por `smoke_c07.py` |
| C08-AC5 / AC-20 | Visor: carga autenticada, zoom y lectura, descarga y "abrir"; error visible con reintento si falla; sin URL pública; PDF de una y varias páginas, escaneado y firmado | Preview visual del build desplegado | REAL parcial: carga autenticada, URL temporal y acciones «Abrir en pestaña nueva» y «Descargar» observadas en el navegador integrado; el navegador integrado no pinta PDF incrustados, así que zoom, lectura, PDF escaneado o de varias páginas y el error con reintento NO_VERIFICADA |
| C08-AC6 | Paquete ZIP por alumno y por carrera y período: solo con el período finalizado y solo el tutor; nombres generados, manifiesto con SHA-256 que coincide con los archivos, protección de fórmulas en el CSV probada en una hoja de cálculo, fallo explícito si falta un documento y descarga registrada | HTTP real + revisión manual de las exportaciones | REAL: ZIP por alumno y por carrera con hashes verificados contra los bytes, nombres generados, CSV con celda `=` protegida, 409 sin finalizar o con archivo faltante (sin registro), registro inmutable; apertura en una hoja de cálculo NO_VERIFICADA |
| C08-AC8 | Ventana del alumno: con la evaluación finalizada ve el aviso con la fecha límite y descarga solo su ZIP durante una semana; pasada la fecha 403 o 404 sin ofrecerlo; no descarga el de otro alumno ni el de la carrera; no se borra ningún archivo | HTTP + PostgreSQL reales con reloj de prueba | REAL con reloj SIMULADO moviendo la finalización con SQL: a 6 días 23 h descarga, a 8 días 403 y el expediente sigue; ZIP ajeno y de carrera 403/404; no se borra ningún archivo |
| C08-AC7 | "Mi expediente" y el expediente del personal en escritorio y móvil con teclado; promedios con la etiqueta correcta | Preview visual del build desplegado | REAL parcial: «Mi expediente» (alumno, vista angosta) y expediente y directorio del tutor (escritorio) en el navegador integrado; teclado, 375 px real y móvil físico NO_VERIFICADA |

## Evidencia de implementación

Implementación 2026-10-16 con Compose local; detalle en [evidencia.md](evidencia.md). Backend 190 pruebas OK; JS 35/35 y contrato 66 llamadas contra 64 rutas; Vite build sin avisos nuevos; `smoke_c08.py` PASS estable y smokes C01–C07 PASS tras adaptarlos a las rutas nuevas; instalación en base nueva (esquema + 003 a 008, 008 dos veces) sin errores. Entregado: expediente por período con grupo histórico (alumno y personal), directorio paginado con bajas, descarga de aprobados, visor con acciones de abrir y descargar, paquete ZIP por alumno y por carrera con manifiesto y hashes, ventana de una semana del alumno y registro inmutable de paquetes (`008_paquetes.sql`); rutas heredadas retiradas (64 rutas).

## Revisión

Veredicto: APPROVED (segunda revisión técnica, 2026-10-16).
Revisor y modalidad: mismo agente; técnica (diff, consultas, contratos, sondas HTTP) y visual del recorrido del alumno en vista angosta y del tutor en escritorio; no es revisión independiente.
Hallazgos materiales: M1 (la primera revisión, CHANGES_REQUESTED): el directorio y el expediente respondían 500 con `desplazamiento` fuera de rango y con un byte NUL; corregido con validación previa (422) y verificado con 190 pruebas, `smoke_c08.py` y `smoke_c07.py`; la segunda revisión no encontró defectos materiales.
Correcciones y verificación focal: ver [evidencia](evidencia.md).
Limitaciones: la depuración de archivos es C08B (DP-14); retención, borrado y respaldos (DP-11) y la restauración son de C10; el visor no se vio con PDF incrustados (el navegador integrado no los pinta), tampoco su error con «Reintentar», teclado, 375 px real ni móvil físico; la apertura del CSV en una hoja de cálculo no se probó; la ventana del alumno se probó con reloj simulado por SQL; el registro de paquetes acredita la generación, no la descarga; el paquete de una carrera no tiene límite de tamaño ni de tiempo; Drive y cualquier proveedor externo siguen NO_VERIFICADOS; los reportes heredados sin obligación no se cuentan; el directorio filtra por el grupo actual (el histórico está en el expediente).

## Aprobaciones y cierre

Aprobación de READY: el responsable decidió la exportación y la depuración (DP-14) el 2026-10-16, delegó el visor al agente y con `IMPLEMENT C08` autorizó pasar a READY y a IN_PROGRESS el mismo día; la propuesta de contar la semana del alumno desde la finalización de la evaluación se adopta al no haber objeción.
Aprobación de implementación: recibida mediante `IMPLEMENT C08` en este chat el 2026-10-16. Autoriza el alcance de esta spec, contratos, fixtures y documentación afectados; no autoriza C08B, C09, commit de implementación ni push (el commit se hace al aprobar el cierre).
Aprobación de cierre: pendiente.
Resumen final: pendiente.
Siguiente spec: C09 solo después de implementar, revisar y cerrar C08.
Commit/push: el commit local de implementación se hace al aprobar el cierre; no hay push salvo indicación explícita.

Aprobación de cierre: el responsable otorgó aprobación de cierre el 2026-10-16 con `CLOSE C08 + NEXT SPEC`, sujeta a revisión aprobada y evidencia suficiente. Con la segunda revisión APPROVED y la evidencia registrada, C08 queda DONE con las limitaciones anteriores. El commit local de implementación se hizo con el cierre; no hay push.
