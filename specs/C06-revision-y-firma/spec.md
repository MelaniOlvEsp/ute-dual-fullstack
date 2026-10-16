# C06 — Revisión y firma

Estado: READY
Fecha: 2026-10-15
Responsable de aprobación: responsable del proyecto
Dependencias: C05 DONE (2026-10-15). DP-08 resuelta; DP-02 y DP-07 resueltas el 2026-10-16 (ver Decisiones). Sin decisiones bloqueantes pendientes: DRAFT → READY el 2026-10-16.

## Problema y resultado esperado

La revisión actual es heredada de la demo: `PATCH /dual/coordinador/reportes/{id}` (permiso de tutor pese al nombre) cambia el estado de la fila del reporte sin saber qué versión se revisa, sin comprobar el estado actual ni bloquear contra un reenvío simultáneo, sobrescribe fecha y nota sin conservar el valor previo (acepta decimales), no exige observación al rechazar y, al aprobar, firma el PDF y lo sube a Drive; si Drive no está disponible la aprobación falla, y el firmado reemplaza al original en el puntero del reporte. La firma agrega una hoja al final sin muestra visual validada.

Resultado esperado: el tutor (todas las carreras) abre la versión vigente con el PDF y los datos declarados lado a lado; corrige fechas y nota con trazabilidad (previo, nuevo, autor, instante); rechaza con observación obligatoria o aprueba con su firma; la decisión recae sobre una versión concreta y se rechaza si ya hay una más nueva; el original y el firmado son documentos distintos y ambos se conservan; una aprobación nunca queda a medias; el alumno ve la decisión, la observación y descarga el firmado propio; ningún cambio mueve la obligación ni el período en silencio.

## Fuentes y alcance

- US: [US-08](../../docs/analysis/ESPECIFICACION_FUNCIONAL.md).
- RN: [RN-14, RN-15, RN-16 y RN-17](../../docs/analysis/REGLAS_DE_NEGOCIO.md); RN-18/RN-19 solo en que la revisión continúa tras el cierre de recepción.
- AC: [AC-12 y AC-13](../../docs/analysis/CRITERIOS_DE_ACEPTACION.md).
- Documentos enlazados: [plan maestro](../../docs/construction/PLAN_MAESTRO.md), [modelo de datos](../../docs/analysis/MODELO_DE_DATOS.md), [archivos e importaciones](../../docs/analysis/CONTRATO_DE_ARCHIVOS_E_IMPORTACIONES.md), [contrato API](../../docs/analysis/CONTRATO_API.md), [UX](../../docs/analysis/UX_Y_FLUJOS.md), [roles (MP-08, MP-09, MP-10)](../../docs/analysis/MATRIZ_DE_ROLES_Y_PERMISOS.md), [DP-02, DP-07 y DP-08](../../docs/analysis/DECISIONES_PENDIENTES.md), [C05](../C05-entregas-y-versiones/spec.md).

Incluye:

1. Revisión por versión: el tutor decide sobre la versión vigente de un reporte (número explícito en la solicitud); si ya existe una más nueva, 409 sin cambios. Una versión recibe una sola decisión (el disparador de C05 ya lo impide en base).
2. Corrección de fechas y nota por el tutor con trazabilidad (valor previo y nuevo, autor, instante), nota entera 1–10 y fechas con inicio ≤ fin; los datos declarados por el alumno en la versión no se modifican.
3. Rechazo con observación obligatoria; el reenvío de C05 sigue siendo la única vía de corrección del alumno.
4. Aprobación con firma: el firmado es un documento derivado nuevo en `documentos`, ligado a la versión aprobada; el original se conserva. Flujo en dos fases: generar el firmado, guardarlo y, en una sola transacción, registrar documento y decisión; si algo falla no queda aprobada ni archivo huérfano referenciado.
5. Almacenamiento local privado para el firmado (DP-08); Drive deja de ser requisito de la aprobación y queda como adaptador opcional NO_VERIFICADO.
6. Estampado de la firma en la celda "Firma" de la fila "Tutor académico" del reporte (DP-07), validado con una muestra sintética aceptada por el responsable y revisión visual del PDF resultante en todas sus páginas.
7. Bandeja y detalle de revisión del tutor: filtros por período, carrera, grupo, estado y alumno; PDF y datos lado a lado; versión revisada visible; evitar decidir sobre una versión obsoleta (UX).
8. Vista del alumno: decisión y observación por versión, descarga del firmado de una versión aprobada propia.
9. Retiro de la ruta heredada de revisión; contratos, cliente, fixtures, migración aditiva sobre C05, documentación, pruebas y preview.

Excluye: cierre de recepción, finalización y promedio (C07); expediente e historial integral y visor (C08); plantillas (C09); reapertura o rectificación posterior a la aprobación (DP-10, no solicitada en V1); validación de la firma de la empresa u OCR; gestión de la firma del tutor (ya existe, MP-09); integración real con Drive.

## Decisiones

Confirmadas (documentos vigentes): el tutor revisa todas las carreras (MP-08); el coordinador no revisa; rechazo exige nota explicativa; el reenvío conserva archivo, datos y decisiones anteriores; la corrección conserva valor previo, nuevo, autor e instante; aprobar incorpora la firma del tutor, conserva original y firmado y no se completa si falla el guardado; después de aprobar el alumno no reemplaza ni se rectifica en V1; las fechas declaradas nunca reasignan semana ni período (DP-01, DP-12); la revisión continúa tras el cierre de recepción; el tutor propietario administra su firma (MP-09).

Propuestas técnicas incluidas para la futura aprobación de implementación:

- Modelo aditivo: tabla `revisiones` (versión única, tutor, decisión, observación, fechas y nota validadas, instante, documento firmado opcional) y `reporte_correcciones` (revisión, campo, previo, nuevo); `documentos` gana el tipo `firmado`. La decisión se refleja en `reporte_versiones` (campos ya creados en C05) y en las columnas heredadas de `reportes_dual` mientras C07/C08 migran la lectura.
- Ruta nueva por versión (por ejemplo `POST …/reportes/{reporte_id}/versiones/{numero}/revision`) para el tutor; detalle con versión vigente y correcciones; descarga del firmado para tutor, coordinador (MP-10) y alumno propio. Se retira `PATCH /dual/coordinador/reportes/{id}`.
- Bloqueo por obligación con la misma clave de C05 y `FOR UPDATE` del reporte: revisión y reenvío simultáneos se serializan; gana el primero y el segundo recibe 409.
- El firmado se genera sobre el original sin alterarlo (estampado en la celda de firma del tutor según DP-07, con la hoja adicional solo como respaldo), se valida con el motor PDF antes de confirmar y se almacena con clave del servidor y SHA-256.
- Tratar de aprobar sin firma cargada o con una versión ya decidida responde 409 sin cambios.

Resueltas por el responsable del proyecto el 2026-10-16 (registradas en [DECISIONES_PENDIENTES](../../docs/analysis/DECISIONES_PENDIENTES.md)):

1. **DP-02 — corrección y período/semana:** la corrección de fechas o nota nunca mueve la obligación ni el período. Si el alumno entregó en la semana equivocada, el tutor rechaza con observación y el alumno entrega en la obligación correcta. No hay movimiento posible hacia un período cerrado, y AC-12 se cumple por construcción.
2. **DP-07 — ubicación de la firma:** tras revisar un reporte de ejemplo, la firma se estampa en el espacio existente: la celda vacía de la columna "Firma" en la fila "Tutor académico" de la tabla final (en el ejemplo, unos 106×32 pt, x 329–435 y y 717–749 de la última hoja, con el reporte de una sola hoja). No se agrega hoja. El responsable acepta una muestra sintética del PDF firmado antes del cierre (C06-AC8). El ejemplo contiene datos de una persona real y no se copia al repositorio.

Propuestas técnicas derivadas de DP-07, adoptadas al pasar a READY el 2026-10-16 (el responsable ordenó el paso tras verlas; se pueden ajustar en la implementación si la muestra lo pide):

- Localizar la celda por anclaje en el texto de la última hoja con contenido de firmas: la fila cuyo texto es "Tutor académico", y la columna "Firma" por el encabezado de la tabla; el rectángulo se toma de las líneas dibujadas de la celda, de modo que funcione aunque el reporte tenga varias hojas (el formato admite evidencias).
- Escalar la imagen de la firma conservando su proporción dentro de la celda con un margen, sin tapar texto ni líneas; no escribir texto adicional dentro de la tabla.
- Si no se encuentra la fila o la celda está ocupada (otro formato, PDF escaneado como imagen), la aprobación no se bloquea ni se estampa a ciegas: se usa como respaldo la hoja adicional actual y se registra en la revisión que se usó el respaldo.
- La muestra de aceptación se genera con datos y firma sintéticos sobre una réplica del formato.

No bloquean: DP-06, DP-09 a DP-11. Si durante la implementación aparece una decisión nueva que cambie permisos, notas o conservación, se detiene solo esa conducta y se presenta la decisión concreta.

## Contratos y cambios

Métodos/rutas/DTO y compatibilidad: revisión por versión (tutor), detalle de revisión, descarga del firmado y consulta de decisiones del alumno; retiro de la ruta heredada de revisión; cliente, contrato estático (`route_contract.json`), OpenAPI y fixtures actualizados juntos. `GET /dual/coordinador/reportes` se alinea con la versión vigente.

Datos, restricciones y conservación: migración `006_revisiones.sql`, aditiva e idempotente sobre C05; sin borrar ni sobrescribir originales ni firmados anteriores; correcciones y decisiones inmutables; FK por identificador sin cascadas. Base nueva de pruebas.

Permisos y estados: tutor revisa, corrige, aprueba y rechaza en todas las carreras; coordinador no revisa y consulta aprobados (MP-10); alumno solo ve lo propio. Estados de revisión: pendiente, rechazado y aprobado; la versión no se reabre.

Archivos/módulos previstos (se fijan al pasar a READY tras inspeccionar el diff base): `database/migrations/006_revisiones.sql` e `init-db.sh`; casos de uso `app/application/use_cases/dual/revisiones.py` y retiro de `revisar_reporte`; `app/infrastructure/documents/signatures.py` y `dual_reports.py`; consultas, routers, DTO; frontend de revisión del tutor y vista del alumno; pruebas (`test_c06_revision.py`, contrato) y documentación.

Comportamiento ante fallos/reintentos: aprobar es transaccional y nunca deja una aprobación sin firmado; un reintento idéntico de la misma decisión no duplica revisión; dos tutores simultáneos sobre la misma versión producen una decisión y un 409; un fallo de guardado del firmado conserva el reporte pendiente y el original.

## Verificación

| AC | Prueba o recorrido | Nivel y datos | Resultado |
|---|---|---|---|
| C06-AC1 / AC-12 | Tutor corrige fechas y nota: se conservan previo, nuevo, autor e instante; nota 0, 11, 8.5 e inicio > fin rechazadas; los datos declarados de la versión no cambian | HTTP + PostgreSQL reales | NO_VERIFICADA |
| C06-AC2 / AC-12, RN-15 | La corrección no mueve obligación ni período (DP-02); con recepción cerrada la revisión sigue permitida | HTTP + PostgreSQL reales | NO_VERIFICADA |
| C06-AC3 / RN-14 | Rechazo sin observación 422; con observación, el alumno la ve y reenvía como versión nueva; decisión sobre versión obsoleta 409 | HTTP + PostgreSQL reales | NO_VERIFICADA |
| C06-AC4 / AC-13, RN-16 | Aprobar con firma: original y firmado legibles, ambos conservados y descargables; hash del original intacto | HTTP + PostgreSQL + almacenamiento reales | NO_VERIFICADA |
| C06-AC5 / AC-13 | Fallo inyectado al firmar o guardar: el reporte no queda aprobado, sin archivo referenciado a medias | Fallos inyectados + verificación real | NO_VERIFICADA |
| C06-AC6 | Revisión y reenvío simultáneos, dos tutores simultáneos: una decisión, un 409, sin duplicados | HTTP + PostgreSQL con concurrencia | NO_VERIFICADA |
| C06-AC7 / MP-08, MP-10 | Alumno y coordinador no revisan (403); alumno solo ve y descarga lo propio (404 ajeno); tutor de otra carrera sí revisa; aprobar sin firma cargada 409 | Negativos HTTP reales | NO_VERIFICADA |
| C06-AC8 / DP-07 | Muestra sintética del PDF firmado revisada visualmente en todas sus páginas y aceptada por el responsable | Revisión visual del PDF | NO_VERIFICADA |
| C06-AC9 | Bandeja y detalle del tutor y vista del alumno en escritorio y móvil con teclado | Preview visual del build desplegado | NO_VERIFICADA |

## Evidencia de implementación

Sin ejecución: spec en DRAFT. Añadir solo después de implementar, con fecha, entorno, revisión del código y clase REAL/SIMULADA/NO_VERIFICADA.

## Revisión

Veredicto: pendiente.
Revisor y modalidad: pendiente.
Hallazgos materiales: no aplica antes de implementación.
Correcciones y verificación focal: no aplica.
Limitaciones: Drive y cualquier proveedor externo quedan NO_VERIFICADOS salvo que se usen; no hay validación de la firma de la empresa ni OCR; la firma aplicada es una representación gráfica, no una firma criptográfica; cierre y promedio son de C07.

## Aprobaciones y cierre

Aprobación de READY: el responsable resolvió DP-02 (la corrección nunca mueve período ni semana) y DP-07 (firma en la celda "Firma" de la fila "Tutor académico") el 2026-10-16 y ordenó pasar C06 a READY sin implementarla.
Aprobación de implementación: pendiente.
Aprobación de cierre: pendiente.
Resumen final: pendiente.
Siguiente spec: C07 solo después de implementar, revisar y cerrar C06.
Commit/push: no autorizados salvo indicación explícita.
