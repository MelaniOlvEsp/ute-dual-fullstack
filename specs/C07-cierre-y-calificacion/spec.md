# C07 — Cierre y calificación

Estado: DRAFT
Fecha: 2026-10-16
Responsable de aprobación: responsable del proyecto
Dependencias: C06 DONE (2026-10-16). DP-04, DP-03 y DP-11 resueltas por el responsable el 2026-10-16 en lo que C07 necesita (ver Decisiones). Sin decisiones bloqueantes pendientes; falta la orden de pasar a READY.

## Problema y resultado esperado

Hoy `POST /dual/tutor/cierre` cierra el único período abierto, sin identificarlo por ID, y además le reescribe `periodo_label` con lo que llegue en la solicitud, de modo que elegir mal en el formulario renombra el período. "Abierto/cerrado" mezcla recepción con calendario y no existe la evaluación: no hay forma de finalizar un período, no hay promedio por período con regla única (el directorio lo calcula con `ROUND(AVG(...))` sobre el grado como período y sobre todos los aprobados) ni resultado congelado. La entrega ya consulta si el período está abierto (C05), pero lee el estado sin bloquearlo: una entrega que llega mientras el coordinador cierra puede aceptarse después del cierre. Las semanas que el alumno no pudo entregar porque el cierre fue anticipado se ven igual que un atraso real.

Resultado esperado: el coordinador cierra la recepción de un período identificado por ID, con confirmación y consecuencia explícita; desde ese instante nadie entrega ni reenvía en él, pero el tutor sigue revisando lo recibido. Cuando no quedan reportes pendientes de revisión, el coordinador finaliza la evaluación: el sistema calcula el promedio de cada alumno con la regla única (suma de notas vigentes aprobadas entre la cantidad de aprobados, dos decimales; sin aprobados, "Sin calificación"), lo congela en un registro propio y auditado y ya no cambia. Mientras tanto el promedio es provisional. Cerrar o finalizar un período no modifica el período que recibe entregas ni reasigna semanas.

## Fuentes y alcance

- US: [US-11 y US-12](../../docs/analysis/ESPECIFICACION_FUNCIONAL.md).
- RN: [RN-18, RN-19, RN-20, RN-21, RN-22, RN-23 y RN-24](../../docs/analysis/REGLAS_DE_NEGOCIO.md).
- AC: [AC-14, AC-15, AC-16, AC-17 y AC-18](../../docs/analysis/CRITERIOS_DE_ACEPTACION.md).
- Documentos enlazados: [plan maestro](../../docs/construction/PLAN_MAESTRO.md), [modelo de datos](../../docs/analysis/MODELO_DE_DATOS.md), [contrato API](../../docs/analysis/CONTRATO_API.md), [UX (coordinador: cierre)](../../docs/analysis/UX_Y_FLUJOS.md), [roles (MP-11, MP-18)](../../docs/analysis/MATRIZ_DE_ROLES_Y_PERMISOS.md), [DP-03, DP-04, DP-10 y DP-11](../../docs/analysis/DECISIONES_PENDIENTES.md), [C04](../C04-calendario-y-pendientes/spec.md), [C06](../C06-revision-y-firma/spec.md).

Incluye:

1. Cierre manual de recepción por período (solo coordinador, MP-11): por ID del período y confirmación; idempotente; registra autor e instante; no cambia las fechas calendario ni el nombre del período; no cierra automáticamente ni por margen de días (RN-18). Reemplaza a `POST /dual/tutor/cierre` (que identifica por texto y renombra).
2. Efecto del cierre (RN-19): entregas y reenvíos del período se rechazan (409) incluso si compiten con el cierre; el tutor sigue revisando y aprobando lo recibido; los rechazados no pueden reenviarse y la pantalla lo informa antes de confirmar. No se trasladan reportes ni semanas futuras al período siguiente.
3. Recepción y evaluación independientes del calendario (RN-23): estado de recepción (abierta o cerrada) y de evaluación (en curso o finalizada) por período, con el instante efectivo de cierre mostrado aparte de las fechas calendario (RN-24). Se puede revisar un período anterior mientras otro recibe.
4. Finalización de la evaluación (solo coordinador): disponible con la recepción cerrada y cero reportes pendientes de revisión (RN-20); rechazados y no entregados no la impiden. En una sola transacción calcula y congela, por alumno con obligaciones en el período, suma, cantidad de aprobados y promedio con la regla de RN-21 y RN-22, con autor e instante. Irreversible en V1 (DP-10 no solicitada).
5. Promedio provisional y final: provisional calculado en vivo con reportes aprobados cuya obligación pertenece al período (no con el grado); final leído del registro congelado. Dos decimales; sin aprobados "Sin calificación", nunca 0.00; no entregados, rechazados y pendientes no entran al denominador. Se corrige la consulta del directorio que hoy promedia por grado.
6. Etiqueta de las semanas cortadas por un cierre anticipado (RN-24, según la decisión de DP-03 pendiente): distinguir "no recibida por cierre" de un atraso real, sin atribuirla automáticamente a incumplimiento ni recalificar al alumno.
7. Panel del coordinador por período (UX): fechas calendario, estados de recepción y evaluación, conteos de recibidos, pendientes de revisión, rechazados, aprobados y faltantes, y promedios provisionales o finales; acciones "Cerrar recepción" y "Finalizar evaluación" con la consecuencia y el período exacto en la confirmación. Avisos de estado para alumno y tutor.
8. Contratos, cliente, fixtures, migración aditiva sobre C06, documentación, pruebas y preview de los recorridos afectados.

Excluye: expediente integral, visor y descargas por período del alumno (C08); reapertura de recepción o rectificación posterior a finalizar (DP-10, no solicitada); plantillas (C09); retención, borrado y respaldos (DP-11, para C10); tratamiento especial de períodos vacacionales (DP-06); cambios de revisión o firma (C06).

## Decisiones

Confirmadas: solo el coordinador cierra la recepción y finaliza (MP-11); no hay cierre automático ni margen de siete días; el cierre permite revisar lo ya recibido y los rechazados no se reenvían; finalizar exige cero pendientes de revisión; el promedio es suma de notas vigentes aprobadas entre cantidad de aprobados, con dos decimales, provisional hasta finalizar y final después; sin aprobados "Sin calificación"; períodos manuales en America/Mexico_City sin solapamiento (DP-04 parcial); la nota vigente aprobada es la validada por el tutor (RN-15, C06); finalizar un período no modifica el que recibe ni reasigna semanas (AC-18); no hay reapertura ni rectificación posterior (DP-10 fuera de V1).

Propuestas técnicas incluidas para la futura aprobación de implementación (con las referencias de buenas prácticas de abajo):

- Modelo aditivo (`007_cierre.sql`): `ciclos_dual` conserva `abierto`/`cerrado`/`cerrado_por`/`cerrado_at` como estado de recepción y gana `evaluacion_finalizada_en` y `evaluacion_finalizada_por` con un CHECK que impide finalizar sin cierre; tabla `cierres_alumno_periodo` (período, matrícula, suma, cantidad, promedio `numeric(4,2)` nulo si cantidad es 0, instante y autor) más el detalle de los reportes y notas que la componen, como registro anexable y con disparador que impide modificarla o borrarla. Un disparador adicional impide registrar revisiones o versiones en un período finalizado como defensa en profundidad.
- Bloqueo coherente del período: cerrar y finalizar toman `FOR NO KEY UPDATE` sobre la fila del período; la entrega y el reenvío (C05) toman `FOR SHARE` sobre la misma fila antes de comprobar que está abierto. Así el resultado coincide con el orden transaccional (AC-15): o la entrega gana y entra antes del cierre, o el cierre gana y la entrega recibe 409.
- Promedio con `numeric`: suma entera, cantidad entera y `ROUND(suma::numeric / cantidad, 2)`; el redondeo de empates de `numeric` en PostgreSQL es hacia el valor mayor en módulo, que para notas positivas equivale a HALF_UP; no usar `float`. Calcular en una sola función compartida por el cálculo provisional y la finalización.
- Rutas por ID (se fijan al pasar a READY), por ejemplo `GET /periodos/{id}/resumen`, `POST /periodos/{id}/cierre-recepcion` y `POST /periodos/{id}/finalizacion`, con `get_coordinator`; se retira `POST /cierre` y se actualizan cliente y contrato estático en el mismo cambio. Reintento idéntico de cada acción: 200 sin duplicar efectos.
- Finalización por alumno: una fila por alumno con al menos una obligación del período, incluidos los de "Sin calificación".

### Referencias de buenas prácticas consultadas

- Odoo (código y documentación en GitHub): las fechas de bloqueo impiden crear o modificar asientos anteriores y permiten excepciones solo con permiso especial, y el módulo `account_lock_to_date` de OCA separa el bloqueo para usuarios comunes del de administradores ([documentación de Odoo](https://github.com/odoo/documentation/pull/15305/files), [OCA account_lock_to_date](https://pypi.org/project/odoo-addon-account-lock-to-date/16.0.1.0.0.1)). Aplicación: el cierre es un estado explícito con autor e instante y toda escritura lo comprueba; aquí no hay excepciones en V1.
- Moodle: bloquear calificaciones es solo una marca de protección sobre filas vivas, y la propuesta de congelar copiando los datos se descartó por requerir cambios de arquitectura; además al desbloquear se reportó que las calificaciones se sobrescribían desde otra tabla ([MDL-50522](https://tracker-old.moodle.org/browse/MDL-50522), [MDL-46291](https://tracker-old.moodle.org/browse/MDL-46291), [documentación de bloqueo](https://docs.moodle.org/503/en/Grade_locking)). Aplicación: el resultado final se guarda en una tabla propia, inmutable y con su detalle, no como una marca sobre filas que pueden cambiar.
- PostgreSQL: usar `FOR NO KEY UPDATE` en lugar de `FOR UPDATE` cuando no se cambia la clave, y que todo escritor tome el mismo bloqueo de fila o de aviso, porque un bloqueo en el que un escritor no participa no protege nada ([Cybertec](https://www.cybertec-postgresql.com/en/select-for-update-considered-harmful-postgresql/), [guía de bloqueos de fila](https://www.netdata.cloud/guides/postgres/postgres-row-level-lock-contention/)). Aplicación: el bloqueo del período descrito arriba, sin trabajo externo dentro de la transacción.
- PostgreSQL `ROUND`: con `numeric` los empates se redondean alejándose de cero (para notas positivas, HALF_UP), mientras que con coma flotante depende de la plataforma ([pgsql-docs](https://postgresql.org/message-id/3da3dcc06220f80537dc1fb2c32cb76c91f87b93.camel%40cybertec.at)). Aplicación: todo el cálculo en `numeric`.

Resueltas por el responsable del proyecto el 2026-10-16 (registradas en [DECISIONES_PENDIENTES](../../docs/analysis/DECISIONES_PENDIENTES.md)):

1. **DP-04 — recepción simultánea:** un solo período con recepción abierta a la vez (se mantiene el índice único actual). Se cierra la recepción de un período antes de abrir la del siguiente, y el anterior se puede revisar y finalizar mientras el nuevo recibe (RN-23, AC-18).
2. **DP-03 — etiqueta por cierre anticipado:** una semana sin entrega cuyo período se cerró antes de que terminara la semana se etiqueta «No recibida por cierre» (sin atraso ni incumplimiento); una semana que ya había terminado antes del cierre sigue como «Atrasada». Ninguna cuenta como cero ni entra al promedio.
3. **DP-11 — promedio:** solo aprobados y dos decimales; ningún valor se redondea a entero. La nota de cada reporte sigue siendo entera (RN-12), la suma y la cantidad de aprobados se guardan exactas y el promedio se calcula en `numeric` con redondeo HALF_UP en el tercer decimal (el responsable confirmó 9.335 → 9.34). Resultado congelado al finalizar en un registro inmutable y sin recálculo posterior. Retención, borrado y respaldos siguen para C10.

Pendientes bloqueantes (DP): ninguno.

No bloquean: DP-06, DP-09 y DP-10 (reapertura fuera de V1). Retención, borrado y responsable de respaldos de DP-11 se resuelven antes de uso real (C10). Si durante la implementación aparece una decisión nueva que cambie calendario, permisos, notas o conservación, se detiene solo esa conducta y se presenta la decisión concreta.

## Contratos y cambios

Métodos/rutas/DTO y compatibilidad: resumen por período, cierre de recepción y finalización por ID (coordinador); campos de estado de recepción y evaluación y de cierre efectivo en la consulta de períodos; estado derivado adicional de obligación según DP-03; retiro de `POST /dual/tutor/cierre`; cliente, contrato estático (`route_contract.json`), OpenAPI y fixtures actualizados juntos. La consulta de directorio deja de promediar por grado.

Datos, restricciones y conservación: migración `007_cierre.sql`, aditiva e idempotente sobre C06; el registro de cierres no se actualiza ni se borra; sin cascadas que borren expediente. Base nueva de pruebas.

Permisos y estados: solo coordinador cierra y finaliza (tutor y alumno 403); tutor y coordinador consultan; el alumno ve el estado de su período. Estados por período: recepción abierta → cerrada → evaluación finalizada; sin retroceso.

Archivos/módulos previstos (se fijan al pasar a READY tras inspeccionar el diff base): `database/migrations/007_cierre.sql` e `init-db.sh`; dominio `app/domain/grading.py` y casos de uso `app/application/use_cases/dual/cierres.py` (y `obligaciones.py` para la etiqueta); consultas, routers, DTO; bloqueo del período en `entregas.py`; `PeriodosDual.svelte` y el cliente; pruebas (`test_c07_cierre.py`, contrato, smoke C07) y documentación.

Comportamiento ante fallos/reintentos: cerrar y finalizar son transaccionales e idempotentes; si el cálculo falla no queda un período a medias; una entrega concurrente con el cierre termina de forma consistente con el orden de las transacciones; el registro congelado nunca cambia.

## Verificación

| AC | Prueba o recorrido | Nivel y datos | Resultado |
|---|---|---|---|
| C07-AC1 / AC-14 | Cierre anticipado con reportes por revisar: bloquea entregas y reenvíos y permite revisar lo recibido; el nombre y las fechas del período no cambian | HTTP + PostgreSQL reales | NO_VERIFICADA |
| C07-AC2 / AC-15 | Tutor y alumno no cierran (403); entrega concurrente con el cierre termina consistente con el orden transaccional; reintento de cierre idempotente | HTTP + PostgreSQL con concurrencia | NO_VERIFICADA |
| C07-AC3 / AC-16 | Notas aprobadas 8, 9 y 10 y un rechazo: promedio 9.00; sin aprobados "Sin calificación", no 0.00; empates de redondeo según DP-11 | HTTP + PostgreSQL reales; pruebas de dominio | NO_VERIFICADA |
| C07-AC4 / AC-17 | Con un pendiente finalizar se rechaza; resuelto el último, el coordinador finaliza y el promedio queda congelado e inmutable en la base | HTTP + PostgreSQL reales | NO_VERIFICADA |
| C07-AC5 / AC-18 | Finalizar un período mientras el nuevo recibe: no modifica el nuevo ni reasigna semanas | HTTP + PostgreSQL reales | NO_VERIFICADA |
| C07-AC6 / RN-24, DP-03 | Etiquetas de semanas no recibidas por cierre anticipado frente a atrasos reales; fechas calendario y cierre efectivo por separado | HTTP + PostgreSQL reales | NO_VERIFICADA |
| C07-AC7 | El promedio provisional y el final coinciden con la regla y el directorio ya no promedia por grado | Pruebas de dominio + HTTP real | NO_VERIFICADA |
| C07-AC8 | Panel del coordinador y avisos de alumno y tutor en escritorio y móvil con teclado | Preview visual del build desplegado | NO_VERIFICADA |

## Evidencia de implementación

Sin ejecución: spec en DRAFT. Añadir solo después de implementar, con fecha, entorno, revisión del código y clase REAL/SIMULADA/NO_VERIFICADA.

## Revisión

Veredicto: pendiente.
Revisor y modalidad: pendiente.
Hallazgos materiales: no aplica antes de implementación.
Correcciones y verificación focal: no aplica.
Limitaciones: la retención, el borrado y los respaldos (DP-11) no se resuelven aquí; no hay reapertura ni rectificación; el expediente integral y el visor son de C08; Drive y cualquier proveedor externo siguen NO_VERIFICADOS.

## Aprobaciones y cierre

Aprobación de READY: pendiente la orden del responsable (DP-04, DP-03 y DP-11 resueltas el 2026-10-16).
Aprobación de implementación: pendiente.
Aprobación de cierre: pendiente.
Resumen final: pendiente.
Siguiente spec: C08 solo después de implementar, revisar y cerrar C07.
Commit/push: el commit local de implementación se hace al aprobar el cierre; no hay push salvo indicación explícita.
