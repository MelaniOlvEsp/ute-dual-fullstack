# Evidencia C08 — Expediente y visor

Fecha: 2026-10-16. Estado de la spec: DONE (cerrada el 2026-10-16; sin push).
Clases: REAL = HTTP, PostgreSQL y almacenamiento reales del Compose local (datos sintéticos); SIMULADA = pruebas con dobles o con el reloj movido por SQL; NO_VERIFICADA = no observado.

## Resumen por criterio

| Criterio | Clase | Fuente |
|---|---|---|
| C08-AC1 expediente por período con grupo histórico, aprobados, promedio y descarga byte a byte | REAL | `smoke_c08.py` |
| C08-AC2 IDOR, permisos y rutas heredadas retiradas | REAL | `smoke_c08.py`, smokes C02, C05, C06 |
| C08-AC3 alumno de baja conserva expediente y aparece en el directorio | REAL | `smoke_c08.py` |
| C08-AC4 directorio paginado, filtros, comodines escapados, parámetros inválidos | REAL | `smoke_c08.py`, `smoke_c07.py` |
| C08-AC5 visor: carga autenticada, abrir y descargar | REAL parcial; zoom, lectura, PDF escaneado o de varias páginas y error con reintento NO_VERIFICADA | navegador integrado |
| C08-AC6 paquete ZIP por alumno y por carrera, manifiesto, CSV protegido, archivo faltante, registro inmutable | REAL; apertura en una hoja de cálculo NO_VERIFICADA | `smoke_c08.py` |
| C08-AC7 «Mi expediente» y expediente del personal | REAL parcial (vista angosta del alumno y escritorio del tutor) | navegador integrado |
| C08-AC8 ventana de una semana del alumno | REAL con reloj SIMULADO por SQL; límites del cálculo también en pruebas de dominio | `smoke_c08.py`, `test_c08_expediente.py` |

## Ejecuciones

- Backend `python -m unittest discover -s tests`: 187 pruebas OK (28 nuevas en `test_c08_expediente.py`: ventana, nombres seguros, protección de CSV, manifiesto estable, constructor de ZIP con archivos reales —incluye faltante, hash distinto, duplicados y limpieza del temporal—, casos de uso con dobles y contrato SQL). Casos de uso SIMULADA; constructor de ZIP REAL sobre archivos temporales.
- JS: 35/35 (6 nuevas de `expediente.js` y descargas con nombres seguros). Contrato de integración: 66 llamadas del frontend contra 64 rutas del backend; ninguna llamada a rutas retiradas.
- Smoke C08 PASS con HTTP, PostgreSQL y almacenamiento reales, cuatro corridas seguidas: dos períodos finalizados para un alumno con cambio de grupo; promedios finales 9.00 y 9.50 leídos del registro congelado; corrección de nota marcada (9 → 10); alumno de baja sin aprobados con «Sin calificación»; directorio con total, páginas de 3 y 1, filtros por período, grupo (grupo actual), búsqueda y situación, comodines `%_\` escapados y parámetros inválidos 422; descarga de aprobado firmado y original con el SHA-256 igual al almacenado, rechazado 404, alumno 403, sin sesión 401; paquete propio (6 entradas: 4 PDF, manifiesto y CSV, solo la matrícula propia; cada hash del manifiesto coincide con los bytes; el hash del registro coincide con el del manifiesto); paquete por alumno con el grupo de ese período; paquete por carrera con cuatro alumnos y ocho archivos (el nombre que empieza con `=` sale como `'=…`); 409 sin finalizar y con un PDF movido del almacenamiento (sin paquete y sin registro) y 200 al restaurarlo; coordinador y alumno 403 en paquetes del tutor; registro inmutable (UPDATE, DELETE y hash inválido rechazados por la base); ventana: a 6 días 23 horas 200, a 8 días 403 y el expediente sigue completo.
- Regresión: smokes C01 a C07 PASS. C02, C03, C05, C06 y C07 se adaptaron a las rutas nuevas (`/expediente`, `/paquete`, `/versiones/{n}/pdf`, directorio paginado con `q`) y C07 ya no consulta la query retirada del directorio.
- Migración `008_paquetes.sql`: instalación en base nueva (esquema + 003 a 008) sin errores y reaplicación idempotente de la 008.
- Vite build: sin avisos nuevos en las páginas tocadas (los selectores CSS no usados de `CoordinadorCarrera.svelte` ya existían antes de C08).

## Visual REAL (navegador integrado, datos sintéticos)

Alumno, vista angosta: «Mi expediente» muestra el aviso de cada paquete con la fecha límite, el selector de período, el grupo del período, el promedio «9.50 final · 2 aprobados · suma 19», las fechas con «Recepción cerrada el 16 oct 2026», el botón «Descargar mi paquete (ZIP)» y la tabla de aprobados con Ver, Firmado y Original; al elegir «Ver» se monta el visor con «Abrir en pestaña nueva» y «Descargar». El navegador integrado no pinta PDF incrustados (el área queda en blanco), por eso esas dos acciones están siempre visibles. Tutor, escritorio: el directorio muestra «1–50 de 277 alumnos» con Anterior y Siguiente, la insignia «Baja» con fecha, aprobados y promedio por alumno, y el panel «Paquete de archivo por carrera» con carrera y períodos finalizados; el expediente del alumno de baja muestra su situación, el grupo histórico, el promedio final y «Descargar paquete del alumno (ZIP)».

## Defectos encontrados y corregidos durante la implementación

- El smoke C08 era intermitente porque los dos períodos se generaban al azar y el «grupo actual» del alumno depende del período más reciente: se ordenan por fecha. El generador de períodos pasados de C07 y C08 se agotaba (72 etiquetas) y colgaba: se amplió a 132 y se detectó con la corrida de preparación del preview.
- Las pruebas JS viejas de exportación CSV se reemplazaron por las de paquete y descarga con nombres seguros.

## Revisión y corrección (2026-10-16)

La revisión técnica (mismo agente) concluyó CHANGES_REQUESTED con un hallazgo material, M1: el directorio respondía 500 con `desplazamiento` fuera del rango de bigint y con un byte NUL en `q` (y NUL en la matrícula del expediente), lo que contradecía C08-AC4. Corrección: `desplazamiento` acotado a 0–10 000 000 y NUL rechazado con 422 en `q`, `grupo`, `cuatrimestre` y en la matrícula del expediente y de los paquetes, antes de llegar a la base (`expediente.validar_texto`). Verificación: 190 pruebas de backend OK (3 nuevas, `EntradasMalformadasTests`), `smoke_c08.py` con las cinco entradas malformadas por HTTP real (422) PASS y `smoke_c07.py` PASS. Revisión focal del mismo agente: cambio acotado a validación previa a la consulta, sin hallazgos nuevos.

## NO_VERIFICADO / limitaciones

- Revisión independiente: pendiente (la spec sigue IN_PROGRESS).
- Zoom, lectura, PDF escaneado o de varias páginas y el estado de error con «Reintentar» del visor no se vieron: el navegador integrado no incrusta PDF y el error no se provocó visualmente (el reintento está cubierto solo por el código).
- Teclado completo, tema oscuro, 375 px real y móvil físico; apertura del CSV en Excel u otra hoja de cálculo (solo se comprobó el texto del CSV).
- La ventana del alumno se simuló moviendo la finalización con SQL (se desactiva el disparador solo en esa sentencia).
- El registro `paquetes_archivo` acredita la generación del ZIP, no que se haya descargado ni guardado fuera; el paquete de una carrera no tiene límite de tamaño ni de tiempo.
- La depuración de archivos con confirmación (DP-14) no está implementada: es C08B. Los reportes heredados sin obligación no se cuentan. Drive y cualquier proveedor externo siguen NO_VERIFICADOS.
- El directorio filtra por el grupo actual del alumno (el histórico por período está en el expediente).

## Decisiones aplicadas

Alcance de la exportación (ZIP por alumno y por carrera, solo el tutor, con el período finalizado), ventana de una semana desde la finalización para el alumno y depuración posterior como incremento aparte (DP-14), registradas en `docs/analysis/DECISIONES_PENDIENTES.md` y en la spec.

## Acta de cierre

La segunda revisión técnica (tras corregir M1) concluyó APPROVED el 2026-10-16 sin defectos materiales; la visual se limitó a los recorridos ya observados porque la interfaz no cambió. El responsable otorgó aprobación de cierre el 2026-10-16 con `CLOSE C08 + NEXT SPEC`, sujeta a revisión aprobada y evidencia suficiente. C08 queda DONE con las limitaciones de la spec. El commit local de implementación se hizo con el cierre; no hay push.
