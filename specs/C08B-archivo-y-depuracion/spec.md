# C08B — Archivo y depuración

Estado: DRAFT
Fecha: 2026-10-16
Responsable de aprobación: responsable del proyecto
Dependencias: C08 DONE (2026-10-16); DP-14 resuelta en política el 2026-10-16. Bloqueada para pasar a READY por las decisiones D1 a D3 de abajo; DP-11 (respaldos y retención) sigue siendo de C10 y aquí solo se declara como límite.

## Problema y resultado esperado

C08 ya permite que el tutor genere el paquete ZIP de un período finalizado (por alumno o por carrera) y deja un registro inmutable de cada paquete generado (`paquetes_archivo`), pero los PDF originales y firmados siguen ocupando el almacenamiento (`dual-uploads`) para siempre. Ese registro acredita que el paquete se generó, no que alguien lo descargó ni que lo guardó fuera del sistema, y no existe ninguna operación para liberar espacio. DP-14 decidió que la depuración solo elimina los archivos PDF de un período, nunca las notas, los promedios, las versiones, las decisiones, las correcciones, los hashes ni el resultado congelado, y que debe pasar por advertencia, confirmación y la opción «Conservar todo».

Resultado esperado: el tutor ve, para un período finalizado, qué ocupan sus archivos y si ya generó el paquete; puede elegir «Conservar todo» (no pasa nada y se puede pedir después) o depurar los archivos tras una advertencia clara, la confirmación de que ya guardó la copia y la prueba de que el paquete correspondiente existe. La depuración se registra (autor, instante, alcance, cantidad y bytes, hash del manifiesto del paquete), es idempotente y se reintenta si se interrumpe; después el expediente sigue mostrando notas, promedios, grupo, versiones y decisiones, y marca los documentos como «archivados» con el motivo y la fecha, sin ofrecer una descarga que ya no existe.

## Fuentes y alcance

- US/RN/AC: [RN-16, RN-25 y RN-29](../../docs/analysis/REGLAS_DE_NEGOCIO.md) (RN-25 cambia para los períodos depurados: el alumno ya no descarga los PDF y se le avisa antes), AC-19 y AC-24 (restauración) de [criterios de aceptación](../../docs/analysis/CRITERIOS_DE_ACEPTACION.md).
- Documentos enlazados: [plan maestro](../../docs/construction/PLAN_MAESTRO.md), [DP-14 y DP-11](../../docs/analysis/DECISIONES_PENDIENTES.md), [modelo de datos](../../docs/analysis/MODELO_DE_DATOS.md), [archivos e importaciones](../../docs/analysis/CONTRATO_DE_ARCHIVOS_E_IMPORTACIONES.md), [contrato API](../../docs/analysis/CONTRATO_API.md), [roles](../../docs/analysis/MATRIZ_DE_ROLES_Y_PERMISOS.md), [C05](../C05-entregas-y-versiones/spec.md), [C07](../C07-cierre-y-calificacion/spec.md), [C08](../C08-expediente-y-visor/spec.md).

Incluye:

1. Estado «archivado» de los documentos: el original y el firmado de las versiones de un período depurado conservan su fila (clave, tamaño y SHA-256 originales como evidencia) con `archivado_en` y la purga que los archivó; el archivo físico se elimina. Notas, promedios, versiones, revisiones, correcciones y el resultado congelado de C07 no se tocan.
2. Registro de purgas (`purgas_archivo`, inmutable salvo la transición pendiente → completada): período, alcance, paquete de respaldo que la habilita, autor, instante de la intención, instante de término, archivos y bytes eliminados y errores.
3. Operación del tutor con tres pasos: ver el resumen de lo que se eliminaría, confirmar con la frase indicada que ya guardó la copia, y ejecutar. Dos fases idempotentes: primero se registra la intención y se marcan los documentos; después se eliminan los archivos con reintento; repetir la solicitud no vuelve a eliminar nada y reporta el estado. Un archivo ya ausente cuenta como eliminado. «Conservar todo» es la salida sin cambios.
4. Expediente, visor y paquetes ajustados: los documentos archivados no ofrecen «Ver», «Firmado» ni «Original», muestran «Archivado el <fecha>» y el aviso al alumno; el paquete de un período archivado ya no se puede generar (409 con el motivo); la descarga de un archivado responde 410 con el motivo, no 404.
5. Aviso al alumno antes de la purga (decisión D3) y contratos, cliente, fixtures, documentación, pruebas y preview de los recorridos afectados.

Excluye: respaldos, retención, restauración y responsable de respaldos (DP-11, C10: la depuración elimina los archivos del almacenamiento vivo y no alcanza copias de seguridad); borrado de cuentas, alumnos, notas o promedios; depuración automática o programada; reapertura o rectificación de un período (DP-10); plantillas, foro y buzón (C09).

## Decisiones

Confirmadas por DP-14: solo el tutor genera paquetes y depura; nada se borra sin un paquete previo; advertencia, confirmación de que ya guardó la copia y opción «Conservar todo»; solo se eliminan los PDF (original y firmado); se conserva todo lo demás; las filas de documentos pasan a «archivado»; dos fases idempotentes con intención registrada y borrado con reintento; la operación se audita.

Bloqueantes para pasar a READY (ver «Decisiones para el responsable» en la respuesta de cierre de C08): D1 alcance y prueba de que la copia existe, D2 quién puede depurar y D3 relación con la ventana del alumno y reversibilidad.

Propuestas técnicas (sujetas a esas decisiones):

- Alcance por carrera y período finalizado, igual que el paquete grande, con el prerrequisito de que exista en `paquetes_archivo` un paquete de carrera generado después de la finalización por ese mismo período y carrera; el hash del manifiesto de ese paquete se guarda en la purga. Una purga por alumno es posible con el paquete por alumno.
- Confirmación con frase exacta que nombra el período y la carrera (patrón type-to-confirm), botón de confirmar separado del que abre el diálogo, nombre del objetivo y la consecuencia irreversible en el texto y «Conservar todo» como acción segura destacada.
- Orden de las fases: transacción 1 (intención, estado de los documentos a «archivado», bloqueo del período contra nuevas lecturas de descarga); luego eliminación de archivos uno por uno con reintento idempotente; transacción 2 (término, cifras y errores). Un fallo a mitad deja la purga «pendiente» y reanudable; ninguna fila se borra de la base.
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
- Rutas del tutor: `GET /dual/carrera/periodos/{periodo_id}/archivo` (resumen: archivos y bytes por carrera, paquete vigente, purgas) y `POST /dual/carrera/periodos/{periodo_id}/purgas` (`carrera`, `confirmar` y la frase; 200 idempotente con el estado; 409 sin período finalizado, sin paquete previo o con una purga en curso; 403 a coordinador y alumno; 401 sin sesión).
- `GET …/versiones/{n}/pdf` y paquetes: 410 para documentos archivados; el expediente incluye `archivado` y `archivado_en` por documento y el estado de la purga del período.

Permisos y estados: solo el tutor; el alumno solo ve el aviso y el estado «archivado»; objeto inexistente 404; período no finalizado 409.

## Verificación

| AC | Prueba o recorrido | Nivel y datos | Resultado |
|---|---|---|---|
| C08B-AC1 | Sin paquete previo o sin confirmar la frase no se elimina nada; con paquete y confirmación se eliminan solo los PDF del alcance y las filas pasan a «archivado» | HTTP + PostgreSQL + almacenamiento reales | NO_VERIFICADA |
| C08B-AC2 | Notas, promedios, versiones, revisiones, correcciones, hashes y resultado congelado idénticos antes y después | PostgreSQL real | NO_VERIFICADA |
| C08B-AC3 | Interrupción a mitad (archivo en uso o fallo inyectado): la purga queda pendiente y reanudable; repetir no elimina de más ni falla por archivos ya ausentes | Fallos inyectados + almacenamiento real | NO_VERIFICADA |
| C08B-AC4 | Permisos: tutor sí; coordinador y alumno 403; sin sesión 401; alcance ajeno o período no finalizado 409/404 | Negativos HTTP reales | NO_VERIFICADA |
| C08B-AC5 | Expediente y visor: documentos archivados sin acciones de descarga, con fecha y aviso; descarga 410; el paquete de un período archivado 409 | HTTP real + preview visual | NO_VERIFICADA |
| C08B-AC6 | «Conservar todo» no cambia nada; el diálogo muestra advertencia, consecuencia irreversible, frase y está disponible en escritorio, móvil y con teclado | Preview visual | NO_VERIFICADA |
| C08B-AC7 | Registro de la purga inmutable (autor, instante, alcance, cifras, hash del manifiesto) | PostgreSQL real | NO_VERIFICADA |

## Evidencia de implementación

Sin ejecución: spec en DRAFT. Añadir solo después de implementar, con fecha, entorno, revisión del código y clase REAL/SIMULADA/NO_VERIFICADA.

## Revisión

Veredicto: pendiente.
Revisor y modalidad: pendiente.
Hallazgos materiales: no aplica antes de implementación.
Correcciones y verificación focal: no aplica.
Limitaciones previstas: los respaldos, la retención y la restauración (DP-11) son de C10 y la depuración no alcanza copias de seguridad; Drive y cualquier proveedor externo siguen NO_VERIFICADOS; el registro de paquetes acredita la generación, no la descarga.

## Aprobaciones y cierre

Pendiente: decisiones D1 a D3 y orden de pasar a READY.
