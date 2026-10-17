# Archivos e importaciones

## Reporte semanal

PDF firmado y calificado por empresa. Campos: obligación semanal, inicio/fin declarados y nota entera 1–10. Tutor verifica visualmente correspondencia; no hay firma empresarial electrónica ni OCR automático.

Implementado en C05 (DP-08, 2026-10-15): límite único de 10 MB en cliente y API (antes 2 MB y 10 MB), leído en bloques con corte al exceder (413). La API rechaza con 422 y mensaje claro: extensión distinta de `.pdf`, archivo vacío, cabecera `%PDF-` ausente, PDF dañado o incompleto (incluido el que requiere reparación), PDF sin páginas, con contraseña o cifrado, o cuya primera página no se pueda leer. No confía solo en el nombre ni en la cabecera. Una entrega rechazada no deja documento, reporte ni archivo.

Conservar original; firma académica produce derivado. Claves de almacenamiento generadas por servidor y fuera del directorio público. No usar matrícula/ruta aportada por cliente para escribir archivos arbitrarios. No comprimir destructivamente evidencia.

Implementado en C05 y trasladado a Drive en C10A (decisión del 2026-10-17: los archivos y los respaldos del piloto viven en Drive y no se guarda nada local): almacenamiento privado con clave `<uuid>.pdf` generada por el servidor, hash SHA-256, tamaño y páginas en `documentos`; el original se guarda byte a byte (sin recompresión) con escritura atómica y nunca sobrescribe. Si la transacción falla se elimina solo el archivo recién guardado; los archivos sin fila de `documentos` se limpian por referencia y antigüedad (`limpiar_huerfanos`). Contrato de almacenamiento (C10A): los casos de uso solo ven guardar, leer, eliminar de forma definitiva, comprobar y listar sobre claves del servidor, separadas por espacio (`documentos`, `plantillas`, `respaldos`); ninguna ruta, identificador de Drive ni URL sale del adaptador. Adaptador de Drive (`app/infrastructure/storage/drive.py`): una carpeta raíz privada creada por la propia aplicación (alcance `drive.file`) con una subcarpeta por espacio y un archivo por clave, con el SHA-256 como propiedad de la aplicación; la subida comprueba el tamaño y el MD5 que devuelve Drive (si no coinciden elimina lo subido y falla), la subida de más de 5 MB es reanudable, un reintento tras un tiempo de espera es idempotente y las claves son de solo escritura; la eliminación es definitiva (`files.delete`, no la papelera); los 403 de cuota (`rateLimitExceeded`, `userRateLimitExceeded`), 429 y 5xx se reintentan con espera exponencial y variación aleatoria (hasta 5 intentos) y el resto de errores no se reintenta. Las lecturas verifican el SHA-256 registrado en la base: un contenido distinto responde 502 y nunca se entrega. Falla cerrada: sin Drive disponible las operaciones con archivos responden 503 sin dejar filas ni archivos y no se escribe nada en disco; `/health` informa `almacenamiento` con solo `tipo` y `estado` (`ok`, `sin_configurar`, `token_caducado`, `cuota`, `carpeta`, `red` o `no_disponible`). Los únicos archivos en disco son temporales transitorios (por ejemplo el ZIP de un paquete) que se eliminan siempre (D2). Los adaptadores `local` (carpeta, solo para desarrollo y regresión con `ALMACENAMIENTO=local`) y `memoria` (pruebas unitarias) no se usan en el piloto. La columna heredada `reportes_dual.archivo_pdf_local` ya no se escribe (NULL) y ningún código la lee; el adaptador y el código de Drive heredados se retiraron.

## Firma académica

Imagen PNG/JPEG de tutor propietario. Propuesta límite 1 MB coherente con SQL actual; validar dimensiones/contenido decodificable. La firma aplicada es una representación gráfica, no certificación criptográfica. El documento aprobado debe permanecer legible y conservar firma de empresa.

Ubicación (DP-07, resuelta el 2026-10-16): la firma se estampa en la celda vacía de la columna «Firma» en la fila «Tutor académico» de la tabla final del reporte. La celda se localiza por el texto de la fila, el encabezado de la columna y las líneas dibujadas de la tabla, en la última hoja que la contenga. Si no se reconoce el formato (por ejemplo un PDF escaneado), la celda está ocupada o la página está girada, se usa como respaldo una hoja adicional con la firma, el nombre y la fecha de revisión, y la revisión registra qué modo se usó. Se conserva el original y el firmado es un documento distinto; el estampado no cambia el texto del reporte. Se validó con una réplica sintética del formato (muestra en la spec C06) y con el reporte de ejemplo del responsable solo de forma local, sin copiarlo al repositorio. Cambio de firma futura no reescribe firmados anteriores.

## Plantilla común

Coordinador publica pareja Word (.docx) y PDF; ambos para las tres carreras. Archivos separados cargados por coordinador, sin conversión automática requerida. Versionar y publicar pareja completa; fallar uno mantiene la versión anterior. Rechazar formatos inesperados; no aceptar macros como requisito de V1. Tamaño Word/PDF en spec C09.

El alumno descarga la versión vigente; no exigirle reentregar un reporte histórico por cambiar plantilla. El Excel existente no forma parte del alcance confirmado.

Implementado en C09: el coordinador publica la pareja con `POST /dual/plantillas/` (multipart `word` y `pdf`, nota opcional). Se valida el contenido real: el PDF con el inspector de entregas (legible, sin cifrar, 10 MB máximo) y el DOCX como contenedor ZIP OOXML (firma `PK`, `[Content_Types].xml` y `word/document.xml`, tipo principal de documento sin macros, sin `vbaProject.bin`, sin rutas absolutas o con `..`, máximo 500 entradas, 100 MB descomprimidos y razón de compresión de 200 por entrada, 10 MB de archivo); el nombre del cliente se ignora y solo se contrasta la extensión. Los archivos se guardan con claves generadas por el servidor en una carpeta privada (`plantillas`), nunca públicos; la versión se inserta y pasa a ser la vigente en una sola transacción con bloqueo, y si algo falla se eliminan los archivos escritos. Todos los roles autenticados descargan por versión y tipo (`GET /dual/plantillas/{numero}/{word|pdf}`) con nombre generado `Plantilla_Reporte_Dual_v{n}.{docx|pdf}`; el historial (`GET /dual/plantillas/`) es del coordinador. Los archivos estáticos del frontend (`public/plantillas`) se retiraron; el Excel de asistencia queda fuera del sistema (DP-09 D3). Limitación: no se revisan relaciones externas ni objetos incrustados dentro del DOCX más allá de las macros.

## CSV de alumnos

Operación existente del tutor sobre grupo seleccionado. Propuesta de contrato:

- UTF-8, encabezados exactos matricula,nombre.
- Matrícula como texto, preservar ceros iniciales; nombre obligatorio.
- Grupo determinado por ruta/selección autorizada, no columna libre del CSV.
- Vista previa con filas válidas, repetidas y errores antes de aplicar.
- Matrícula repetida con nombre o grupo diferente no sobrescribe silenciosamente: resolver conflicto.
- Aplicación transaccional del lote validado; reintento no duplica alumnos.
- Límite propuesto 500 filas por lote; fijar en C03, no es requisito aprobado.
- Exportaciones protegen valores interpretables como fórmulas por hojas de cálculo.

La carga individual debe aplicar las mismas reglas y habilitar registro institucional. No inferir estado laboral por cargar matrícula.

## Descarga y visor

API autoriza cada documento. Frontend obtiene binario mediante sesión, construye URL temporal de objeto y la libera al cerrar; no incrustar JWT en URL. Mostrar carga, error y acción de reintentar/descargar. Verificar en navegador PDF de una y varias páginas, escaneado y firmado.

Implementado en C08: `VisorPDF` obtiene el documento con la sesión, crea una URL temporal que libera al cambiar o destruirse, ofrece siempre «Abrir en pestaña nueva» y «Descargar», muestra el error del servidor con «Reintentar» y, en pantallas táctiles estrechas, ofrece abrir o descargar antes de intentar incrustarlo. Un navegador sin visor PDF integrado deja el área en blanco: por eso las acciones de abrir y descargar son permanentes.

Paquete de archivo (C08, DP-14): ZIP por alumno o por carrera y período finalizado, solo para el tutor; el alumno descarga únicamente el suyo durante 7 días desde la finalización. Contiene `manifiesto.json` (SHA-256 y tamaño de cada archivo, claves y filas en orden estable), `resumen.csv` (UTF-8 con BOM, CRLF, protección contra inyección de fórmulas) y los PDF en `carrera/período/grupo/matrícula/S<n>-v<n>-firmado|original.pdf`; los nombres y rutas los genera el servidor (ASCII, sin `..` ni separadores del alumno). Se arma en un archivo temporal por bloques de 64 KB verificando tamaño y SHA-256 de cada original; si falta o cambió un archivo responde 409 sin entregar un paquete parcial, y el temporal se elimina al terminar o fallar. No hay límite de tamaño ni de tiempo para el paquete de una carrera.

Depuración (C08B, DP-14): con el período finalizado y el paquete ZIP del mismo alcance generado después de la finalización, el tutor o el coordinador programan la eliminación de los PDF (original y firmado de la versión aprobada vigente) con advertencia, confirmación de que la copia ya se guardó y frase escrita; hay 7 días para cancelar y después una tarea de fondo elimina los archivos físicos con reintento idempotente. La fila del documento se conserva (clave, tamaño y SHA-256) marcada como archivada; la descarga responde 410 y el paquete ya no puede generarse. No alcanza copias de seguridad (DP-11, C10).

Probar que el visor obtiene el mismo documento autorizado que descarga. Error de Drive/local no debe resolverse haciendo público el archivo. Exportación ZIP, si se conserva, incluye solo documentos del expediente autorizado y nombres seguros.
