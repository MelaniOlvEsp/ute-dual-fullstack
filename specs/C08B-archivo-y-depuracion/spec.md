# C08B — Archivo y depuración

Estado: DONE
Cierre: 2026-10-17
Fecha: 2026-10-16
Responsable de aprobación: responsable del proyecto
Dependencias: C08 DONE (2026-10-16); DP-14 resuelta en política el 2026-10-16. D1 a D3 resueltas por el responsable el 2026-10-16 (ver Decisiones); la tarea de fondo de D3 (propuesta mínima, sin cola ni servicio nuevo) se adopta al no haber objeción; DRAFT → READY → IN_PROGRESS el 2026-10-16 con la orden `IMPLEMENT C08B`. DP-11 (respaldos y retención) sigue siendo de C10 y aquí solo se declara como límite.

## Problema y resultado esperado

C08 ya permite que el tutor genere el paquete ZIP de un período finalizado (por alumno o por carrera) y deja un registro inmutable de cada paquete generado (`paquetes_archivo`), pero los PDF originales y firmados siguen ocupando el almacenamiento (`dual-uploads`) para siempre. Ese registro acredita que el paquete se generó, no que alguien lo descargó ni que lo guardó fuera del sistema, y no existe ninguna operación para liberar espacio. DP-14 decidió que la depuración solo elimina los archivos PDF de un período, nunca las notas, los promedios, las versiones, las decisiones, las correcciones, los hashes ni el resultado congelado, y que debe pasar por advertencia, confirmación y la opción «Conservar todo».

Resultado esperado: el tutor ve, para un período finalizado, qué ocupan sus archivos y si ya generó el paquete; puede elegir «Conservar todo» (no pasa nada y se puede pedir después) o depurar los archivos tras una advertencia clara, la confirmación de que ya guardó la copia y la prueba de que el paquete correspondiente existe. La depuración se registra (autor, instante, alcance, cantidad y bytes, hash del manifiesto del paquete), es idempotente y se reintenta si se interrumpe; después el expediente sigue mostrando notas, promedios, grupo, versiones y decisiones, y marca los documentos como «archivados» con el motivo y la fecha, sin ofrecer una descarga que ya no existe.

## Fuentes y alcance

- US/RN/AC: [RN-16, RN-25 y RN-29](../../docs/analysis/REGLAS_DE_NEGOCIO.md) (RN-25 cambia para los períodos depurados: el alumno ya no descarga los PDF y se le avisa antes), AC-19 y AC-24 (restauración) de [criterios de aceptación](../../docs/analysis/CRITERIOS_DE_ACEPTACION.md).
- Documentos enlazados: [plan maestro](../../docs/construction/PLAN_MAESTRO.md), [DP-14 y DP-11](../../docs/analysis/DECISIONES_PENDIENTES.md), [modelo de datos](../../docs/analysis/MODELO_DE_DATOS.md), [archivos e importaciones](../../docs/analysis/CONTRATO_DE_ARCHIVOS_E_IMPORTACIONES.md), [contrato API](../../docs/analysis/CONTRATO_API.md), [roles](../../docs/analysis/MATRIZ_DE_ROLES_Y_PERMISOS.md), [C05](../C05-entregas-y-versiones/spec.md), [C07](../C07-cierre-y-calificacion/spec.md), [C08](../C08-expediente-y-visor/spec.md).

Incluye:

1. Estado «archivado» de los documentos: el original y el firmado de las versiones de un período depurado conservan su fila (clave, tamaño y SHA-256 originales como evidencia) con `archivado_en` y la purga que los archivó; el archivo físico se elimina. Notas, promedios, versiones, revisiones, correcciones y el resultado congelado de C07 no se tocan.
2. Registro de purgas (`purgas_archivo`, inmutable salvo la transición pendiente → completada): período, alcance, paquete de respaldo que la habilita, autor, instante de la intención, instante de término, archivos y bytes eliminados y errores.
3. Operación del tutor o del coordinador con tres pasos: ver el resumen de lo que se eliminaría, confirmar con la frase indicada que ya guardó la copia, y programar. Con período de gracia de 7 días (D3): al confirmar se registra la intención y los documentos se marcan «en depuración» sin eliminar nada; durante la gracia cualquiera de los dos roles puede cancelar y todo sigue igual; al vencer, se eliminan los archivos con reintento. Repetir la solicitud no vuelve a eliminar nada y reporta el estado. Un archivo ya ausente cuenta como eliminado. «Conservar todo» es la salida sin cambios.
4. Expediente, visor y paquetes ajustados: los documentos archivados no ofrecen «Ver», «Firmado» ni «Original», muestran «Archivado el <fecha>» y el aviso al alumno; el paquete de un período archivado ya no se puede generar (409 con el motivo); la descarga de un archivado responde 410 con el motivo, no 404.
5. Aviso al alumno antes de la purga (decisión D3) y contratos, cliente, fixtures, documentación, pruebas y preview de los recorridos afectados.

Excluye: respaldos, retención, restauración y responsable de respaldos (DP-11, C10: la depuración elimina los archivos del almacenamiento vivo y no alcanza copias de seguridad); borrado de cuentas, alumnos, notas o promedios; reapertura o rectificación de un período (DP-10); plantillas, foro y buzón (C09).

## Decisiones

Confirmadas por DP-14: solo el tutor genera paquetes y depura; nada se borra sin un paquete previo; advertencia, confirmación de que ya guardó la copia y opción «Conservar todo»; solo se eliminan los PDF (original y firmado); se conserva todo lo demás; las filas de documentos pasan a «archivado»; dos fases idempotentes con intención registrada y borrado con reintento; la operación se audita.

Resueltas por el responsable el 2026-10-16 (se registran en DP-14):

- D1: la depuración puede hacerse por carrera y período finalizado y también por alumno. Exige el paquete correspondiente (de carrera o del alumno) generado después de la finalización y registrado en `paquetes_archivo`, la confirmación de que ya lo guardó y la frase escrita; el hash del manifiesto de ese paquete se guarda en la purga.
- D2: pueden depurar el tutor y el coordinador. Generar el paquete sigue siendo solo del tutor (DP-14), así que el prerrequisito lo cubre el tutor; el alumno no depura.
- D3: período de gracia de 7 días. Al confirmar, los documentos quedan «en depuración» y se eliminan automáticamente al vencer la gracia; durante ese tiempo tutor o coordinador pueden cancelar. La ventana de descarga del alumno (una semana desde la finalización) es independiente: la depuración puede programarse en cualquier momento, y el alumno ve el aviso de la fecha de eliminación; si la eliminación llega antes de que termine su ventana, el aviso lo dice y la descarga termina ese día. Pasada la eliminación es irreversible en el sistema; solo existirían respaldos, que son de C10 (DP-11).

Consecuencia técnica de D3 a confirmar al pasar a READY: la eliminación al vencer la gracia necesita un proceso que la ejecute sin intervención. Propuesta mínima: una tarea de fondo de la API que revisa las purgas vencidas y las reintenta, más una acción manual «Ejecutar ahora» solo para reintentar una purga vencida; sin cola ni servicio nuevo.

Propuestas técnicas (sujetas a esas decisiones):

- Alcance por carrera y período finalizado o por alumno y período, con el prerrequisito de que exista en `paquetes_archivo` el paquete del mismo alcance generado después de la finalización; el hash del manifiesto de ese paquete se guarda en la purga.
- Confirmación con frase exacta que nombra el período y la carrera (patrón type-to-confirm), botón de confirmar separado del que abre el diálogo, nombre del objetivo y la consecuencia irreversible en el texto y «Conservar todo» como acción segura destacada.
- Orden de las fases: transacción 1 (intención con fecha de eliminación = confirmación + 7 días, documentos «en depuración», cancelable); al vencer, transacción 2 (documentos «archivado») y eliminación de archivos uno por uno con reintento idempotente; transacción 3 (término, cifras y errores). Un fallo a mitad deja la purga «pendiente» y reanudable; ninguna fila se borra de la base. Cancelar durante la gracia devuelve los documentos a su estado normal y queda registrado.
- Descargas: la lectura de un documento archivado devuelve 410 antes de tocar el almacenamiento.

### Referencias de buenas prácticas consultadas

Consultadas el 2026-10-16 (patrones de profesionales y documentación de productos, no normas; usarlas como criterio de diseño, no como requisito):

- [Soft vs. hard delete con periodo de gracia, purga idempotente y registro de lo purgado](https://www.designgurus.io/answers/detail/how-would-you-implement-soft-vs-hard-ttl-for-gdpr-deletion): la fase blanda marca, la dura elimina con tareas idempotentes y deja un resumen de lo purgado; los respaldos inmutables no se reescriben (límite que se declara aquí y se resuelve en C10 con DP-11).
- [Idempotent delete (Brandur)](https://brandur.org/fragments/idempotent-delete): repetir la eliminación es seguro; distinguir «ya eliminado» (410) de «nunca existió» (404).
- [Marking data for deletion (BMC)](https://docs.bmc.com/docs/serverautomation/231/marking-data-for-deletion-1159149764.html) y [Understanding database cleanup](https://docs.helixops.ai/bin/Automation-DevSecOps/Server-Automation/BMC-Server-Automation/bsa83/Administering/Cleaning-up-BMC-Server-Automation-data/Understanding-database-cleanup/): marcar primero y eliminar después en un paso separado; los archivos del servidor se limpian aparte de la base, por lo que hay que poder reintentar y detectar archivos huérfanos o pendientes.
- [Confirm destructive actions (Vercel Geist)](https://vercel.com/geist/destructive-action-modal), [Confirm a destructive action (Alberta)](https://v2.design.alberta.ca/examples/confirm-a-destructive-action) y [Designing Confirmation](https://uxdesign.cc/designing-confirmation-278d159723e): confirmación solo para lo realmente destructivo, frase escrita para lo más peligroso, nombrar el objetivo y la irreversibilidad y no repetir la posición del botón que abrió el diálogo.

## Contratos y cambios

Propuesta mínima, a concretar al aprobar las decisiones:

- Migración `009_depuracion.sql`: `documentos.archivado_en`, `documentos.purga_id`; tabla `purgas_archivo` (período, carrera, paquete_id de respaldo con su hash de manifiesto, autor, intención, término, archivos, bytes, errores, estado); disparadores que impiden borrar filas y modificar lo ya registrado salvo el cierre de la purga; RLS y permisos como `paquetes_archivo`.
- Rutas del tutor: `GET /dual/carrera/periodos/{periodo_id}/archivo` (resumen: archivos y bytes por carrera, paquete vigente, purgas) y `POST /dual/carrera/periodos/{periodo_id}/purgas` (`carrera` o `matricula`, `confirmar` y la frase; 200 idempotente con el estado y la fecha de eliminación; 409 sin período finalizado, sin paquete previo del mismo alcance o con una purga en curso; 403 a alumno; 401 sin sesión), `POST …/purgas/{purga_id}/cancelacion` (durante la gracia) y `POST …/purgas/{purga_id}/ejecucion` (solo reintento de una purga vencida).
- `GET …/versiones/{n}/pdf` y paquetes: 410 para documentos archivados; el expediente incluye `archivado` y `archivado_en` por documento y el estado de la purga del período.

Permisos y estados: tutor y coordinador (D2); el alumno solo ve el aviso con la fecha de eliminación y el estado «archivado»; objeto inexistente 404; período no finalizado 409.

## Verificación

| AC | Prueba o recorrido | Nivel y datos | Resultado |
|---|---|---|---|
| C08B-AC1 | Sin paquete previo o sin confirmar la frase no se elimina nada; con paquete y confirmación se eliminan solo los PDF del alcance y las filas pasan a «archivado» | HTTP + PostgreSQL + almacenamiento reales | REAL: `smoke_c08b.py` (409 sin paquete; 422 sin confirmar o con frase distinta; con paquete y frase se programa y, al vencer, se eliminan solo los PDF del paquete) |
| C08B-AC2 | Notas, promedios, versiones, revisiones, correcciones, hashes y resultado congelado idénticos antes y después | PostgreSQL real | REAL: notas, promedios congelados, versiones y revisiones idénticos antes y después; filas archivadas con clave y hash originales; los originales rechazados siguen en disco |
| C08B-AC3 | Interrupción a mitad (archivo en uso o fallo inyectado): la purga queda pendiente y reanudable; repetir no elimina de más ni falla por archivos ya ausentes | Fallos inyectados + almacenamiento real | REAL: un directorio ocupando el lugar del archivo hace fallar la eliminación (500 sin detalles internos), la purga queda programada con intento y error y sin filas archivadas; tras restaurar, el reintento la completa; ausentes cuentan como eliminados en pruebas con dobles |
| C08B-AC4 | Permisos: tutor y coordinador sí; alumno 403; sin sesión 401; alcance ajeno o período no finalizado 409/404 | Negativos HTTP reales | REAL: tutor y coordinador programan, cancelan y ven el resumen; alumno 403; sin sesión 401; carrera inexistente y período ajeno 404; frase con NUL 422; conflicto entre alcances 409 |
| C08B-AC5 | Expediente y visor: documentos archivados sin acciones de descarga, con fecha y aviso; descarga 410; el paquete de un período archivado 409 | HTTP real + preview visual | REAL: descarga de aprobados archivados 410 (personal, alumno y tutor), paquetes 409, expediente con «Archivado el …» y sin acciones; visual en navegador integrado |
| C08B-AC6 | «Conservar todo» no cambia nada; el diálogo muestra advertencia, consecuencia irreversible, frase y está disponible en escritorio, móvil y con teclado | Preview visual | REAL parcial: diálogo con advertencia, consecuencia irreversible, confirmación y frase observado en escritorio (el botón queda deshabilitado con una frase distinta); alumno a 375 px sin desborde; «Conservar todo» y el teclado completo NO_VERIFICADA |
| C08B-AC7 | Registro de la purga inmutable (autor, instante, alcance, cifras, hash del manifiesto) | PostgreSQL real | REAL: UPDATE y DELETE de purgas y cambios de hash o restablecimiento de archivado en documentos rechazados por la base; el registro guarda autor, instante, alcance, cifras y el hash del manifiesto del paquete |
| C08B-AC8 | Período de gracia: durante los 7 días no se elimina nada y se puede cancelar; al vencer se eliminan los archivos sin intervención y se reintenta si falla; el alumno ve la fecha de eliminación | HTTP + PostgreSQL + almacenamiento reales con reloj de prueba | REAL con reloj SIMULADO por SQL: 7 días de gracia sin eliminar nada, cancelación, repetición idempotente, la tarea de fondo real ejecuta la purga vencida (y la ejecución manual reintenta); el alumno ve la fecha de eliminación |

## Evidencia de implementación

Implementación 2026-10-17 con Compose local; detalle en [evidencia.md](evidencia.md). Backend 214 pruebas OK (23 nuevas en `test_c08b_depuracion.py`); JS 39/39 y contrato 70 llamadas contra 68 rutas; Vite build sin avisos nuevos propios (un aviso de accesibilidad de región desplazable como en C08); `smoke_c08b.py` PASS (dos corridas) y smokes C01–C08 PASS; instalación en base nueva (esquema + 003 a 009, 009 dos veces) sin errores. Entregado: `009_depuracion.sql` (purgas_archivo y estado de archivado en documentos con disparadores), programación con gracia de 7 días, cancelación, ejecución por tarea de fondo con reintento (`SKIP LOCKED`) y manual, 410 en descargas, paquetes bloqueados tras depurar, aviso al alumno y panel del personal. Revisada (APPROVED) y cerrada el 2026-10-17.

## Revisión

Veredicto: APPROVED (revisión técnica, 2026-10-17).
Revisor y modalidad: mismo agente; técnica (diff completo, consultas SQL, permisos, conservación del historial, contratos y evidencia); la visual reutilizó el preview de la implementación porque la interfaz no cambió; no es revisión independiente.
Hallazgos materiales: ninguno.
Correcciones y verificación focal: no aplica; los defectos hallados durante la implementación están en [evidencia](evidencia.md).
Limitaciones: la gracia de 7 días se probó con reloj simulado por SQL; no se probó «Conservar todo», el teclado completo del diálogo, tema oscuro ni móvil físico; la tarea de fondo no se probó con más de un proceso; la depuración no alcanza copias de seguridad (DP-11, C10); los originales de versiones rechazadas o reemplazadas no están en el paquete y permanecen en el almacenamiento (interpretación acotada de «archivos del período», registrada en DP-14); el registro de paquetes acredita la generación y la confirmación de «ya guardé la copia» es una declaración del usuario; Drive y cualquier proveedor externo siguen NO_VERIFICADOS.

## Aprobaciones y cierre

D1 a D3 resueltas por el responsable el 2026-10-16. Con `IMPLEMENT C08B` autorizó pasar a READY y a IN_PROGRESS el mismo día; la tarea de fondo de D3 se adopta al no haber objeción. Interpretación acotada al implementar: la depuración elimina los PDF que contiene el paquete (original y firmado de la versión aprobada vigente de cada reporte); los originales de versiones rechazadas o reemplazadas no están en el paquete y no se tocan, para no destruir lo que no se archivó.

Aprobación de cierre: el responsable otorgó aprobación de cierre el 2026-10-17 con `CLOSE C08B`, tras la revisión técnica APPROVED y con la evidencia registrada. C08B queda DONE con las limitaciones anteriores. El commit local de implementación se hizo con el cierre; no hay push.
