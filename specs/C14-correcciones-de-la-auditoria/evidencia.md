# Evidencia C14 — Correcciones de la auditoría

Fecha: 2026-10-17. Entorno: Docker Compose local (PostgreSQL, API, web y contenedor `smoke`), almacenamiento en Drive real
con datos sintéticos (`ALMACENAMIENTO=drive`). Revisión del código: árbol de trabajo sobre `dev` (sin commit). Clases:
REAL (HTTP, PostgreSQL y Drive reales), SIMULADA (pruebas unitarias con dobles), NO_VERIFICADA.

## C14-AC1 — Limitador: REAL y SIMULADA

- `RateLimitMiddleware` devuelve un `JSONResponse` 429 con `Retry-After` y mensaje en español en lugar de lanzar la excepción
  (que Starlette convertía en 500 con traza). Clave según D1(b): usuario del token válido (240/min), IP solo para quien no trae
  sesión válida (120/min) y tope de respaldo por IP (1200/min); `/health` y `OPTIONS` quedan fuera. `X-Forwarded-For` solo se
  usa si la conexión viene de un proxy listado en `RATE_LIMIT_PROXIES` (por omisión vacío). Va como middleware más interno,
  así el 429 lleva las cabeceras de seguridad y de CORS.
- `tests/test_c14_limitador.py` (12 pruebas, SIMULADA): 429 con `Retry-After`, cabeceras de seguridad y CORS en el 429, usuarios
  independientes aunque compartan IP, tope de respaldo por IP, renovación de la ventana, `/health` exento, token inválido
  cuenta como anónimo, ráfaga solo con 200/429, lectura segura de `X-Forwarded-For`.
- REAL: 200 solicitudes anónimas desde una IP: 120 respuestas 401 y 80 respuestas 429 con `Retry-After`, ningún 500 ni traza
  (el registro deja un aviso por clave y ventana). Antes: 120 OK y 80 con 500. REAL: 40 alumnos sintéticos desde una sola IP
  (80 solicitudes en 15 s, ZIP y expediente) sin ningún 429.

## C14-AC2 — Dependencias y regresión: REAL

- Las 11 dependencias se actualizaron (D2 a) con el resolutor de pip; `pip-audit -r requirements.txt`: **No known vulnerabilities
  found** (antes: 87 vulnerabilidades en 11 paquetes). Se añadió `tzdata` porque la imagen `python:3.12-slim` no trae la zona
  `America/Mexico_City`.
- Regresión completa repetida al final, tras la última corrección del review (cierre/resumen, 2026-10-17 23:18 a 23:27): backend 321 pruebas OK (1 omitida), frontend 48/48, contrato 1/1, `vite build`
  OK y smokes C01, C02, C03, C04, C05, C06, C07, C08, C08B, C09, C10A y C10 en PASS con Drive real (reinicio de la API entre
  smokes por el límite de inicios de sesión).

## C14-AC3 — ZIP: REAL (carrera cumple; alumno cumple salvo paquetes grandes)

El armado lee los documentos con lecturas en paralelo (grupo de 16 hilos compartido y persistente, ventana de 16 documentos en
memoria, cada hilo conserva su cliente de Drive), verifica tamaño y SHA-256 de cada documento antes de añadirlo y escribe el ZIP
en orden desde un solo hilo; un documento faltante o alterado sigue abortando el paquete (409) y un fallo de Drive da 503.

| Medición (Drive real, 160 PDF, 49.6 MB) | Antes | Después |
|---|---|---|
| ZIP de la carrera, secuencial | 88.7 s (121.8 s en otra corrida) | — |
| 4 lectores | — | 39.9 s |
| 8 lectores | — | 33.2 s |
| 16 lectores, hilos de un grupo por paquete | — | 30.4 s |
| 16 lectores, grupo compartido y persistente | — | **20.2 a 21.3 s** (espera de lectura 19.5 s, verificación y escritura 1.4 s) |

ZIP del alumno con 16 peticiones simultáneas (40 alumnos, 80 solicitudes, REAL): antes p95 27.5 s; ahora p50 2.5 s y p95 11.8 s,
máximo 13.1 s. Los paquetes pequeños (documentos de unos KB) tardan 0.3 a 2.7 s; los cinco más lentos son los de alumnos con
el PDF de relleno de ~6 MB (12.3 MB por ZIP) que compiten por el ancho de banda de Drive (la bitácora `Paquete: …` muestra 11.7 a
12.9 s de espera de lectura). **El p95 < 10 s no se cumple con esos paquetes de 12 MB, pero no son representativos: el guion de carga añade un PDF de relleno de ~6 MB (original y firmado suman ~12 MB) a 1 de cada 10 alumnos para probar la subida grande, y el responsable indicó que su reporte más pesado pesa menos de 500 KB. D4 resuelta el 2026-10-17: la meta aplica a tamaño real y se cumple (0.3 a 2.7 s)**. Es el límite de la conexión con Drive de este equipo, no del código (la parte de verificación y escritura es de
decenas de milisegundos); no se afinó más (una cola de trabajos en segundo plano queda excluida por la spec).

`tests/test_c14_paquete_paralelo.py` (3 pruebas, SIMULADA con almacenamiento local): 25 documentos conservan orden y contenido
byte a byte; las lecturas se solapan y no superan el número de lectores; un documento faltante al final falla todo el paquete
con 409. Las pruebas existentes de C08 (contenido, manifiesto, hash alterado, nombres duplicados) siguen en verde. El manifiesto
y el CSV se arman antes y no cambian.

## C14-AC4 — Aprobar y firmar: REAL, causa documentada (no se reduce desde el código)

Se añadió una línea de bitácora por aprobación con el tiempo de cada etapa. Con 6 simultáneas (24 aprobaciones, dos corridas
sobre datos nuevos, Drive real):

| Etapa | p50 | p95 | máx |
|---|---|---|---|
| Leer el original de Drive | 0.38 s | 4.1 s | 4.4 s |
| Estampar la firma (CPU) | 0.01 s | 0.15 s | 0.15 s |
| Subir el firmado a Drive | 0.99 s | 4.5 s | 4.6 s |
| Registrar en PostgreSQL | 0.01 s | 0.03 s | 0.03 s |

Petición completa: p50 1.4 s, p95 7.4 a 8.6 s (antes p50 1.6 s, p95 9.3 s). El estampado y la base de datos son despreciables;
la cola viene de la latencia de Drive (lectura y subida), sin reintentos ni errores de cuota en la bitácora. **No se cumple
p95 < 4 s**; queda documentado con la medición. Posible mejora futura (no hecha): evitar la búsqueda duplicada que hace
`guardar` antes de `subir`.

## C14-AC5 — Obligaciones con inicio antiguo (D3 a): REAL y SIMULADA

Cambio: el alta con inicio anterior a 26 semanas ya no genera su historial al instante (`generar_al_alta`); `sincronizar`
lo crea acotado a `min(hoy, baja)` en la primera lectura de obligaciones o bandeja y en el cierre de recepción de un período
(`cerrar_recepcion` sincroniza primero). La baja sigue generando solo hasta la baja y nunca se borran filas. `finalizar_evaluacion`
no se toca (C07 exige que no modifique obligaciones). Tras la revisión, el resumen del período también sincroniza y `cerrar_recepcion` lo hace en una transacción propia **antes** del bloqueo exclusivo (si lo hiciera después, el upsert esperaría la fila que una entrega en curso ya tiene bloqueada mientras esa entrega espera al período: interbloqueo; deducido del orden de bloqueos, no reproducido). `tests/test_c14_cierre_sincroniza.py` (2 pruebas, SIMULADA) falla si se quita cualquiera de las dos sincronizaciones o si el cierre toca obligaciones tras el bloqueo; `test_c07_cierre` ajustada a ese orden.
El expediente y los paquetes no sincronizan: un alta retroactiva que nadie ha leído puede no aparecer en ellos hasta la primera
lectura de obligaciones. El grupo de lectores del ZIP es compartido y FIFO: un ZIP de carrera retrasa a los de alumnos mientras
dura (~20 s); no se midió la capacidad de respuesta tras ese cambio.

REAL (`scripts/auditoria/retroactiva.py`): alta con inicio el 2015-01-05 y baja el 2015-02-01 antes de la primera lectura:
alta 8 ms y 0 filas, baja 31 ms y 4 filas (última semana 2015-02-01), lectura 24 ms y 4 filas; ninguna posterior a la baja.
Antes: 14 180 filas en 4 s con inicio en 1755. `tests/test_c14_obligaciones_retroactivas.py` (4 pruebas, SIMULADA):
alta reciente genera al instante, alta retroactiva no genera nada, la creación posterior se acota a la baja, sin baja se
completa hasta hoy. `smoke_c04` (incluye «las semanas posteriores a la baja no se borran») sigue en PASS.

Limitación: si la baja se registra después de que una lectura ya creó el historial, esas filas posteriores a la baja se
conservan (decisión D3: no borrar).

## C14-AC6 — `smoke_c04.py`: REAL, causa encontrada (era del smoke)

Reproducido: 8 fallos en 50 ejecuciones seguidas (con reinicio de la API entre ellas por el límite de inicios de sesión) y, con
mensajes en las aserciones, tres causas, **todas del smoke y no del producto**: (1) el año sorteado para la prueba del 30 de
abril solo excluía que fuera domingo; cuando era lunes la semana de inicio no es parcial y la aserción fallaba (~1/7 de los
años, 8 de 50); (2) y (3) el año sorteado podía coincidir con el de una corrida anterior, cuyo período sintético persiste:
«Sin período hasta que exista» y `UniqueViolation` en `ciclos_dual` (aumenta con el estado acumulado). Corrección: excluir lunes
y domingo, y elegir años que no estén en `ciclos_dual`. Todas las aserciones llevan mensaje con los valores observados.
Resultado tras la corrección: **50 PASS de 50** consecutivos (y el estado de todas las corridas anteriores acumulado), repetido
al final con el código definitivo de cierre/resumen (50 de 50 otra vez). La
parte de concurrencia de obligaciones no falló en ninguna de las ~150 corridas hechas; la falla original de la auditoría (sin
mensaje, 1 de 11) no se puede atribuir con certeza, pero la tasa observada de la causa 1 (~1/7) la explica sin necesidad de una
condición de carrera del producto.

## C14-AC7 — Guiones en el repositorio: REAL

`ute-api-backend/scripts/auditoria/` (`comun.py`, `rutas.py`, `carga.py`, `retroactiva.py` y `README.md`) se ejecutan en el
contenedor `smoke`. `rutas.py` se ejecutó completo desde el repositorio tras moverlo: 74 operaciones de OpenAPI × anónimo,
alumno, tutor y coordinador y 96 cargas malformadas, **0 hallazgos y ningún 5xx** (latencias p95 de 10 a 57 ms por rol). `retroactiva.py`
y `carga.py` (`setup`, `alumnos`, `revisar`, `lecturas`, `paquete`) se ejecutaron desde la imagen construida con el repositorio para las
mediciones de arriba. El estado vive en `AUDITORIA_DIR` (por omisión
`/tmp/auditoria`; `.auditoria-tmp/` está en `.gitignore`).

## Limitaciones

- Las mediciones dependen de la latencia de Drive y del ancho de banda de este equipo; la carga sale de una sola máquina.
- ZIP de alumno: cumple con reportes de tamaño real (< 500 KB, 0.3 a 2.7 s); los paquetes sintéticos de ~12 MB dieron p95 11.8 s (D4,
  no representativos). Aprobar y firmar p95 ~8 s (objetivo 4 s no cumplido, AC4 lo admite con la causa documentada): dominado por Drive.
- Los pendientes del hospedaje (`/docs`, imagen web de producción, política de seguridad de contenido) no se tratan aquí.
- Sin móvil físico ni integraciones externas distintas de Drive: NO_VERIFICADAS.
