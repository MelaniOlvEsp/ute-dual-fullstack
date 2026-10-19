# C14 — Correcciones de la auditoría

Estado: DONE (2026-10-18)
Fecha: 2026-10-17
Responsable de aprobación: responsable del proyecto
Dependencias: C13 DONE (2026-10-17). D1, D2 y D3 resueltas el 2026-10-17 (tal como se recomendó); implementada el mismo día con `IMPLEMENT C14` y pendiente de revisión y cierre. Es una spec de corrección de lo que encontró la auditoría completa del 2026-10-17 (regresión, recorrido de todas las rutas por rol, simulación con 40 alumnos y pruebas de carga); no agrega funciones de producto.

## Problema y resultado esperado

La auditoría confirmó que el sistema hace lo que debe (74 operaciones sin 5xx ni fugas de permisos; 40 alumnos con 80 entregas aprobadas, cierre y finalización con promedios correctos; 160 documentos íntegros en Drive), y encontró siete cosas que conviene corregir antes de usar el piloto con más gente o con datos reales:

1. **El limitador de solicitudes responde 500 en lugar de 429.** `RateLimitMiddleware` ([security.py](../../ute-api-backend/app/presentation/middleware/security.py)) lanza `HTTPException(429)` dentro de un `BaseHTTPMiddleware`; ese tipo de excepción no la convierte la aplicación en respuesta y el cliente recibe `{"detail":"Internal server error"}` con una traza en el registro (200 `GET /health` en 1 s: 120 OK y 80 con 500). Además el límite de 120 solicitudes por minuto **por IP** es bajo: una clase de 40 alumnos detrás de una misma IP se repartiría 3 solicitudes por minuto cada uno.
2. **87 vulnerabilidades conocidas en 11 dependencias** de `requirements.txt` según `pip-audit` (starlette, pyjwt, python-multipart, pillow, cryptography, urllib3, anyio, idna, httplib2, oauthlib y pyasn1), con versiones corregidas disponibles. Varias están en la ruta de peticiones y de carga de archivos.
3. **Los paquetes ZIP son lentos:** el de una carrera con 160 PDF tardó entre 90 y 120 s (lecturas secuenciales de Drive, unos 0.6 a 0.8 s por archivo) y el de un alumno llegó a 27 s con 16 peticiones simultáneas. Con más alumnos supera cualquier tiempo de espera razonable del navegador o de un intermediario.
4. **Aprobar y firmar tiene una cola larga:** con 6 revisiones simultáneas, p50 1.6 s pero hasta 14 s (p95 9.3 s).
5. **Una fecha de inicio muy antigua crea miles de obligaciones:** registrar una incorporación con inicio en 1755 creó 14 180 obligaciones por alumno y tardó 4 s (la base de desarrollo ya tiene 1.6 millones de filas, 370 MB). Un error de captura del tutor (por ejemplo el año 2005 en vez de 2025) tendría el mismo efecto en pequeño; la baja posterior no elimina las filas ya creadas.
6. **`smoke_c04.py` falló una de 11 ejecuciones** con un `AssertionError` sin mensaje en la parte de concurrencia de obligaciones; no se reprodujo en 10 repeticiones. Puede ser una condición de carrera real o la dependencia del estado que deja el smoke anterior.
7. **Pendientes del hospedaje** (`/docs` expuesto, imagen web que corre el servidor de desarrollo de Vite como root, sin política de seguridad de contenido): se registran, pero no se tratan aquí.

Resultado esperado: el límite responde 429 con `Retry-After` y se reparte de forma razonable; las dependencias actualizadas sin vulnerabilidades conocidas y con todas las pruebas en verde; el ZIP de una carrera de 160 PDF en menos de 30 s y el de un alumno en menos de 10 s bajo la misma carga; la cola de aprobación explicada y reducida si es del código; las obligaciones acotadas; y el smoke intermitente reproducido y corregido o explicado.

## Fuentes y alcance

US/RN/AC: sin AC nuevos del producto; RN-25 y RN-29 (archivos y conservación) y las reglas de calendario de [C04](../C04-calendario-y-pendientes/spec.md) para el punto 5.
Documentos enlazados: [plan maestro](../../docs/construction/PLAN_MAESTRO.md), [guía de uso y operación](../../docs/construction/GUIA_DE_USO_Y_OPERACION.md), [evidencia C10](../C10-validacion-integral-local/evidencia.md), [CONTRATO_API](../../docs/analysis/CONTRATO_API.md), [DECISIONES_PENDIENTES](../../docs/analysis/DECISIONES_PENDIENTES.md).

Incluye:

1. **Limitador:** el middleware devuelve una respuesta 429 (`Retry-After` y mensaje en español) en vez de lanzar la excepción; el límite y su clave según D1; las respuestas 429 se cuentan y no producen trazas; el limitador de inicio de sesión y el bloqueo por cuenta de C02 no cambian.
2. **Dependencias:** actualizar los pins de las 11 dependencias a las versiones corregidas (según D2), repetir `pip-audit` y la regresión completa (backend, frontend, contrato y los smokes con Drive); si una actualización rompe algo, fijarla al paso anterior con el motivo.
3. **Paquetes ZIP:** leer los documentos de Drive con un número acotado de lecturas en paralelo (conservando la verificación de SHA-256, el orden del ZIP y el manifiesto idéntico) y medir antes y después; sin cambios del contrato de la API.
4. **Aprobar y firmar:** medir dónde está la cola (lectura del original, estampado de la firma, subida del firmado a Drive, bloqueos de la base) y reducirla si es del código; si es el rendimiento de Drive con esa concurrencia, documentarlo con la medición.
5. **Obligaciones:** acotar su creación según D3.
6. **`smoke_c04.py`:** reproducirlo (repeticiones y con el estado del smoke anterior), añadir mensajes a las aserciones y corregir la causa si es del producto.
7. **Herramientas de la auditoría:** guardar en el repositorio los guiones de carga y de auditoría de rutas (`scripts/auditoria/`) con una guía breve, para repetirlas.

Excluye: los pendientes del hospedaje (punto 7 del problema), nuevas funciones, cambios de interfaz, cambios del contrato de la API, cola de trabajos en segundo plano para los ZIP (se evalúa solo si la lectura en paralelo no alcanza) y la migración a otro almacenamiento.

## Decisiones

Confirmadas: ninguna corrección cambia permisos, datos ni reglas de negocio ya aprobadas; las mediciones se hacen con datos sintéticos y con Drive real, antes y después; cada corrección se prueba con una prueba que habría fallado sin ella.

Resueltas por el responsable el 2026-10-17, tal como se recomendó (D1: opción b, límite por usuario con respaldo por IP; D2: opción a, actualizar las 11 dependencias con la regresión completa; D3: opción a, acotar la creación de obligaciones a `min(hoy, baja)`). Se conserva el texto de las opciones:

- **D1 — Límite de solicitudes.** El límite actual (120 por minuto y por IP) es bajo y la IP no distingue usuarios (una clase detrás de una IP, o un servicio detrás de un proxy). Opciones: (a) subir el límite por IP (por ejemplo a 600 por minuto) y dejar la clave como está; (b) clave mixta: por **usuario** (el identificador del token válido) con un límite generoso (por ejemplo 240 por minuto) y por **IP** solo para las solicitudes sin sesión (por ejemplo 120 por minuto) más un tope general por IP alto como respaldo (por ejemplo 1200); (c) mantener todo y solo corregir el 429. La IP detrás de un proxy solo se toma de la cabecera `X-Forwarded-For` si se configura explícitamente (apagado por defecto). Recomendación: (b), porque no depende de cuántas personas compartan una IP y conserva la protección contra el abuso anónimo; los valores se ajustan con la medición de la auditoría.
- **D2 — Alcance de la actualización de dependencias.** Opciones: (a) actualizar las 11 dependencias a la última versión corregida en este incremento, con la regresión completa; (b) actualizar solo las que están en la ruta de peticiones y de carga de archivos (starlette, pyjwt, python-multipart, pillow) y dejar el resto para después; (c) actualizar solo hasta la versión que corrige cada aviso, sin saltar de versión mayor. Recomendación: (a) con la salvedad de (c) para cualquier paquete que cambie de versión mayor y rompa pruebas, que se fija con el motivo anotado.
- **D3 — Obligaciones de una incorporación con inicio muy antiguo.** Las obligaciones se crean desde la fecha de inicio hasta hoy, sin tope y sin considerar la baja registrada después. Es una regla de calendario (afecta qué semanas existen), por eso se decide antes de implementarla. Opciones: (a) **acotar la creación** a `min(hoy, fecha de baja)` y no crear filas más allá de la baja, sin tocar las existentes ni rechazar fechas; (b) **validar** la fecha de inicio (no anterior a 24 meses antes de hoy ni posterior a 12 meses después) y rechazar con un mensaje claro (obliga a que los smokes creen sus períodos pasados de otra forma); (c) las dos. Recomendación: (a) porque no cambia qué fechas acepta el producto ni rompe los períodos pasados de las pruebas, y es suficiente para evitar las miles de filas cuando la baja ya existe; si el responsable quiere además proteger el error de captura sin baja, (c) con la ventana indicada.

Propuestas técnicas incluidas en esta aprobación (sujetas a D1 a D3): el 429 como `JSONResponse` con `Retry-After` desde el middleware (sin excepciones no manejadas); contador por clave con limpieza periódica; lecturas de Drive con un `ThreadPoolExecutor` acotado (4 a 8 hilos) en el armado del ZIP, verificando el SHA-256 de cada documento antes de añadirlo; instrumentación de tiempos por etapa en la aprobación; los guiones de la auditoría como parte del repositorio.

### Referencias de buenas prácticas consultadas

Consultadas el 2026-10-17 (guías y fragmentos de terceros; criterio de diseño, no norma; lo específico de Starlette se confirma contra su documentación y con una prueba al implementar):

- [Ejemplos de middleware de limitación de tasa con Starlette](https://www.resumelens.org/blog/fastapi/implementing-rate-limiting-in-fastapi-using-starlette-middleware) y [fastapi-traffic](https://homelabgitea.duckdns.org/zanewalker/fastapi-traffic/src/tag/v0.3.1/fastapi_traffic/middleware.py): la alternativa a lanzar la excepción es devolver directamente una respuesta JSON con el código y las cabeceras de reintento; [slowapi](https://openapps.pro/packages/slowapi) se integra con el manejo de excepciones de Starlette. La búsqueda no explicó por qué la excepción da 500; es coherente con que `BaseHTTPMiddleware` queda fuera del manejador de excepciones de FastAPI y es lo que se observó en la auditoría.
- [Qué es el 429 y cómo usar `Retry-After`](https://pulsetic.com/errors/429-too-many-requests/) y [límites por usuario o por IP detrás de NAT](https://docs.gotosocial.org/en/latest/api/ratelimiting/): `Retry-After` se envía en segundos o fecha, el 429 no se guarda en caché (RFC 6585), la limitación por IP es poco precisa cuando una IP representa a muchas personas y el compromiso habitual es por usuario autenticado más un respaldo por IP; detrás de un proxy solo se confía en `X-Forwarded-For` si se configura la lista de proxies. La búsqueda no cubrió cómo leer la cabecera de forma segura; se resuelve al implementar.
- [pip-audit](https://pypi.org/project/pip-audit/): audita las dependencias fijadas contra bases de avisos públicas; se usa como comprobación antes y después de actualizar.

## Contratos y cambios

Métodos/rutas/DTO y compatibilidad: sin cambios de rutas ni de contrato (73 rutas); la respuesta 429 pasa a ser un 429 real con `Retry-After` y un mensaje en español (el contrato lo describe como respuesta posible); los fixtures y el contrato estático no cambian salvo esa descripción.
Datos, restricciones y conservación: sin cambios de esquema; las obligaciones existentes se conservan (D3); los ZIP y el registro de paquetes no cambian de contenido.
Permisos y estados: sin cambios.
Archivos/módulos previstos: `app/presentation/middleware/security.py` y `app/main.py` (limitador); `requirements.txt` y su origen; `app/infrastructure/documents/paquetes.py` (armado del ZIP); el caso de uso de revisión (`revisiones.py`) y las consultas de incorporación y obligaciones (según D3); `scripts/smoke_c04.py`; `scripts/auditoria/` (guiones nuevos); pruebas nuevas en `tests/`.
Comportamiento ante fallos/reintentos: un fallo de lectura de Drive en el ZIP sigue abortando el paquete con el mismo error (409/503); el limitador no cambia el comportamiento de los demás errores.

## Verificación

| AC | Prueba o recorrido | Nivel y datos | Resultado |
|---|---|---|---|
| C14-AC1 | Al pasar el límite la API responde 429 con `Retry-After`, sin traza en el registro; 200 `GET /health` desde una IP ya no producen 500; con la clave de D1, 40 usuarios sintéticos desde una sola IP no se limitan entre sí | HTTP real y pruebas unitarias del middleware | REAL: 200 solicitudes anónimas → 120×401 y 80×429 con `Retry-After`, sin 500 ni traza; 40 alumnos desde una IP sin 429. SIMULADA: 12 pruebas del middleware |
| C14-AC2 | `pip-audit` sin vulnerabilidades conocidas (o con las excepciones justificadas por escrito); regresión completa: backend, frontend, contrato y smokes C01 a C10 con Drive | Pruebas y smokes reales | REAL: `pip-audit` sin vulnerabilidades (antes 87); backend 319, frontend 48/48, contrato 1/1, `vite build` y smokes C01–C10A en PASS con Drive |
| C14-AC3 | El ZIP de una carrera con 160 PDF en menos de 30 s y el de un alumno en menos de 10 s con 16 peticiones simultáneas; contenido, orden, manifiesto y SHA-256 idénticos a los de antes; sin pérdida de verificación | Drive real, datos sintéticos, antes y después | REAL: carrera 88.7 s → 20.2 a 21.3 s (cumple). Alumno con 16 simultáneas: p95 27.5 s → 11.8 s (el p95 sube por los alumnos sintéticos con un PDF de relleno de ~6 MB, paquete de ~12 MB, que el guion de carga añade a 1 de cada 10 para probar la subida grande; el responsable indicó que su reporte más pesado es menor de 500 KB. Con tamaño real los paquetes tardan 0.3 a 2.7 s). **D4 resuelta por el responsable (2026-10-17): la meta de 10 s aplica a reportes de tamaño real (< 500 KB); queda cumplida en ese caso.** SIMULADA: 3 pruebas de orden, contenido, solape y fallo; sin cambios en el manifiesto ni en la verificación de SHA-256 |
| C14-AC4 | Medición por etapa de aprobar y firmar con 6 simultáneas; p95 por debajo de 4 s o la causa documentada con la medición | Drive real | REAL: p95 de la petición 7.4 a 8.6 s (no cumple 4 s); por etapa, leer 0.38 s p50 / 4.1 s p95, estampar 0.01 s, subir 0.99 s p50 / 4.5 s p95, registrar 0.01 s: la cola es la latencia de Drive, documentada |
| C14-AC5 | Una incorporación con inicio antiguo y una baja registrada no crea obligaciones más allá de la baja ni tarda más de 1 s; las filas existentes se conservan (según D3) | HTTP y PostgreSQL reales | REAL: inicio 2015-01-05 y baja 2015-02-01: alta 8 ms y 0 filas, baja 31 ms y 4 filas, ninguna posterior a la baja (antes 14 180 filas en 4 s). SIMULADA: 4 pruebas. Se conservan las filas existentes |
| C14-AC6 | `smoke_c04.py` reproducido o descartado con 50 ejecuciones seguidas y con el estado del smoke anterior; las aserciones con mensaje | Smokes reales | REAL: reproducido (8 fallos de 50), causa en el smoke (año con lunes el 30 de abril y años ya ocupados por corridas anteriores); corregido y con mensajes: 50 PASS de 50 |
| C14-AC7 | Los guiones de auditoría y de carga se ejecutan desde el repositorio con la guía | Ejecución real | REAL: `scripts/auditoria/` con README; `rutas.py` (74 operaciones × 4 roles + 96 cargas malformadas: 0 hallazgos, ningún 5xx), `retroactiva.py` y `carga.py` ejecutados desde la imagen del repositorio |

## Evidencia de implementación

Implementado el 2026-10-17; detalle, mediciones antes y después y limitaciones en [evidencia.md](evidencia.md). Resumen: los siete puntos corregidos o explicados; los objetivos de tiempo de AC3 (ZIP de alumno con paquetes de 12 MB: p95 11.8 s) y AC4 (aprobar y firmar p95 ~8 s) no se cumplen y su causa medida es la latencia de Drive. Línea base de la auditoría (2026-10-17, solo como referencia): ZIP de carrera 88.7 a 121.8 s (160 PDF, 49.6 MB), ZIP de alumno p50 3.3 s y p95 27.5 s (16 simultáneos), aprobar y firmar p50 1.6 s y p95 9.3 s (6 simultáneos), entrega p50 1.05 s y de ~6 MB 7.7 s, 14 180 obligaciones y 4 s por incorporación con inicio en 1755, 87 vulnerabilidades en 11 dependencias.

## Revisión

Veredicto: APPROVED tras FIX (revisión técnica; sin cambios de interfaz ni de PDF, por lo que no hubo revisión visual).
Revisor y modalidad (mismo agente / independiente): mismo agente, tres pasadas (dos de revisión y una focal tras el FIX).
Hallazgos materiales: (1) interbloqueo posible entre el cierre y una entrega al sincronizar obligaciones con el período bloqueado; (2) evidencia de regresión anterior a los últimos cambios; (3) sin pruebas que fallaran sin la sincronización del resumen y del cierre; (4) meta del ZIP de alumno con paquetes de 12 MB.
Correcciones y verificación focal: sincronización del cierre en transacción propia antes del bloqueo, sincronización en el resumen, `test_c14_cierre_sincroniza.py` (falla al quitar la corrección, comprobado por mutación), `test_c07_cierre` ajustada, regresión completa repetida (backend 321, frontend 48/48, contrato, build, smokes C01–C10A con Drive) y `smoke_c04` 50 de 50. El hallazgo 4 se resolvió con D4: los 12 MB eran el relleno del guion de carga; con reportes reales (< 500 KB) el ZIP tarda 0.3 a 2.7 s.
Limitaciones: el interbloqueo se dedujo del orden de bloqueos y no se reprodujo; aprobar y firmar queda en p95 de ~8 s (meta 4 s, admitido con la causa documentada: latencia de Drive); el expediente y los paquetes no sincronizan obligaciones; el reparto de lecturas del ZIP es FIFO. Las mediciones dependen de la latencia de Drive y de la cuenta de pruebas; la carga se genera desde pocas IP y no sustituye a una prueba con usuarios reales; los pendientes del hospedaje quedan fuera.

## Aprobaciones y cierre

Aprobación de implementación: D1, D2 y D3 resueltas el 2026-10-17; el responsable autorizó la implementación con `IMPLEMENT C14` el 2026-10-17: sin decisiones bloqueantes, la spec pasó de DRAFT a READY y a IN_PROGRESS el mismo día. Sin commit ni push.
Aprobación de cierre: el responsable ordenó el cierre ("cierrala") el 2026-10-18; D4 resuelta el 2026-10-17 (meta del ZIP de alumno aplicada a reportes de tamaño real).
Resumen final: limitador con 429 y `Retry-After` por usuario con respaldo por IP, 11 dependencias actualizadas (`pip-audit` limpio, antes 87), ZIP de carrera de 88.7 s a ~21 s con lecturas en paralelo, aprobación instrumentada por etapa, creación de obligaciones acotada para altas retroactivas, `smoke_c04` corregido (50 de 50) y guiones de auditoría en `scripts/auditoria/`. Evidencia en [evidencia.md](evidencia.md).
Siguiente spec: los pendientes del hospedaje (`/docs`, imagen web de producción, política de seguridad de contenido), el aviso de privacidad y la cuenta de Workspace no están en el plan maestro; se tratan cuando el responsable decida publicar.
Commit/push: no autorizados salvo indicación explícita.
