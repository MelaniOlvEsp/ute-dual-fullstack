# Archivos e importaciones

## Reporte semanal

PDF firmado y calificado por empresa. Campos: obligación semanal, inicio/fin declarados y nota entera 1–10. Tutor verifica visualmente correspondencia; no hay firma empresarial electrónica ni OCR automático.

Límite actual inconsistente: 2 MB frontend / 10 MB API. Unificar en C05 tras DP-08; propuesta 10 MB. Verificar tamaño durante lectura, contenido PDF parseable, extensión/tipo y rechazo claro de corruptos o protegidos que no puedan revisarse. No confiar solo en nombre o cabecera.

Conservar original; firma académica produce derivado. Claves de almacenamiento generadas por servidor y fuera del directorio público. No usar matrícula/ruta aportada por cliente para escribir archivos arbitrarios. No comprimir destructivamente evidencia.

## Firma académica

Imagen PNG/JPEG de tutor propietario. Propuesta límite 1 MB coherente con SQL actual; validar dimensiones/contenido decodificable. La firma aplicada es una representación gráfica, no certificación criptográfica. El documento aprobado debe permanecer legible y conservar firma de empresa.

Ubicación pendiente de muestra visual DP-07. Crear muestra sintética o anonimizada; revisar todas las páginas relevantes. Cambio de firma futura no reescribe firmados anteriores.

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
