# Evidencia C10A — Almacenamiento en Drive

Fecha: 2026-10-17. Estado de la spec: DONE (cerrada el 2026-10-17; prueba contra Drive real realizada ese mismo día, ver «Prueba con Drive real»; sin push).
Clases: REAL = HTTP, PostgreSQL y almacenamiento reales del Compose local (datos sintéticos); SIMULADA = pruebas con dobles o con un transporte simulado; NO_VERIFICADA = no observado.

## Resumen por criterio

| Criterio | Clase | Fuente |
|---|---|---|
| C10A-AC1 guardar, leer y eliminar de forma definitiva en Drive | REAL con Drive; además SIMULADA (cliente real de Google sobre un transporte simulado) | `smoke_c10a.py` parte B, `test_c10a_almacenamiento.py` |
| C10A-AC2 hash distinto nunca se entrega; ausente con error claro | REAL con Drive y con el adaptador local de regresión; SIMULADA en pruebas unitarias | `test_c05_entregas.py`, `test_c10a_almacenamiento.py` |
| C10A-AC3 Drive no disponible: falla cerrada | REAL parcial (sin autorizar: 503 sin filas ni archivos); token caducado, cuota y red SIMULADA | smokes C05 a C08B y C10A (parte A), pruebas unitarias |
| C10A-AC4 reintentos con espera creciente y límite | SIMULADA | `test_c10a_almacenamiento.py` |
| C10A-AC5 smokes C01 a C09 con el almacenamiento nuevo | REAL con Drive (y con el adaptador local de regresión) | smokes C01 a C09 y C08B |
| C10A-AC6 sin secretos ni IDs de Drive | REAL parcial | smoke C10A parte A, revisión de código |
| C10A-AC7 nada persistente en disco | REAL con Drive autorizado (sin temporales ni escritura local en los smokes) | smoke C10A parte B y smokes con Drive |

## Ejecuciones

- Backend `python -m unittest discover -s tests`: 268 pruebas OK (también con el valor predeterminado `drive`). Nuevas (`test_c10a_almacenamiento.py`): contrato común sobre los adaptadores de memoria y de carpeta (guardar, leer, existir, eliminar de forma definitiva e idempotente, claves de solo escritura, validación de nombres y listado); adaptador de Drive sobre un servicio simulado (nombre con la clave, SHA-256 como propiedad, MD5 que no coincide elimina lo subido y falla, reintento idempotente, 403 de cuota y 429 y 5xx con esperas 1, 2 y 4 s y límite de cinco intentos, errores permanentes sin reintento con su código, autorización revocada como `token_caducado`, errores de red, sin carpeta raíz como `sin_configurar`, eliminación definitiva) y sobre el cliente real de Google con un transporte simulado (peticiones válidas de lista, subida, comprobación del MD5 y eliminación). Ajustadas: C05, C06, C08, C08B y C09 (usan los adaptadores en vez de rutas) y la lectura con SHA-256 en los casos de uso de descarga.
- Contrato HTTP: sin cambios (73 rutas); las descargas siguen siendo respuestas binarias autenticadas y ningún cliente recibe un identificador de Drive.
- Regresión con `ALMACENAMIENTO=local` (adaptador de regresión): smokes C01 a C09 y C08B PASS. Los smokes de C05, C06, C08, C08B y C09 se adaptaron para leer, listar y eliminar a través del mismo contrato (en C08B, la inyección de un fallo de eliminación solo corre con el adaptador local).
- Falla cerrada REAL: con el valor predeterminado (`drive`) y sin autorizar, las entregas respondieron 503 «El almacenamiento de archivos no está disponible…» y `/health` informó `{"tipo": "drive", "estado": "sin_configurar"}` sin ningún secreto; `smoke_c10a.py` (parte A) verifica que la publicación de una plantilla responde 503 sin filas y que el error no expone detalles internos.
- Retiro del adaptador heredado: `integrations/drive.py` y `google_auth.py`, las funciones de lectura de Drive y de ruta local de `dual_reports` y sus entradas en el puerto de servicios; la columna `archivo_pdf_local` ya no se escribe.

## Revisión y corrección (2026-10-17)

La revisión técnica (mismo agente) concluyó CHANGES_REQUESTED con dos hallazgos materiales en el adaptador de Drive, ambos por la permisividad de Drive con los nombres repetidos. M1: la búsqueda o creación de una subcarpeta no estaba protegida (dos hilos que estrenan un espacio creaban dos carpetas `documentos` y los archivos de la carpeta «perdedora» dejaban de encontrarse, con la depuración dándolos por eliminados). M2: un reintento de la subida tras perder la respuesta creaba un segundo archivo con la misma clave y `eliminar` solo borraba uno, dejando una copia recuperable. Corrección: candado por espacio durante buscar o crear, elección determinista de la carpeta más antigua (`orderBy=createdTime`, también tras un reinicio o ante otro proceso, y se descarta la carpeta propia vacía si otro la creó a la vez), comprobación en cada intento de la subida de que la clave no existe ya (se reutiliza si tiene la misma huella y nunca se sobrescribe otra) y `eliminar` borra todas las copias que encuentre. Verificación: 5 pruebas nuevas (dos hilos con una barrera que fuerza la carrera, carpetas duplicadas y creación concurrente de otro proceso, reintento tras respuesta perdida con un solo archivo resultante, clave ocupada por otro contenido y eliminación de duplicados) y 268 pruebas de backend OK. Ambas correcciones siguen SIMULADA: se confirmarán con Drive real. Revisión focal del mismo agente: cambio acotado al adaptador, sin hallazgos nuevos.

## Prueba con Drive real (2026-10-17, tras el cierre)

Con la cuenta de pruebas autorizada (OAuth de usuario, `drive.file`, aplicación en modo de prueba) y la carpeta raíz creada por la aplicación: `smoke_c10a.py` parte B PASS (guardar, leer byte a byte con huella, reintento idempotente, clave de solo escritura, listado, archivo de más de 5 MB reanudable, eliminación definitiva sin papelera y sin temporales) y los smokes C01 a C09 y C08B PASS contra Drive (entre 6 y 64 s cada uno; nada se escribió en el volumen local). Revisión posterior (técnica y visual del PDF, APPROVED, sin defectos materiales): el PDF firmado de una entrega real de la demostración se leyó desde Drive por el contrato de almacenamiento (`/health`: `drive`, `ok`), tiene 1 página, `firma_modo = celda` y la firma queda dentro de la celda «Firma» de la fila «Tutor académico» del ejemplo real con tabla. Esto cierra AC1, AC2, AC5 y AC7 como REAL; AC4 (reintentos, límites de cuota) y las rutas de token caducado, cuota y red siguen SIMULADA. AC6 se mantiene parcial: no se repitió una búsqueda de secretos con Drive autorizado.

Nota de operación observada: los smokes C07, C08, C08B y C09 comparten un generador de etiquetas de períodos pasados cuyo conjunto (132 etiquetas) quedó agotado por las ejecuciones acumuladas en la base de pruebas, y se cuelgan al generarlas; se corrige en C10 (ver su spec), no es un defecto del almacenamiento.

## Lo que NO se probó (y por qué)

- La vista previa embebida del PDF en el navegador de la plataforma (el navegador integrado no la renderiza) y la interfaz completa con Drive: pasan a C10 (revisión visual).
- La caducidad real del token a los 7 días, la cuota gratuita y los límites de peticiones de Drive: solo se simularon las respuestas.
- La carga reanudable (más de 5 MB) y la descarga por bloques solo corren contra el cliente real de Google en la parte B.

## Decisiones e interpretaciones

D1 (OAuth de usuario con `drive.file` sobre la cuenta de pruebas, token con caducidad de 7 días, cambio a Workspace por configuración) y D2 (temporales transitorios permitidos) del 2026-10-17. Interpretación al implementar: los adaptadores `local` (carpeta) y `memoria` se conservan **solo** para desarrollo, regresión y pruebas, activados explícitamente con `ALMACENAMIENTO=local|memoria`; el predeterminado es `drive` y el piloto no guarda nada local. La spec hablaba de un adaptador en memoria para pruebas; el de carpeta local se añadió porque los smokes comparten el almacenamiento entre contenedores.

## Limitaciones previstas

La validación usa una cuenta de prueba y su cuota gratuita; la disponibilidad depende de Drive y del token; una aplicación de Google sin verificar muestra advertencias de consentimiento; el respaldo y la restauración son de C10; el móvil físico y el hospedaje no se validan.

## Acta de cierre

La segunda revisión técnica (tras corregir M1 y M2) concluyó APPROVED el 2026-10-17 sin defectos materiales; en ella se verificó además la suite con `ALMACENAMIENTO=drive` forzado (268/268). El responsable otorgó la aprobación de cierre con `CLOSE C10A` sabiendo que la prueba contra Drive real seguía pendiente. Ese mismo día se ejecutó (ver «Prueba con Drive real») y el responsable reiteró la aprobación de cierre con `CLOSE C10a + NEXT SPEC` tras una revisión APPROVED que incluyó el PDF firmado desde Drive. C10A queda DONE con las limitaciones anteriores. El commit local de implementación se hizo con el primer cierre; este registro posterior no se ha confirmado en commit (no se ordenó) y no hay push.
