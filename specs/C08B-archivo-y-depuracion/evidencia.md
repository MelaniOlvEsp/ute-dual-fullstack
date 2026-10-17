# Evidencia C08B — Archivo y depuración

Fecha: 2026-10-17. Estado de la spec: DONE (cerrada el 2026-10-17; sin push).
Clases: REAL = HTTP, PostgreSQL y almacenamiento reales del Compose local (datos sintéticos); SIMULADA = pruebas con dobles o con el reloj movido por SQL; NO_VERIFICADA = no observado.

## Resumen por criterio

| Criterio | Clase | Fuente |
|---|---|---|
| C08B-AC1 sin paquete o confirmación no se elimina; con ellos se programa y al vencer se eliminan solo los PDF del paquete | REAL | `smoke_c08b.py` |
| C08B-AC2 notas, promedios, versiones y revisiones intactos; filas archivadas con clave y hash | REAL | smoke C08B |
| C08B-AC3 fallo real del almacenamiento: purga pendiente con error, reanudable | REAL; archivos ausentes y atomicidad con dobles SIMULADA | smoke C08B, `test_c08b_depuracion.py` |
| C08B-AC4 permisos (tutor y coordinador sí, alumno 403, sin sesión 401) y validaciones | REAL | smoke C08B |
| C08B-AC5 410 en descargas, 409 en paquetes, expediente con «Archivado el…» | REAL (HTTP) y visual | smoke C08B, navegador integrado |
| C08B-AC6 diálogo de confirmación | REAL parcial (escritorio y 375 px); «Conservar todo» y teclado NO_VERIFICADA | navegador integrado |
| C08B-AC7 registro inmutable | REAL | smoke C08B |
| C08B-AC8 gracia de 7 días, cancelación y tarea de fondo | REAL con reloj SIMULADO por SQL | smoke C08B |

## Ejecuciones

- Backend `python -m unittest discover -s tests`: 214 pruebas OK (23 nuevas en `test_c08b_depuracion.py`: 410, estados del expediente, paquetes tras depurar, programación con todas sus validaciones, cancelación, ejecución con éxito y con fallo revertido, vencidas con una falla, reintento manual sin detalles internos, resumen por carrera, eliminación idempotente sobre archivos reales y contrato SQL). Casos de uso SIMULADA; `purgar_documento` REAL sobre archivos temporales.
- JS: 39/39 (4 nuevas de `archivo.js`). Contrato de integración: 70 llamadas del frontend contra 68 rutas. Vite build sin avisos nuevos propios (aviso de región desplazable con `tabindex`, igual que en el expediente de C08).
- Smoke C08B PASS con HTTP, PostgreSQL y almacenamiento reales, dos corridas: sin paquete previo 409 y nada eliminado; permisos y validaciones; paquetes de respaldo por carrera y por alumno; el coordinador programa con gracia de 7 días y el hash del manifiesto del paquete queda en la purga; repetir devuelve la misma purga; el alumno ve «programada» con la fecha y sin identificador de purga; las descargas siguen funcionando; cancelar libera los documentos y es idempotente; reprogramar y conflicto 409 con un alcance que ya incluye los archivos; reloj SIMULADO con SQL; fallo real del almacenamiento (un directorio ocupa el lugar del archivo): 500 sin detalles internos, purga programada con intento y error, sin filas archivadas; la tarea de fondo real ejecuta la purga vencida de TII en menos de dos minutos; el reintento manual completa la de MER tras restaurar el archivo; solo los PDF del paquete desaparecen y el original rechazado queda; notas congeladas y conteos iguales; UPDATE y DELETE sobre purgas y cambios de hash o restablecimiento de documentos rechazados por la base; 410 en descargas de personal, alumno y tutor; paquetes 409; expediente archivado; resumen «depurado»; nueva programación 409 «ya están depurados».
- Regresión: smokes C01 a C08 PASS (no requirieron cambios).
- Migración `009_depuracion.sql`: aplicada dos veces a la base local sin error; instalación en base nueva (esquema + 003 a 009, 009 dos veces) sin errores.

## Visual REAL (navegador integrado, datos sintéticos)

Coordinador en escritorio: el panel «Archivo y depuración de archivos» muestra por carrera alumnos, archivos, tamaño, paquete generado y estado; «Depurar archivos…» abre un diálogo centrado con la advertencia (cantidad y tamaño, 7 días, irreversible después, qué se conserva), la confirmación de la copia, la frase a escribir y «Conservar todo» como acción principal; «Programar depuración» queda deshabilitada con una frase distinta o sin marcar la confirmación y se habilita con la frase exacta; al programar, la fila muestra «Depuración programada · Se eliminan el 24 oct 2026» con «Cancelar depuración» y el historial cuenta las purgas. Alumno a 375 px sin desborde horizontal: antes de vencer ve el aviso «se eliminarán el 24 oct 2026… tus notas, tu promedio y tu historial se conservan»; después de ejecutarse la tarea de fondo ve «se depuraron el…», «Archivado el …» en cada reporte, sin Ver/Firmado/Original ni botón de ZIP, y el promedio 9.00 intacto.

## Defectos encontrados y corregidos durante la implementación

- El diálogo se dibujaba pegado a la esquina porque el reseteo global quita el margen automático del `dialog`: se añadió `margin: auto`.
- Las fechas de depuración llegaban como instantes UTC y el aviso mostraba un día distinto del motivo del paquete: el servidor ahora entrega fechas civiles (America/Mexico_City) y el panel del personal usa fecha y hora locales.
- En el contrato de la API se había perdido el encabezado «Reglas objetivo generales» al documentar C08 (error de la sustitución de texto); se restauró.

## NO_VERIFICADO / limitaciones

- Revisión independiente: no hubo; la revisión técnica fue del mismo agente.
- Reloj de la gracia SIMULADO moviendo `solicitada_en` y `ejecutar_en` con SQL (se desactiva el disparador solo en esa sentencia); no se esperaron 7 días reales.
- «Conservar todo» y el teclado completo del diálogo, tema oscuro y móvil físico; no se observó el panel con una purga completada ni el historial desplegado.
- La depuración elimina los PDF del paquete; los originales de versiones rechazadas o reemplazadas permanecen en el almacenamiento (no están en el paquete). La depuración no alcanza copias de seguridad ni el volumen respaldado (DP-11, C10).
- La tarea de fondo corre dentro del proceso de la API (un ciclo cada 60 s por omisión); con varias réplicas el bloqueo `SKIP LOCKED` evita duplicados, pero no se probó con más de un proceso. Si la API está apagada al vencer la gracia, la purga se ejecuta al volver a levantarla.
- El registro de paquetes acredita la generación, no la descarga ni el guardado externo; la confirmación de «ya guardé la copia» es una declaración del usuario.
- Drive y cualquier proveedor externo siguen NO_VERIFICADOS.

## Decisiones aplicadas

D1 (alcance por carrera o por alumno con el paquete del mismo alcance), D2 (tutor y coordinador pueden depurar) y D3 (gracia de 7 días con cancelación y eliminación automática) del 2026-10-16, registradas en DP-14; la tarea de fondo mínima se adoptó al no haber objeción.

## Acta de cierre

La revisión técnica concluyó APPROVED el 2026-10-17 sin defectos materiales; la visual reutilizó el preview de la implementación porque la interfaz no cambió. El responsable otorgó aprobación de cierre el 2026-10-17 con `CLOSE C08B`. C08B queda DONE con las limitaciones de la spec. El commit local de implementación se hizo con el cierre; no hay push.
