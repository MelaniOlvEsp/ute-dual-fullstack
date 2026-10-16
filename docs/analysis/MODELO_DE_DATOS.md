# Modelo de datos objetivo

Estado: PROPUESTA técnica. Fuente funcional: RN-01 a RN-29. No ejecutar este documento como migración. Esquema físico, índices y nombres definitivos se concretan en specs. Base inicial vacía.

## Separaciones esenciales

- Período calendario tiene ID y fechas; grado académico es un número del grupo.
- Incorporación laboral puede cruzar períodos; no crear una empresa/asignación nueva solo por cambiar cuatrimestre.
- Pertenencia a grupo tiene historia por período.
- Obligación semanal existe aunque el alumno no entregue.
- Reporte lógico tiene versiones; documento original y firmado son objetos distintos.
- Recepción y evaluación tienen estados diferentes.

## Entidades propuestas

| Entidad | Datos y relaciones mínimos | Invariantes |
|---|---|---|
| usuarios | ID, correo, hash, rol, matrícula opcional, activo, versión de credenciales | Correo normalizado único; alumno vinculado a matrícula; tres roles, nunca privilegio por nombre de ruta. |
| alumnos | Matrícula, nombre, autorización de registro | Matrícula única; historial no se borra por baja Dual. |
| carreras | Código estable, nombre visible, activo | Catálogo cerrado exclusivamente a TIC, Logística y Mercadotecnia; conservar literalmente códigos y nombres de la base institucional. No admitir Educación ni otras carreras. |
| grupos | ID, carrera, grado académico, componentes nomenclatura, cohorte | Nomenclatura institucional existente; no rediseñarla ni usar su etiqueta como FK. |
| periodos | ID, año, bloque, fechas, recepción, evaluación, autores/instantes de cambios | Bloque único por año; fin calendario no cambia por cierre anticipado. C04: fechas sin solapamiento (restricción de exclusión sobre `daterange` en `ciclos_dual`) y apertura manual en America/Mexico_City. C07: la recepción es `abierto`/`cerrado` con `cerrado_por` y `cerrado_at`, la evaluación añade `evaluacion_finalizada_en` y `evaluacion_finalizada_por` (CHECK: solo tras cerrar la recepción), un período finalizado no cambia ni se reabre (disparador) y no admite versiones ni revisiones nuevas. |
| alumno_grupo_periodo | Alumno, grupo, período | Un grupo vigente por alumno/período, con cambios auditados; no reescribir períodos anteriores. |
| empresas | ID, nombre, activo | Mantener referencias históricas. |
| incorporaciones_dual | Alumno, empresa, inicio, baja opcional | Inicio ≤ baja; continuidad entre períodos; política de cambio de empresa en spec. |
| obligaciones_semanales | ID, incorporación, inicio/fin calendario, período resuelto | Una obligación por intervalo; generación idempotente; regla de pertenencia DP-01. Implementada en C04 (`004_obligaciones.sql`): `UNIQUE (incorporacion_id, semana_inicio)`, lunes–domingo por CHECK, fechas efectivas dentro de la semana, período nulo si ningún período contiene el domingo; las semanas posteriores a la baja se excluyen de las lecturas y no se borran. |
| reportes | ID, obligación, versión vigente, estado | Un reporte lógico por obligación; no creado para simular entrega inexistente. Implementado en C05 sobre `reportes_dual` con `obligacion_id` único (nulo solo en filas heredadas); la versión vigente es la de mayor número y sus datos se reflejan en las columnas heredadas mientras C06 migra la revisión; sin techo de 18 semanas ni unicidad textual por semana. |
| reporte_versiones | Reporte, número, fechas declaradas, nota declarada, archivo original, recepción | Número único por reporte; versiones recibidas inmutables. Implementado en C05 (`005_entregas.sql`): nota `smallint` con CHECK 1–10, inicio ≤ fin, documento por FK, autor e instante de recepción y, al reenviar, la decisión anterior copiada a la versión que la recibió; un disparador impide modificar o borrar lo recibido. |
| revisiones | Versión, tutor, decisión, nota, fechas/nota validadas, instante, archivo firmado | Rechazo con motivo; historial de correcciones; aprobación con firmado disponible. Implementado en C06 (`006_revisiones.sql`): una revisión por versión (`version_id` único), CHECK de observación obligatoria al rechazar y de documento firmado solo si se aprueba, nota `smallint` 1–10, inicio ≤ fin; `reporte_correcciones` guarda campo, valor previo y nuevo (único por revisión y campo); disparadores impiden modificar o borrar ambas tablas. La decisión se copia a `reporte_versiones` y a las columnas heredadas de `reportes_dual` (con los valores validados y, al aprobar, la ruta del firmado). |
| documentos | ID, proveedor, clave privada, tipo, tamaño, hash, estado | Sin URL pública como identidad; original conservado; metadatos no incluyen tokens. Implementado en C05: clave `<uuid>.pdf` generada por el servidor (CHECK de formato), tamaño 1 byte a 10 MB, SHA-256 y páginas; almacenamiento local privado, sin proveedor (Drive queda NO_VERIFICADO). C06 agrega `rol` (`original` o `firmado`) y `firma_modo` (`celda` u `hoja_adicional`, solo para firmados); el firmado puede llegar a 20 MB, el original conserva 10 MB. |
| firmas_tutor | Tutor, documento/imagen y versión | Solo propietario administra; aprobado conserva artefacto firmado histórico. |
| cierres_alumno_periodo | Alumno, período, suma, cantidad, promedio, cierre | Resultado final reproducible; sin aprobados promedio nulo; snapshot auditado. Implementado en C07 (`007_cierre.sql`): una fila por alumno y período (único), suma y cantidad enteras exactas, promedio `numeric(4,2)` con HALF_UP (nulo si no hay aprobados, CHECK), autor e instante; `cierre_alumno_notas` guarda los reportes y notas que lo componen; disparadores impiden modificar o borrar ambas tablas. |
| versiones_plantilla | ID, Word, PDF, fecha, autor, vigente | Pareja completa publicada atómicamente; versiones anteriores no alteran entregas. |
| foro_publicaciones/reacciones | Autor, contenido/fecha; reacción por usuario | Mantener permisos existentes hasta decidir moderación. |
| buzon_mensajes/respuestas | Alumno propietario, asunto, estado, respuestas con autor/fecha | Lectura y respuesta solo propietario/personal; no filtrar datos entre alumnos. |
| eventos_auditoria | Actor, acción, recurso, instante, cambios pertinentes | Trazabilidad mínima, sin credenciales ni copia indiscriminada de documentos. |

No es obligación crear una tabla por cada nombre: la spec puede combinar elementos cuando conserve las invariantes y simplifique el sistema.

## Relaciones

Alumno → pertenencias por período → grupo/carrera.
Alumno → incorporaciones → obligaciones → reporte → versiones → revisiones/documentos.
Período → obligaciones y cierres de calificación.
Usuario tutor → revisiones/firmas; usuario coordinador → cierres/plantillas.
Alumno → conversaciones → respuestas.

## Integridad y concurrencia

FK por identificador; no unir por cuatrimestre textual. Nota entera con CHECK 1–10. Fechas de documento ordenadas. Unicidad de obligación y versión. No cascadas que borren expediente por desactivar alumno/tutor.

Generación de semanas y reintentos no duplican obligaciones. Cierre bloquea recepción con validación transaccional; revisión y finalización coordinan bloqueo/versionado. Índices iniciales en FK y búsquedas por período/estado/alumno; medir antes de agregar índices de rendimiento.

Almacenamiento y PostgreSQL no comparten transacción: documento pasa por preparación/confirmación y limpieza de huérfanos por referencia. Nunca borrar original válido por un fallo de reenvío o firma.

## Calendario y historia

Guardar límites calendario y fechas declaradas separados. Una modificación de datos del PDF no debe cambiar inadvertidamente la identidad semanal. DP-01/02 determinan cuándo se permite cambiar período.

No codificar techo universal de 18 semanas de incorporación: una estancia puede durar varios períodos. El ordinal visible puede reiniciarse por período o continuar, pero las fechas e ID son la identidad; fijarlo en C04.

## Diferencia respecto de database/

Los scripts actuales optimizan compatibilidad con una demo: roles JSONB, cuatrimestre textual, un reporte por semana sin versiones. C01 puede conservar JSONB para no refactorizar identidad innecesariamente; C03–C07 incorporan el modelo aprobado de forma incremental. No se necesita backfill de datos reales.
