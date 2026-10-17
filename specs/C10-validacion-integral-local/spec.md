# C10 — Validación integral local

Estado: DRAFT
Fecha: 2026-10-17
Responsable de aprobación: responsable del proyecto
Dependencias: C09 DONE (2026-10-17) y C10A (con D1 y D2 resueltas) (almacenamiento en Drive; el responsable decidió el 2026-10-17 que los archivos y los respaldos viven en Drive y que no se guarda nada local). D2 (almacenamiento del piloto) quedó resuelta con esa decisión; D1 (política de respaldos, DP-11) resuelta el 2026-10-17; sigue bloqueada para pasar a READY solo por C10A (debe estar DONE) y por la orden de pasar a READY.

## Problema y resultado esperado

C01 a C09 se verificaron incremento por incremento: cada uno tiene su smoke con HTTP, PostgreSQL y almacenamiento reales, pero ninguna prueba recorre el producto completo con las tres cuentas a la vez, los controles negativos se repartieron entre specs y la recuperación nunca se ha probado: no existe un procedimiento de respaldo ni de restauración, no hay guía de uso y operación y `docs/construction/VALIDACION_Y_OPERACION_LOCAL.md` sigue siendo una guía de preparación con comandos de C01. Además, DP-11 dejó pendiente para este incremento la retención, el borrado y el responsable de los respaldos. Un build o un conjunto de pruebas unitarias no demuestra por sí solo que el producto sea utilizable (definición de producto utilizable).

Resultado esperado: un recorrido integral reproducible con cuentas sintéticas y archivos reales, los controles negativos del recorrido, una copia de seguridad coherente de PostgreSQL y de los documentos (en Drive) que se restaura en un destino nuevo y aislado y se verifica, una guía de uso y operación con comandos probados y la validación de lo que quedó pendiente en los incrementos anteriores (teclado, tema oscuro y vista móvil en navegador). El resultado declara con claridad qué se probó con servicios reales locales y qué no (Drive, móvil físico, hospedaje).

## Fuentes y alcance

- US/RN/AC: [definición de producto utilizable](../../docs/analysis/ESPECIFICACION_FUNCIONAL.md), [RN-25 y RN-29](../../docs/analysis/REGLAS_DE_NEGOCIO.md), [AC-24 y la trazabilidad AC-01 a AC-23](../../docs/analysis/CRITERIOS_DE_ACEPTACION.md).
- Documentos enlazados: [plan maestro](../../docs/construction/PLAN_MAESTRO.md), [validación y operación local](../../docs/construction/VALIDACION_Y_OPERACION_LOCAL.md), [DP-11](../../docs/analysis/DECISIONES_PENDIENTES.md), [estado y brechas](../../docs/analysis/ESTADO_ACTUAL_Y_BRECHAS.md), [ADR-08 y ADR-09](../../docs/analysis/DECISIONES_DE_ARQUITECTURA.md), [modelo de datos](../../docs/analysis/MODELO_DE_DATOS.md), [contrato de archivos](../../docs/analysis/CONTRATO_DE_ARCHIVOS_E_IMPORTACIONES.md), [C01](../C01-base-local/spec.md), [C08B](../C08B-archivo-y-depuracion/spec.md), [C09](../C09-foro-buzon-y-plantillas/spec.md).

Incluye:

0. Primer paso, heredado de C10A (cerrada el 2026-10-17 sin prueba contra Drive real): con la cuenta de pruebas autorizada, ejecutar `scripts/smoke_c10a.py` parte B y los smokes C01 a C09 con `ALMACENAMIENTO=drive`, y registrar el resultado; cualquier defecto se corrige antes de seguir (consistencia lectura-tras-escritura, papelera, cuota, token).
1. Recorrido integral (`scripts/smoke_c10.py`) con HTTP, PostgreSQL y almacenamiento reales y cuentas sintéticas de coordinador, dos tutores y dos alumnos de grupos y períodos distintos: crear grupo y alumno; configurar empresa e inicio; registrar al alumno; ingresar al foro; descargar la plantilla; entregar dos semanas; rechazar una y reenviar; aprobar con firma; comprobar historia y expediente; cerrar la recepción con otra entrega pendiente; verificar el bloqueo y la aprobación posterior; finalizar y comprobar el promedio; abrir un segundo período y confirmar que el primero no cambia; descargar períodos anteriores; paquete y depuración con gracia.
2. Controles negativos del mismo recorrido: acceso cruzado entre los alumnos A y B (expediente, versiones, paquetes y buzón), el tutor intentando el cierre, un fallo inyectado del almacenamiento, un PDF corrupto, el envío duplicado concurrente y la conversación completa del buzón con el hilo cerrado.
3. Respaldo: un procedimiento y una orden que generan una copia coherente de PostgreSQL y de los documentos con un manifiesto (fecha, versión de las migraciones, conteos, SHA-256 de cada archivo de la copia). Conforme a la decisión del 2026-10-17 la copia se guarda en una subcarpeta de respaldos de Drive (con el contrato de almacenamiento de C10A) y no en el equipo; el volcado de la base pasa por un archivo temporal que se elimina al terminar; sin credenciales dentro de la copia.
4. Restauración (AC-24): una orden que restaura en un proyecto de Compose nuevo y aislado (base y puerto propios y una carpeta de Drive de prueba distinta, sin tocar la base ni la carpeta vivas), verifica el manifiesto, los conteos, las referencias (cada documento no archivado existe en la carpeta restaurada y coincide con su SHA-256; ninguna fila apunta a un archivo ausente), descarga una muestra de originales y firmados por la API restaurada y vuelve a aplicar el registro de depuraciones de C08B (los archivos de documentos marcados como archivados que reaparezcan por haber sido restaurados se eliminan de nuevo).
5. Guía de uso y operación en español: instalación desde cero, cuentas iniciales, operación diaria por rol, respaldo y restauración, qué hacer si falla un servicio, límites conocidos y qué no se validó. Se actualiza `VALIDACION_Y_OPERACION_LOCAL.md` con comandos probados y resultados reales y se corrige el resto de la documentación que contradiga el código.
6. Validación de lo pendiente de los incrementos anteriores en el navegador: teclado completo, tema oscuro y vista móvil emulada de las pantallas principales de cada rol; el móvil físico sigue NO_VERIFICADA.
7. Conciliación final: tabla de trazabilidad AC-01 a AC-24 con la evidencia de cada incremento y lo que queda sin verificar; contratos, fixtures y documentación coherentes con el código.

Excluye: nuevas funciones del producto (el almacenamiento en Drive es de C10A); otros proveedores externos; publicación u hospedaje y su selección (se investiga aparte con límites actuales y consentimiento de publicación); automatización del despliegue y de los respaldos programados (ADR-08, salvo lo que decida D1); notificaciones por correo; migración de datos de la demo (ADR-09: base nueva); móvil físico.

## Decisiones

Confirmadas (incluida la decisión del responsable del 2026-10-17: archivos y respaldos en Drive, nada local, base de datos en Docker en el equipo y correo de la universidad solo para usuarios de prueba): la base es nueva y sin limpieza histórica de la demo (RN-29, ADR-09); la validación usa datos sintéticos y no declara recuperada una producción que no se probó (guía de operación); Drive se declara validado solo con la cuenta de prueba realmente utilizada en C10A y C10; un respaldo no se declara recuperable sin restauración probada; las credenciales se guardan aparte de los respaldos compartibles; la depuración de C08B no alcanza copias de seguridad y esta spec define cómo se tratan al restaurar.

Resuelta el 2026-10-17:

- D2: almacenamiento del piloto = Drive (C10A); destino de los respaldos = Drive. El criterio de salida de C10 es «validado con la base en Docker local y los archivos en Drive con datos sintéticos», no «listo para publicar».

D1 (DP-11), resuelta por el responsable el 2026-10-17, tal como se recomendó:

- Responsable de los respaldos: el propio responsable del proyecto.
- Frecuencia: una copia semanal y otra antes de cada finalización de período o depuración de archivos.
- Retención: 8 copias semanales y 4 mensuales.
- Prueba de restauración: una por trimestre, en un destino aislado.
- Destino: Drive (C10A). La guía de operación debe registrar estas reglas, quién ejecuta cada paso y dónde se anota el resultado de cada prueba de restauración. La automatización de los respaldos programados sigue fuera de alcance (ADR-08): se ejecutan con la orden del procedimiento.

Propuestas técnicas (sujetas a esas decisiones):

- Coherencia del respaldo: `pg_dump` en formato personalizado entrega una instantánea consistente de la base aunque haya uso, pero no cubre los archivos; como los documentos son de solo escritura (clave nueva, nunca se sobrescriben) y la depuración solo elimina, se copia primero la base y después los documentos: la copia de archivos es un superconjunto de lo que la base referencia y los archivos sin fila son huérfanos inofensivos; el manifiesto registra ambos instantes. Un archivo que la base referencia y que no está en la copia (eliminado por una depuración entre los dos pasos) corresponde a una fila archivada o se informa como error del respaldo.
- Restauración aislada: proyecto de Compose con otro nombre (`docker compose -p c10-restauracion`), volúmenes nuevos, base nueva con el mismo script de instalación y los mismos puertos desplazados; nunca se restaura sobre la base viva. Se verifica con `pg_restore --list` y conteos antes de aceptar, y después con consultas de integridad y descargas reales.
- Documentos depurados tras restaurar: se vuelve a aplicar el registro de purgas completadas (sin intervención) para que un respaldo anterior a una depuración no devuelva archivos que ya se habían eliminado a propósito, y las purgas programadas siguen su plazo; no hay ninguna garantía sobre copias antiguas ya entregadas a terceros, y esa limitación se documenta.
- El recorrido integral reutiliza los ayudantes de los smokes existentes (`smoke_periodos`, entregas, firma) en un solo guion y no sustituye a los smokes por incremento, que quedan como regresión.
- Teclado y tema oscuro: recorrido con Tab, Intro y Escape de las pantallas principales (acceso, foro, reportes, revisión, expediente, plantilla, diálogos) y lectura de contraste en el tema oscuro, con anchos de 375 y 768 px emulados.

### Referencias de buenas prácticas consultadas

Consultadas el 2026-10-17 (guías de terceros y de productos, no normas; criterio de diseño, no requisito):

- [Cómo probar la restauración de un respaldo de PostgreSQL](https://oneuptime.com/blog/post/2026-01-21-postgresql-backup-testing/view) y [pg_dump](https://oneuptime.com/blog/post/2026-01-21-postgresql-pg-dump-backup/view): un respaldo solo vale si se restaura; restaurar a una base nueva, ejecutar consultas de la aplicación y descartarla; `pg_dump` da una instantánea consistente de la base pero no de los archivos. La búsqueda no devolvió cómo emparejar el volcado con el almacén de archivos: se resuelve aquí con el orden base → archivos sobre documentos de solo escritura.
- [Regla 3-2-1 y pruebas de restauración (guía para pequeñas organizaciones)](https://beancount.io/blog/2026/09/24/3-2-1-backup-rule-small-business-ransomware-restore-tests-guide), [qué es 3-2-1-1-0 (AvePoint)](https://www.avepoint.com/blog/backup/what-is-the-3-2-1-backup-rule): tres copias, dos medios, una fuera del sitio, y verificar legibilidad y sumas de control; guardar las credenciales de respaldo aparte; probar la restauración cada cierto tiempo (mensual o trimestral según el caso). Son guías de proveedores, no una norma.
- [Datos eliminados que reaparecen al restaurar (GDPR y respaldos)](https://www.datasanitization.org/gdpr-and-backups-can-ghosts-of-data-past-rise-from-the-grave/) y [cómo tratar las solicitudes de eliminación en respaldos](https://www.probackup.io/blog/gdpr-and-backups-how-to-handle-deletion-requests): al restaurar un respaldo anterior a una eliminación vuelven los datos eliminados, y la práctica citada es volver a aplicar la eliminación sobre la copia restaurada. No hay un estándar que prescriba el método; aquí se aplica el registro de purgas como propuesta y se documenta la limitación.

## Contratos y cambios

Propuesta mínima, a concretar al aprobar las decisiones:

- Scripts: `scripts/smoke_c10.py` (recorrido y negativos), `scripts/respaldo_local` y `scripts/restaurar_local` (PowerShell o Python según la plataforma del piloto), un verificador de integridad de la restauración y, si hace falta, una ruta de lectura solo del personal que no existe hoy (se evita: la verificación usa SQL y las rutas existentes).
- Documentación: guía de uso y operación nueva, `VALIDACION_Y_OPERACION_LOCAL.md` actualizada con resultados reales, trazabilidad AC-01 a AC-24 y la limpieza de contratos y estados desactualizados (por ejemplo encabezados de incrementos ya cerrados).
- Sin cambios de esquema ni de contrato API previstos; cualquier defecto que el recorrido encuentre se corrige en una spec de corrección explícita, no dentro de C10.

Permisos y estados: el respaldo y la restauración los ejecuta el responsable de D1 con acceso a la máquina; no son rutas de la API.

## Verificación

| AC | Prueba o recorrido | Nivel y datos | Resultado |
|---|---|---|---|
| C10-AC1 | Recorrido integral completo con tres roles y dos alumnos en períodos distintos: cada paso produce el estado esperado y el primer período no cambia al abrir el segundo | HTTP + PostgreSQL + almacenamiento reales con cuentas sintéticas | NO_VERIFICADA |
| C10-AC2 | Controles negativos: acceso cruzado A/B, tutor intenta el cierre, fallo de almacenamiento inyectado, PDF corrupto, envío duplicado concurrente, buzón con hilo cerrado | Negativos HTTP reales | NO_VERIFICADA |
| C10-AC3 / AC-24 | Respaldo coherente y restauración en un destino nuevo y aislado: manifiesto, conteos, referencias, hashes y descargas reales de originales y firmados; la base y la carpeta de Drive vivas no se modifican y no queda nada persistente en disco | PostgreSQL local y Drive reales en un proyecto de Compose y una carpeta de prueba aparte | NO_VERIFICADA |
| C10-AC4 | Tras restaurar un respaldo anterior a una depuración, los archivos de documentos archivados vuelven a eliminarse y las notas, promedios e historial coinciden con la base viva | PostgreSQL y almacenamiento reales | NO_VERIFICADA |
| C10-AC5 | Un respaldo incompleto o alterado (archivo faltante, hash distinto, volcado dañado) se detecta y la restauración se rechaza con un motivo | Fallos inyectados reales | NO_VERIFICADA |
| C10-AC6 | La guía se sigue desde cero en un entorno nuevo (instalar, crear el coordinador, operar un ciclo, respaldar y restaurar) sin pasos implícitos | Ejecución real de la guía | NO_VERIFICADA |
| C10-AC7 | Teclado completo, tema oscuro y vista móvil emulada de las pantallas principales de cada rol | Preview del build desplegado | NO_VERIFICADA |
| C10-AC8 | Trazabilidad AC-01 a AC-24 con la evidencia de cada incremento y las lagunas declaradas; contratos y documentación coherentes con el código | Revisión documental con comprobaciones automáticas de contratos | NO_VERIFICADA |

## Evidencia de implementación

Sin ejecución: spec en DRAFT. Añadir solo después de implementar, con fecha, entorno, revisión del código y clase REAL/SIMULADA/NO_VERIFICADA.

## Revisión

Veredicto: pendiente.
Revisor y modalidad: pendiente.
Hallazgos materiales: no aplica antes de implementación.
Correcciones y verificación focal: no aplica.
Limitaciones previstas: validación solo con datos sintéticos, con la base en la máquina local y los archivos en Drive con una cuenta de prueba; el apagado del equipo interrumpe el servicio (sin garantía de disponibilidad) y la disponibilidad de archivos depende de Drive y del token de la cuenta; móvil físico, otros proveedores y el hospedaje quedan NO_VERIFICADOS; una restauración de datos sintéticos no demuestra la recuperación de una producción; las copias antiguas ya entregadas a terceros no se pueden recuperar.

## Aprobaciones y cierre

D1 y D2 resueltas el 2026-10-17 (D1 tal como se recomendó). Pendiente: C10A DONE y la orden de pasar a READY.
