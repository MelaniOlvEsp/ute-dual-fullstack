# C10A — Almacenamiento en Drive

Estado: DONE
Cierre: 2026-10-17
Fecha: 2026-10-17
Responsable de aprobación: responsable del proyecto
Dependencias: C09 DONE (2026-10-17). Decisión del responsable del 2026-10-17: los archivos y los respaldos viven en Drive y no se guarda nada de forma local; la base de datos sigue corriendo en Docker en el equipo (Drive no puede alojarla); se usa una cuenta de Google de prueba y el correo de la universidad solo para usuarios de prueba del sistema. Esto sustituye la decisión de almacenamiento local del piloto de DP-08. D1 y D2 resueltas por el responsable el 2026-10-17 (ver Decisiones); DRAFT → READY → IN_PROGRESS el 2026-10-17 con la orden `IMPLEMENT C10A`.

## Problema y resultado esperado

Los documentos privados se guardan hoy en el volumen local `dual-uploads` (DP-08, ADR-03): los originales y firmados de los reportes (`dual_reports`), la plantilla común (`plantillas`), los ZIP temporales de los paquetes (`paquetes`) y la eliminación de la depuración de C08B tocan el disco directamente por ruta. Existe un adaptador de Drive heredado (`integrations/drive.py` con `google_auth.py`) pensado para la demo: usa una carpeta fija, identifica archivos por ID de Drive guardado como puntero, nunca se probó con los documentos versionados y depende de un archivo de credenciales que el equipo no maneja desde C01. El responsable no quiere conservar archivos locales.

Resultado esperado: todo acceso a un documento pasa por un contrato de almacenamiento privado (guardar, leer, eliminar y comprobar) con un adaptador de Drive probado con una cuenta real de prueba; los originales, los firmados, las plantillas y los respaldos (C10) viven en una carpeta privada de Drive; la base conserva la clave, el tamaño y el SHA-256 de cada documento como fuente de verdad de la integridad; un fallo de Drive falla la operación con un error claro y no deja rastro ni cae a disco local; y los smokes C01 a C09 siguen pasando con Drive como almacenamiento.

## Fuentes y alcance

- RN/AC: [RN-12, RN-16 y RN-25](../../docs/analysis/REGLAS_DE_NEGOCIO.md), [AC-10, AC-11 y AC-24](../../docs/analysis/CRITERIOS_DE_ACEPTACION.md).
- Documentos enlazados: [plan maestro](../../docs/construction/PLAN_MAESTRO.md), [ADR-03 (archivos privados y almacenamiento intercambiable)](../../docs/analysis/DECISIONES_DE_ARQUITECTURA.md), [DP-08](../../docs/analysis/DECISIONES_PENDIENTES.md), [contrato de archivos](../../docs/analysis/CONTRATO_DE_ARCHIVOS_E_IMPORTACIONES.md), [modelo de datos (documentos)](../../docs/analysis/MODELO_DE_DATOS.md), [validación y operación local](../../docs/construction/VALIDACION_Y_OPERACION_LOCAL.md), [C05](../C05-entregas-y-versiones/spec.md), [C06](../C06-revision-y-firma/spec.md), [C08](../C08-expediente-y-visor/spec.md), [C08B](../C08B-archivo-y-depuracion/spec.md), [C09](../C09-foro-buzon-y-plantillas/spec.md).

Incluye:

1. Contrato de almacenamiento privado (ADR-03): operaciones guardar, leer, eliminar de forma definitiva y comprobar existencia sobre claves generadas por el servidor, sin exponer rutas, IDs de Drive ni URL públicas fuera del adaptador; los casos de uso solo ven el contrato.
2. Adaptador de Drive: carpeta raíz privada configurada por variable de entorno con subcarpetas por tipo (documentos de reportes, plantillas, respaldos), un archivo de Drive por documento nombrado con su clave y con la clave, el tipo y el SHA-256 como propiedades de la aplicación; subida con comprobación del tamaño y de la suma MD5 que devuelve Drive; lectura que verifica el SHA-256 contra la base antes de entregar el archivo; eliminación definitiva (no a la papelera) para que la depuración de C08B elimine de verdad; reintentos con espera exponencial y variación aleatoria ante 403 de cuota, 429 y 5xx, con un límite de intentos y de tiempo; sin la carpeta compartida con nadie.
3. Migración de los usos actuales al contrato sin cambiar sus reglas: guardado y lectura de originales y firmados (C05, C06), plantilla común (C09), paquetes ZIP de C08 (lectura de documentos desde Drive y archivo temporal transitorio según D2), depuración de C08B (eliminación en Drive, el «ausente cuenta como eliminado» se conserva) y limpieza de huérfanos por listado de la carpeta.
4. Conexión de la cuenta: una orden de autorización que guarda las credenciales en un archivo local de configuración excluido de git y nunca en el chat, el repositorio ni el registro; la API arranca sin Drive configurado solo en modo pruebas con un adaptador en memoria; en producción local, sin credenciales válidas la API responde con un error claro en las operaciones de archivos y `/health` lo informa sin exponer secretos.
5. Pruebas: unitarias con un adaptador en memoria (SIMULADA) y contra la cuenta de prueba real (REAL): subida, lectura con hash, eliminación definitiva, cuota y reintentos, fallo inyectado (credencial revocada, carpeta inexistente, red) y los smokes C01 a C09 ejecutados con Drive.
6. Contratos, documentación (DP-08, ADR-03, contrato de archivos, modelo de datos, operación) y la limpieza del adaptador heredado.

Excluye: respaldo y restauración (C10), hospedaje de la base de datos o de la aplicación, correo electrónico (el correo de la universidad solo identifica a usuarios de prueba), migración de archivos existentes (base nueva, ADR-09), cifrado propio de los archivos antes de subirlos, múltiples proveedores a la vez y el móvil físico.

## Decisiones

Confirmadas por el responsable el 2026-10-17: archivos y respaldos en Drive y nada guardado de forma local; la base de datos sigue en Docker en el equipo; una cuenta de Google de prueba conecta Drive; el correo de la universidad se usa solo para cuentas de prueba del sistema; las credenciales las coloca el responsable en un archivo local de configuración y nunca se pegan en el chat. Consecuencia aceptada: si Drive no responde, las operaciones con archivos fallan y no se guardan en disco.

Resueltas por el responsable el 2026-10-17:

- D1: se usa la cuenta personal de pruebas de Google con OAuth de usuario y el alcance `drive.file`, con la aplicación en modo de prueba y por tanto con el token de actualización caducando a los 7 días: el responsable vuelve a autorizar cuando caduque, solo para probar. Más adelante el responsable consultará con su profesor si la universidad dispone de una cuenta de Workspace o similar; si la hay, el cambio es de configuración (cuenta de servicio con una unidad compartida o delegación) sin tocar los casos de uso, porque el contrato de almacenamiento no depende de cómo se autentica el adaptador. Marcar la aplicación como publicada queda como opción si la caducidad estorba.
- D2: se admiten archivos temporales transitorios en el servidor durante la subida y el armado de un ZIP, siempre borrados al terminar; la prueba comprueba que no queda nada persistente.

Propuestas técnicas (sujetas a esas decisiones):

- Autenticación con OAuth de usuario (una cuenta personal no puede ser dueña de archivos mediante una cuenta de servicio sin una unidad compartida de Workspace) y alcance `drive.file`, que limita el acceso a los archivos que la propia aplicación crea. El token de actualización va en un archivo de configuración local ignorado por git; la autorización se hace con una orden explícita y se puede repetir. La autenticación queda detrás de una función de credenciales del adaptador para poder cambiar a una cuenta de servicio con unidad compartida (con `supportsAllDrives`) sin cambiar los casos de uso.
- Aplicación en modo de prueba (D1): el token de actualización caduca a los 7 días; el adaptador distingue «token caducado o revocado» con un error propio, `/health` lo informa sin exponer secretos y la guía explica cómo volver a autorizar con una orden. Las pruebas reales de C10A y C10 se hacen dentro de una ventana de 7 días tras autorizar. No se almacena la clave en el repositorio ni en el registro.
- Contrato sin `ruta` y sin identificador de Drive hacia fuera: `guardar(clave, bytes) → {tamano, sha256}`, `leer(clave) → bytes` con verificación del SHA-256 contra el valor de la base, `eliminar(clave)` idempotente y `existe(clave)`; la traducción de clave a archivo de Drive la mantiene el adaptador (consulta por nombre dentro de la carpeta y caché solo en memoria).
- Armado de los ZIP: se descargan los documentos de uno en uno a un archivo temporal que se elimina siempre, con el mismo límite de memoria actual; los respaldos de C10 usan el mismo contrato con otra subcarpeta.
- Cuota y límites: el piloto usa la cuota gratuita de la cuenta (la cuota de almacenamiento y los límites de peticiones se consultan al implementar con la documentación vigente; las cifras varían entre fuentes) y registra el uso en la guía de operación.

### Referencias de buenas prácticas consultadas

Consultadas el 2026-10-17 (foros, documentación de productos y blogs; contrastar con la documentación oficial de Google al implementar):

- [Una cuenta de servicio no tiene cuota de almacenamiento y no puede ser dueña de archivos (Fivetran)](https://fivetran.com/docs/activations/destinations/available-destinations/google-drive/troubleshooting/service-accounts-storage-quota), [error 403 storageQuotaExceeded con una cuenta de servicio (foro de Google)](https://discuss.google.dev/t/error-403-storagequotaexceeded-when-the-service-accounts-drive-is-completely-empty/194265) y [límites de almacenamiento y subida de Workspace](https://knowledge.workspace.google.com/admin/drive/storage-and-upload-limits-for-google-workspace?hl=cs): las cuentas de servicio solo escriben en unidades compartidas o con delegación; para una cuenta personal se usa OAuth en nombre del usuario.
- [Caducidad de 7 días del token de actualización en modo de prueba (Unipile)](https://www.unipile.com/google-oauth-refresh-token/) y [los tokens de prueba de Google OAuth caducan cada semana](https://newscrewdriver.com/2023/02/04/google-oauth-test-tokens-expire-weekly/): pasar a producción quita la caducidad semanal, hay un tope de tokens vivos por cuenta y cliente y un flujo de reconexión no debe emitir un token nuevo en cada clic. Las fuentes discrepan en los detalles: verificar con la documentación vigente.
- [Límites de uso de la API de Drive](https://developers.google.com/workspace/drive/api/guides/limits) y [cómo manejar los límites de tasa](https://folderpal.io/articles/how-to-handle-google-drive-api-rate-limits-for-bulk-folder-copying-and-automation): un exceso de cuota devuelve 403 y las comprobaciones adicionales 429; ambos se reintentan con espera exponencial y variación aleatoria (1, 2, 4 s…). Las cifras de cuota difieren entre versiones de la página: consultarlas al implementar. La búsqueda no devolvió nada sobre la carga reanudable, `md5Checksum` ni `appProperties`: leer la documentación oficial.

## Contratos y cambios

Propuesta mínima, a concretar al aprobar las decisiones:

- Variables de entorno de Drive (carpeta raíz y credenciales) en un archivo local ignorado por git y un ejemplo sin secretos en el repositorio; la orden de autorización y el retiro del archivo de credenciales heredado.
- Sin migración de esquema prevista: `documentos` conserva clave, tamaño y SHA-256 y la clave sigue siendo el nombre del archivo en Drive; el campo de proveedor del modelo de datos se documenta como «drive».
- Sin cambios de contrato HTTP: las descargas siguen siendo respuestas binarias autenticadas y ningún cliente recibe un ID de Drive ni una URL.

Permisos y estados: sin cambios en los roles; el acceso a Drive es solo del servidor.

## Verificación

| AC | Prueba o recorrido | Nivel y datos | Resultado |
|---|---|---|---|
| C10A-AC1 | Guardar, leer y eliminar de forma definitiva un documento en Drive: el contenido es idéntico byte a byte, el SHA-256 y el tamaño coinciden y tras eliminar no queda en Drive ni en la papelera | Cuenta de Drive de prueba real | Drive real NO_VERIFICADA (falta autorizar la cuenta de pruebas); contrato SIMULADA con el cliente real de Google sobre un transporte simulado y REAL con el adaptador local; `smoke_c10a.py` parte B lista para ejecutarse |
| C10A-AC2 | Una lectura cuyo contenido no coincide con el SHA-256 registrado se rechaza y nunca se entrega; un archivo ausente responde con un error claro | Fallos inyectados reales | REAL con el adaptador local de regresión y SIMULADA en pruebas unitarias (502 con otra huella; archivo ausente 404); con Drive real NO_VERIFICADA |
| C10A-AC3 | Drive no disponible, credencial revocada o cuota llena: la entrega, la revisión y la publicación fallan con un error claro y sin dejar filas ni archivos a medias, y no se escribe nada en disco | Fallos inyectados reales | REAL parcial: con ALMACENAMIENTO=drive sin autorizar, las entregas (smokes C05 a C08B) y la publicación de plantilla (`smoke_c10a.py`) responden 503 sin filas ni archivos y `/health` informa `sin_configurar`; token caducado, cuota y red SIMULADA |
| C10A-AC4 | Reintentos: un 403 de cuota o un 429 se reintenta con espera creciente y límite; un error permanente no se reintenta | Adaptador con respuestas simuladas | SIMULADA: 403 de cuota, 429 y 5xx con espera creciente y límite de intentos, errores permanentes sin reintento (401, cuota llena, carpeta), red y `RefreshError` en `test_c10a_almacenamiento.py` |
| C10A-AC5 | Los smokes C01 a C09 pasan con Drive como almacenamiento, incluidas la depuración (eliminación real) y los paquetes ZIP | HTTP + PostgreSQL + Drive reales | REAL con el adaptador local de regresión (smokes C01 a C09 y C08B PASS, incluidos depuración y paquetes ZIP); con Drive real NO_VERIFICADA |
| C10A-AC6 | Ningún secreto ni ID de Drive aparece en respuestas, registros, evidencias ni en el repositorio; el archivo local de credenciales está ignorado por git | Revisión de código y búsqueda de secretos | REAL parcial: `/health` solo expone `tipo` y `estado` (verificado en el smoke); `.secretos/` ignorada por git; sin secretos en respuestas de error; búsqueda de secretos con Drive autorizado NO_VERIFICADA |
| C10A-AC7 | Verificación de que no queda nada persistente en disco: la carpeta de documentos local está vacía tras los recorridos y los temporales se eliminan | Comprobación del sistema de archivos | SIMULADA y REAL parcial: con Drive sin autorizar no se escribe nada; los temporales del ZIP se eliminan (pruebas de C08); la comprobación con Drive autorizado está en `smoke_c10a.py` parte B (NO_VERIFICADA) |

## Evidencia de implementación

Implementación 2026-10-17 con Compose local; detalle en [evidencia.md](evidencia.md). Backend 268 pruebas OK (31 nuevas en `test_c10a_almacenamiento.py` y ajustes de las de C05, C06, C08, C08B y C09); contrato HTTP sin cambios (73 rutas); smokes C01 a C09 y C08B PASS con el adaptador local de regresión; `smoke_c10a.py` PASS (parte A). Entregado: contrato de almacenamiento y adaptadores (Drive, local de regresión y memoria), verificación del SHA-256 en cada lectura, eliminación definitiva, reintentos, falla cerrada con 503, `/health` con el estado del almacenamiento, orden de autorización de la cuenta de pruebas y retiro del adaptador de Drive heredado. **No se probó contra Drive real**: la cuenta de pruebas aún no está autorizada (C10A-AC1 y la parte real de AC2, AC5 y AC7 siguen NO_VERIFICADA). Revisada (APPROVED, segunda revisión tras corregir M1 y M2) y cerrada el 2026-10-17 con la prueba contra Drive real pendiente (ver Limitaciones).

## Revisión

Veredicto: APPROVED (segunda revisión técnica, 2026-10-17, tras corregir M1 y M2).
Revisor y modalidad: mismo agente; técnica (adaptador de Drive completo, configuración, scripts, contratos y evidencia); no hubo revisión visual porque la interfaz no cambió; no es revisión independiente.
Hallazgos materiales: la primera revisión (CHANGES_REQUESTED) encontró M1 (carrera al crear subcarpetas que dejaba archivos «perdidos») y M2 (un reintento de subida tras perder la respuesta duplicaba el archivo y `eliminar` dejaba una copia); corregidos con candado por espacio, elección de la carpeta más antigua, comprobación en cada intento de subida y borrado de todas las copias; la segunda revisión no encontró defectos materiales.
Correcciones y verificación focal: ver [evidencia](evidencia.md).
Limitaciones: **no se probó contra Drive real** (la cuenta de pruebas no estaba autorizada): C10A-AC1 y la parte real de AC2, AC5 y AC7 siguen NO_VERIFICADA y se ejecutan como primer paso de C10 (`scripts/smoke_c10a.py` parte B y los smokes C01 a C09 con Drive); la caducidad real del token a los 7 días, la cuota gratuita y los límites de peticiones solo se simularon; riesgo no descartado de consistencia lectura-tras-escritura de las consultas por nombre de Drive (si ocurre, guardar el identificador devuelto al subir); varias réplicas de la API solo simuladas; los adaptadores `local` y `memoria` quedan solo para desarrollo, regresión y pruebas; respaldo y restauración son de C10; móvil físico y hospedaje no se validan; una aplicación de Google sin verificar muestra advertencias de consentimiento.

## Aprobaciones y cierre

D1 y D2 aprobadas por el responsable el 2026-10-17 (D1 con la cuenta de pruebas y reautorización cada 7 días; D2 tal como se recomendó). Con `IMPLEMENT C10A` autorizó pasar a READY y a IN_PROGRESS el 2026-10-17.

Aprobación de cierre: el responsable otorgó la aprobación de cierre el 2026-10-17 con `CLOSE C10A`, tras la segunda revisión APPROVED y sabiendo que la prueba contra Drive real sigue pendiente. C10A queda DONE con las limitaciones anteriores; la verificación con Drive real pasa a ser el primer paso de C10. El commit local de implementación se hizo con el cierre; no hay push.
