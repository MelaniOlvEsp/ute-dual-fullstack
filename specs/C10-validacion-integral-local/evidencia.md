# Evidencia C10 — Validación integral local

Fecha: 2026-10-17. Estado de la spec: DONE (cerrada el 2026-10-17; sin push).
Clases: REAL = HTTP, PostgreSQL y Drive reales (cuenta de pruebas) con datos sintéticos; SIMULADA = pruebas con dobles; NO_VERIFICADA = no observado.
Los identificadores de Drive y las credenciales no se anotan.

## Resumen por criterio

| Criterio | Clase | Fuente |
|---|---|---|
| C10-AC1 recorrido integral con tres roles y dos alumnos en períodos distintos; el primero no cambia | REAL | `smoke_c10.py` PASS en la base de desarrollo y, aparte, en un proyecto Compose limpio con su propia carpeta de Drive |
| C10-AC2 controles negativos | REAL (acceso cruzado A/B, tutor y alumno intentando cierre y finalización, archivo ausente del almacenamiento, PDF corrupto y de otro tipo, envío concurrente, buzón con hilo cerrado); fallo de Drive inyectado (token, cuota, red) SIMULADA en C10A | `smoke_c10.py`, `test_c10a_almacenamiento.py` |
| C10-AC3 / AC-24 respaldo coherente y restauración aislada | REAL con una base nueva; la base y la carpeta vivas no se midieron antes y después (aislamiento por diseño y por una negativa explícita a restaurar sobre la carpeta de respaldos) | `respaldo.ps1`, `restaurar.ps1`, `respaldo.py` |
| C10-AC4 restauración de un respaldo anterior a una depuración | REAL | restauración de `…-periodo` con el registro de `…-depuracion` |
| C10-AC5 respaldo incompleto o alterado se detecta y se rechaza | REAL (documento faltante, hash distinto, volcado alterado, volcado dañado con `pg_restore --list`, base con 569 referencias sin archivo) + SIMULADA (8 pruebas unitarias) | `probar-fallos`, `restaurar.ps1`, `test_c10_respaldo.py` |
| C10-AC6 la guía se sigue desde cero | REAL parcial: proyecto Compose, base y carpeta de Drive nuevos, recorrido, respaldo y restauración ejecutados; no se repitió `setup-local.ps1` sin `.env`, el alta interactiva del coordinador ni la autorización OAuth desde cero (hecha en C10A) | `GUIA_DE_USO_Y_OPERACION.md` |
| C10-AC7 teclado, tema oscuro y vista móvil | REAL parcial: vista móvil emulada (375 y 768 px) con auditoría automática en claro y oscuro de las pantallas de los tres roles, teclado de acceso y menú, visor del PDF firmado. El escritorio de 1280 px no se revisó visualmente (la emulación se reduce al tamaño del panel) y los diálogos con teclado no se repitieron | navegador integrado |
| C10-AC8 trazabilidad AC-01 a AC-24, contratos y documentación | REAL (revisión documental; suites automáticas) | tabla de este archivo |

## Ejecuciones

- **Paso 0 (regresión):** el permiso de Drive estaba vigente; `smoke_c10a.py` parte B y los smokes C07, C08, C08B y C09 PASS con Drive tras ampliar el rango de años de las etiquetas pasadas a 1500–1899 (D4; antes se colgaban). Los smokes C01 a C06 y C08B habían pasado con Drive ese mismo día en C10A.
- **`smoke_c10.py` (nuevo):** un solo guion con el coordinador, dos tutores y dos alumnos (TII en el período 1 y MER en el período 2, ambos pasados y abiertos por SQL): foro y anuncio; plantilla Word/PDF publicada y descargada byte a byte; entregas con una réplica del formato que tiene la tabla; PDF corrupto o de otro tipo sin rastro; rechazo y reenvío (versión 2, historial conservado); aprobación con firma en la celda (`firma = celda`); envío concurrente (un 201 y cinco 409); revisión por el segundo tutor; expediente; archivo firmado eliminado de Drive → 404/409/503 sin entregar nada ni detalles internos y luego repuesto; tutor y alumno sin permiso para cerrar o finalizar; cierre de recepción con una entrega pendiente; reenvío bloqueado; finalización rechazada por el pendiente; aprobación posterior al cierre; finalización con promedio 9.00 (suma 27, tres aprobados); segundo período finalizado con 8.00 sin modificar el primero (resumen, cierres y expediente idénticos); acceso cruzado A/B en cinco rutas y paquetes; ZIP del alumno y de la carrera; depuración programada y cancelada (la gracia no elimina nada); buzón completo con hilo cerrado, hilo enlazado y reapertura. 5 inicios de sesión. PASS en la base de desarrollo y PASS en un proyecto Compose limpio (`c10-origen`, base y carpeta de Drive nuevas).
- **Respaldo y restauración (entorno limpio `c10-origen`):** respaldo previo a la depuración (12 documentos); `smoke_c10_depuracion.py` ejecutó una depuración vencida real (6 archivos eliminados de Drive; el reloj se simuló con SQL como en C08B); respaldo posterior (6 documentos y 6 depurados sin copia); restauración del primero con el registro del segundo en un proyecto Compose aparte (`c10-restauracion`, base nueva) y una carpeta de Drive nueva: «VERIFICADA» (referencias comprobadas 6, 6 depurados tras el respaldo que no reaparecen, 4 descargas de muestra correctas por la API restaurada, conteos y huellas de notas, revisiones y versiones dentro del intervalo del manifiesto); proyecto y carpeta eliminados con `-Descartar`.
- **Detección de fallos (AC5):** `probar-fallos` creó variantes del manifiesto y las cuatro se detectaron (documento faltante, SHA-256 distinto, volcado alterado, sin manifiesto); la restauración de un volcado con cabecera válida pero dañado se rechazó con `pg_restore --list` sin tocar la base de prueba; el respaldo de la base de desarrollo (569 documentos referenciados sin archivo en Drive por el modo local anterior a C10A) se rechazó con código 2 y no dejó volcado suelto.
- **Pruebas:** backend 281 OK con 1 omitida (268 + 13 de `test_c10_respaldo.py`: retención 8 + 4 y verificación del respaldo; también con `ALMACENAMIENTO=memoria`); frontend 40 OK; contratos 1 OK (73 rutas, sin cambios de API).
- **Revisión visual (2026-10-17, mismo agente, técnica y visual):** acceso solo con teclado (correo, Tab, clave, Intro) termina en el foro para alumno y tutor; el menú se abre con Tab+Intro, el foco pasa a «Cerrar menú» y Escape lo cierra; tema oscuro legible en foro, reportes y expediente; el visor del PDF firmado (que sale de Drive) se muestra con su barra (descargar, imprimir, abrir en pestaña nueva y «Descargar»). Auditoría automática por iframe a 375 y 768 px en claro y oscuro: **sin desbordes horizontales, sin controles sin indicador de foco y sin controles sin etiqueta** en las 7 pantallas del tutor, 5 del coordinador y 4 del alumno, salvo H1.

## Revisión y corrección (2026-10-17)

La revisión técnica y visual (mismo agente, no independiente) concluyó CHANGES_REQUESTED con un defecto material. **M1:** `respaldo.ps1` lanzaba `pg_dump` antes de que `respaldo.py` tomara los conteos y la huella "antes", así que una escritura entre ambos pasos hacía que una restauración correcta se reportara con errores, y `instantes.conteos_antes` no reflejaba el instante del volcado. **Corrección:** el nuevo subcomando `instantanea` toma conteos y huella antes del `pg_dump`; `crear` los exige (rechaza el respaldo si faltan, son incompletos o tienen más de una hora) y el manifiesto registra `conteos_antes_del_volcado` y `conteos_despues_del_volcado`. **Verificación:** backend 279 pruebas OK (3 nuevas: instantánea válida, vieja/incompleta/ausente rechazada y orden instantánea → `pg_dump` en el procedimiento; una se omite dentro de la imagen) y una prueba REAL en un entorno limpio nuevo (`smoke_c10.py` PASS, carpeta de Drive nueva): respaldo con otro proceso insertando usuarios sin parar (15 → 40 filas durante el respaldo) y restauración «VERIFICADA» (12 referencias, 6 descargas de muestra correctas, conteos dentro del intervalo). Las observaciones menores de la revisión (`probar-fallos` sin documentar, falta de guardas al ejecutar subcomandos a mano, poda concurrente con un respaldo) no se tocaron por ser de alcance mayor; siguen abiertas como notas. Revisión focal (mismo agente): cambio acotado a `respaldo.py`, `respaldo.ps1` y su test, sin hallazgos nuevos; la instantánea previa no contiene datos sensibles (solo conteos y una huella) y se elimina al terminar.

**Segunda revisión (mismo agente, técnica): CHANGES_REQUESTED, M2.** La restauración exigía que la huella de notas, revisiones y versiones coincidiera con la de uno de los dos extremos del respaldo; con dos o más cambios en esas tablas alrededor del volcado, el estado intermedio no coincide con ninguno y una restauración correcta se reportaba con errores (la prueba concurrente del FIX solo escribió usuarios, que no entran en la huella). **Corrección:** `comparar_huella`: en reposo (extremos iguales) debe coincidir; si hubo cambios, coincide con uno de los extremos y, si no, se informa «no concluyente» con un aviso (los conteos siguen comprobándose) sin marcar error. **Verificación:** backend 281 OK con 1 omitida (2 pruebas nuevas) y un respaldo y una restauración REALES en un entorno limpio nuevo (`smoke_c10.py` PASS, carpeta de Drive nueva): «VERIFICADA». El camino «no concluyente» solo se probó de forma unitaria (SIMULADA): no se forzaron escrituras reales en revisiones o versiones durante el volcado. Revisión focal (mismo agente): cambio acotado a `respaldo.py` y su test, sin hallazgos nuevos.

## Hallazgos de interfaz (no bloquean el uso; candidatos a una spec de corrección, no a C10)

- **H1:** `/dual/tutores` (coordinador) desborda 173 px a 375 px: el formulario y la columna «Acciones» salen de la pantalla.
- **H2:** contraste por debajo de AA (4.5:1) en textos secundarios: la pestaña activa «Anuncios» (blanco sobre naranja, 2.8:1), los botones naranja como «Abrir período» (2.8:1) y las etiquetas y encabezados en mayúscula del tema claro (≈2.5:1; ≈3.5–4.0:1 en el oscuro). La cifra sale de una aproximación automática (puede marcar de más, por ejemplo emojis); conviene confirmarla con una herramienta de accesibilidad.
- **H3:** las tablas de versiones y de aprobados necesitan desplazamiento horizontal en pantallas angostas (la acción «Ver» queda fuera de vista) y la barra de desplazamiento es clara en el tema oscuro.

## Trazabilidad AC-01 a AC-24

| AC | Incremento | Clase y fuente | Sin verificar |
|---|---|---|---|
| AC-01 | C01 | REAL: smoke C01 y, en C10, instalación limpia en un proyecto nuevo + `smoke_c10.py` | `setup-local.ps1` sin `.env` no se repitió |
| AC-02, AC-03 | C02 | REAL: smoke C02 (ejecutado por el usuario el 2026-10-15) y, con Drive, el smoke C02 de C10A | la recuperación de acceso la ejecuta el tutor desde la plataforma |
| AC-04 | C02, C08, C09 | REAL: smokes C02, C08, C09 y los negativos cruzados de C10 | |
| AC-05 | C03 | REAL: smoke C03 | |
| AC-06, AC-08 | C04 | REAL: smoke C04 (reloj real) | |
| AC-07 | C04 | REAL con reloj inyectado en casos de uso (el reloj del servidor no se mueve) | |
| AC-09, AC-10, AC-11 | C05 | REAL: smoke C05 y reenvío y concurrencia de C10 | |
| AC-12 | C06 | REAL: smoke C06 | |
| AC-13 | C06 | REAL; firma en la celda comprobada en C10 con el formato real del responsable (celda «Firma» de «Tutor académico») | otras plantillas de reporte distintas del formato actual |
| AC-14 a AC-18 | C07 | REAL: smoke C07 y C10 (cierre, finalización, pendiente, otro período) | el cierre anticipado usa un instante movido por SQL |
| AC-19 | C08 | REAL: smoke C08 y C10 (períodos anteriores, grupo histórico, promedio) | |
| AC-20 | C08 | REAL parcial: carga autenticada, descarga, abrir en pestaña nueva y visor con barra en el navegador integrado | error visible con reintento, PDF escaneado y escritorio grande |
| AC-21, AC-22, AC-23 | C09 | REAL: smoke C09 y C10; en C10 también el tutor entra al foro | |
| AC-24 | C10 | REAL con una base y una carpeta de Drive nuevas (datos sintéticos) | recuperación de una producción; móvil físico; hospedaje |

## Lo que NO se probó (y por qué)

- Móvil físico y hospedaje (fuera del alcance). El escritorio de 1280 px no se revisó visualmente.
- La caducidad real del permiso de Drive a los 7 días (alrededor del 2026-10-24), la cuota gratuita y los límites de Drive a escala; varias réplicas de la API.
- Cifrado del respaldo (D3: sin cifrar solo con datos sintéticos).
- Una restauración que parte de un respaldo anterior a una depuración deja las filas de esos documentos sin marcar como archivadas (la fila de la purga no existe en esa copia): sus archivos se eliminan de nuevo, pero la descarga responde 404 en vez de 410 hasta restaurar un respaldo posterior. Se documenta como límite; lo normal es restaurar el más reciente.
- `setup-local.ps1` desde cero, el alta interactiva del coordinador y la autorización OAuth se siguieron solo en parte.
- Los hallazgos H1 a H3 no se corrigieron: C10 no agrega funciones ni corrige interfaz.

## Decisiones e interpretaciones

D1 a D4 de la spec (resueltas el 2026-10-17). Interpretaciones al implementar: (1) la base de desarrollo contiene filas de pruebas del modo local anterior a C10A cuyos archivos no existen en Drive, así que la validación del respaldo y la restauración corrió en un proyecto Compose limpio con su propia carpeta de Drive (consistente con ADR-09: base nueva); (2) la retención se implementó como «los 8 respaldos más recientes más el más antiguo de cada uno de los 4 meses más recientes», sobre todos los respaldos sin distinguir su etiqueta; (3) los documentos se copian una sola vez (son de solo escritura) y la poda elimina las copias que ningún respaldo conservado referencia; (4) la verificación acepta los conteos entre los tomados antes y después del volcado y compara la huella de notas, revisiones y versiones; (5) el manifiesto no está firmado: la integridad de la copia se apoya en los SHA-256 que registra, no en un sello del propio manifiesto.

## Archivos nuevos o modificados

`scripts/smoke_c10.py`, `smoke_c10_depuracion.py`, `respaldo.py`; `scripts/respaldo.ps1`, `restaurar.ps1`; servicio `respaldo` en `docker-compose.yml`; `.respaldo-tmp/` en `.gitignore`; `tests/test_c10_respaldo.py`; los cuatro smokes con el rango de años; textos finales de los smokes C05 a C07; `GUIA_DE_USO_Y_OPERACION.md`, `REGISTRO_DE_RESPALDOS.md`, `VALIDACION_Y_OPERACION_LOCAL.md`, `README_INTEGRACION.md`, `docs/README.md`, `PLAN_MAESTRO.md`, `CONTRATO_API.md` y las specs C10 y C10A.

## Acta de cierre

La tercera revisión técnica (mismo agente) concluyó APPROVED el 2026-10-17 sin defectos materiales, después de corregir M1 y M2. El responsable otorgó la aprobación de cierre con `CLOSE C10 + NEXT SPEC` sabiendo que quedan sin verificar la actividad real sobre notas durante un respaldo, la caducidad del token de Drive, `setup-local.ps1` y la autorización OAuth desde cero, la revisión visual a 1280 px, el móvil físico y el hospedaje, y que los hallazgos de interfaz H1 a H3 y tres observaciones menores del respaldo siguen sin corregir. C10 queda DONE. El commit local de implementación se hizo con el cierre; no hay push.

