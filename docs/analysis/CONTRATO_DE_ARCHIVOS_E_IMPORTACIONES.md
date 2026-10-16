# Archivos e importaciones

## Reporte semanal

PDF firmado y calificado por empresa. Campos: obligación semanal, inicio/fin declarados y nota entera 1–10. Tutor verifica visualmente correspondencia; no hay firma empresarial electrónica ni OCR automático.

Implementado en C05 (DP-08, 2026-10-15): límite único de 10 MB en cliente y API (antes 2 MB y 10 MB), leído en bloques con corte al exceder (413). La API rechaza con 422 y mensaje claro: extensión distinta de `.pdf`, archivo vacío, cabecera `%PDF-` ausente, PDF dañado o incompleto (incluido el que requiere reparación), PDF sin páginas, con contraseña o cifrado, o cuya primera página no se pueda leer. No confía solo en el nombre ni en la cabecera. Una entrega rechazada no deja documento, reporte ni archivo.

Conservar original; firma académica produce derivado. Claves de almacenamiento generadas por servidor y fuera del directorio público. No usar matrícula/ruta aportada por cliente para escribir archivos arbitrarios. No comprimir destructivamente evidencia.

Implementado en C05: almacenamiento privado local (volumen `dual-uploads`) con clave `<uuid>.pdf` generada por el servidor, hash SHA-256, tamaño y páginas en `documentos`; el original se guarda byte a byte (sin recompresión) con escritura atómica y nunca sobrescribe. Si la transacción falla se elimina solo el archivo recién guardado; los archivos sin fila de `documentos` se limpian por referencia y antigüedad (`limpiar_huerfanos`). Drive queda como lectura heredada y NO_VERIFICADO.

## Firma académica

Imagen PNG/JPEG de tutor propietario. Propuesta límite 1 MB coherente con SQL actual; validar dimensiones/contenido decodificable. La firma aplicada es una representación gráfica, no certificación criptográfica. El documento aprobado debe permanecer legible y conservar firma de empresa.

Ubicación (DP-07, resuelta el 2026-10-16): la firma se estampa en la celda vacía de la columna «Firma» en la fila «Tutor académico» de la tabla final del reporte. La celda se localiza por el texto de la fila, el encabezado de la columna y las líneas dibujadas de la tabla, en la última hoja que la contenga. Si no se reconoce el formato (por ejemplo un PDF escaneado), la celda está ocupada o la página está girada, se usa como respaldo una hoja adicional con la firma, el nombre y la fecha de revisión, y la revisión registra qué modo se usó. Se conserva el original y el firmado es un documento distinto; el estampado no cambia el texto del reporte. Se validó con una réplica sintética del formato (muestra en la spec C06) y con el reporte de ejemplo del responsable solo de forma local, sin copiarlo al repositorio. Cambio de firma futura no reescribe firmados anteriores.

## Plantilla común

Coordinador publica pareja Word (.docx) y PDF; ambos para las tres carreras. Archivos separados cargados por coordinador, sin conversión automática requerida. Versionar y publicar pareja completa; fallar uno mantiene la versión anterior. Rechazar formatos inesperados; no aceptar macros como requisito de V1. Tamaño Word/PDF en spec C09.

El alumno descarga la versión vigente; no exigirle reentregar un reporte histórico por cambiar plantilla. El Excel existente no forma parte del alcance confirmado.

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

Probar que el visor obtiene el mismo documento autorizado que descarga. Error de Drive/local no debe resolverse haciendo público el archivo. Exportación ZIP, si se conserva, incluye solo documentos del expediente autorizado y nombres seguros.
