# Guía de uso y operación del piloto

Estado: escrita en C10 (2026-10-17) y seguida con comandos reales en la validación de C10; ver
[evidencia C10](../../specs/C10-validacion-integral-local/evidencia.md) para lo que se probó y lo que no. Está pensada
para el responsable del piloto (coordinador y encargado de la máquina). No requiere hospedaje: el sistema corre en
Docker en un equipo y los archivos viven en Drive. **Sin garantía de disponibilidad**: si el equipo se apaga, el
servicio se detiene.

## 1. Qué hay y dónde

| Pieza | Dónde vive | Cómo se opera |
|---|---|---|
| Aplicación web | Contenedor `web`, `http://127.0.0.1:5174` | Navegador |
| API | Contenedor `api`, `http://127.0.0.1:8001` (`/health` informa el estado) | Docker Compose |
| Base de datos | Contenedor `postgres` (volumen `postgres-data`), sin puerto publicado | Respaldos de la sección 6 |
| Archivos (reportes, plantilla, respaldos) | Carpeta privada de Drive «Formación Dual (piloto)» de la cuenta de pruebas | Nada se guarda en el disco del equipo |
| Credenciales de Drive | `.secretos/` (ignorada por git, nunca se comparte ni se pega en un chat) | Sección 2 |

## 2. Instalación desde cero

Requisitos: Docker Desktop con contenedores Linux, PowerShell y una cuenta de Google de pruebas.

1. `./scripts/setup-local.ps1` genera `.env` con secretos aleatorios (no sobrescribe uno existente; no lo compartas).
2. `docker compose up --build -d --wait` arranca PostgreSQL, API y web. La base se crea nueva (ADR-09), sin datos.
3. Primer coordinador (pide una contraseña oculta de 12 caracteres con mayúscula, minúscula y número; en el primer
   ingreso se obliga a cambiarla):
   `docker compose exec api python scripts/local_admin.py create-coordinator --email <correo> --name "<nombre>"`
4. Drive (una sola vez; ver «Almacenamiento en Drive» en [VALIDACION_Y_OPERACION_LOCAL.md](VALIDACION_Y_OPERACION_LOCAL.md)):
   crear el cliente OAuth «Aplicación de escritorio», guardar su JSON como `.secretos/client_secret.json` y ejecutar
   `docker compose --profile drive run --rm --service-ports drive-autorizar`; abrir la dirección que imprime y aceptar con la
   cuenta de pruebas. Después `docker compose up -d api` y comprobar que `http://127.0.0.1:8001/health` dice
   `"almacenamiento": {"tipo": "drive", "estado": "ok"}`.
5. **Cada 7 días** (aplicación de Google en modo de prueba) el permiso caduca: `/health` pasa a `token_caducado` y los reportes
   dejan de guardarse (503, a propósito, para no aceptar entregas que no se puedan conservar). Repite el paso 4 (solo la
   autorización; la carpeta existente se conserva). Si la universidad ofrece Workspace, el cambio es de configuración.

## 3. Operación diaria por rol

**Alumno** (se registra con su correo institucional si el tutor ya cargó su matrícula en un grupo): entra al foro; descarga la
plantilla Word/PDF; en «Mis reportes» entrega cada semana por separado (PDF y nota entera de 1 a 10; hasta el domingo, y desde
el lunes siguiente aparece como atrasada); si el tutor rechaza, lee la observación y reenvía (queda como versión nueva, la
anterior se conserva); en «Mi expediente» ve por período su grupo de entonces, aprobados (original y firmado), promedio y, tras la
finalización, el paquete ZIP. Escribe al buzón y, si un hilo se cierra, abre uno nuevo enlazado.

**Tutor académico** (transversal a las tres carreras): crea grupos y empresas, carga alumnos con un CSV (`matricula,nombre`),
registra incorporación (empresa y fecha) y baja; en «Revisar y firmar reportes» aprueba (con su firma, que queda dentro de la
celda «Firma» de la fila «Tutor académico» del formato; si el PDF no trae esa tabla se agrega una hoja con la firma y el original
no se altera) o rechaza con observación; puede corregir nota y fechas dejando constancia; consulta expedientes y genera paquetes
ZIP; recupera el acceso de un alumno. **No** cierra ni finaliza períodos.

**Coordinador**: todo lo anterior de consulta, más: abrir períodos, **cerrar la recepción** (bloquea entregas y reenvíos pero permite
seguir revisando), **finalizar** el período cuando no queden reportes por revisar (congela promedios), publicar la plantilla
(Word y PDF juntos), cuentas de tutores, moderar anuncios y programar la **depuración** de archivos (sección 5).

## 4. Ciclo de un período

1. Abrir período → 2. entregas y revisiones → 3. cierre de recepción (coordinador) → 4. revisar lo que quede → 5. finalización
(promedio congelado; «Sin calificación» si no hay aprobados) → 6. paquete ZIP por alumno o por carrera → 7. depuración opcional.
Un período finalizado no se reabre. **Antes de los pasos 5 y 7 haz un respaldo** (sección 6, etiquetas `periodo` y `depuracion`).

## 5. Depuración de archivos (DP-14)

Solo después de haber generado el paquete ZIP. El tutor o el coordinador programa la depuración de un alumno o de una carrera
escribiendo la frase de confirmación que la pantalla indica; hay una **gracia de 7 días** (se puede cancelar) y después la tarea de
fondo elimina de Drive solo los PDF cubiertos por el paquete (aprobado vigente, original y firmado). Notas, promedios, historial y
filas se conservan. Una depuración no alcanza a los respaldos (sección 6), que la restauración vuelve a aplicar.

## 6. Respaldo y restauración (DP-11)

**Política aprobada el 2026-10-17:** el responsable del proyecto ejecuta y vigila los respaldos; una copia semanal y otra antes
de cada finalización de período o depuración; se conservan las 8 copias más recientes y la más antigua de cada uno de los 4
meses más recientes; **una prueba de restauración por trimestre** en un destino aislado; el destino es Drive (espacio `respaldos`);
la automatización queda fuera de alcance (ADR-08). Las copias **no van cifradas** (D3): válido solo con datos sintéticos; antes
de usar datos reales hay que cifrar el volcado con una clave que se guarde aparte.

| Qué | Orden (PowerShell, desde la carpeta del proyecto) |
|---|---|
| Respaldo semanal | `./scripts/respaldo.ps1` |
| Antes de finalizar / depurar | `./scripts/respaldo.ps1 -Etiqueta periodo` / `-Etiqueta depuracion` |
| Ver respaldos | `./scripts/respaldo.ps1 -Orden listar` |
| Comprobar uno (manifiesto, volcado, SHA-256 de cada documento) | `./scripts/respaldo.ps1 -Orden verificar -Id <id>` |
| Retención (simulación; `-Aplicar` elimina de verdad) | `./scripts/respaldo.ps1 -Orden podar` |
| Prueba de restauración aislada | `./scripts/restaurar.ps1 -Id <id> -Descartar` |

- El respaldo sube a Drive el volcado de PostgreSQL, una copia de cada documento (sin repetir los ya guardados) y un manifiesto
  con fecha, huellas de migraciones, conteos, SHA-256 y el registro de depuraciones. Primero se vuelca la base y después se copian
  los documentos. **Se rechaza** (código 2) si la base referencia documentos que no están en Drive: nada se da por respaldado.
  El volcado pasa por `.respaldo-tmp/` (ignorada por git) y se elimina al terminar.
- La restauración **nunca** toca la base ni la carpeta vivas: crea una carpeta de Drive nueva, un proyecto Compose aparte
  (`c10-restauracion`, base nueva, API en el puerto 8101), restaura el volcado, copia los documentos, vuelve a eliminar lo que
  una depuración posterior ya había borrado y verifica conteos, huellas de notas y revisiones, SHA-256 de cada documento y una
  muestra de descargas por la API restaurada. `-Descartar` elimina al final el proyecto de prueba y la carpeta de Drive.
- **Dónde anotar:** cada respaldo relevante y cada prueba de restauración se anotan en
  [REGISTRO_DE_RESPALDOS.md](REGISTRO_DE_RESPALDOS.md) (fecha, id, resultado, quién). Un respaldo sin prueba de restauración no se
  declara recuperable.
- Para **recuperar de verdad** tras perder el equipo: instalar (sección 2) con la misma carpeta de Drive y el mismo permiso,
  y restaurar el último respaldo íntegro; la restauración de prueba ensaya exactamente esos pasos.

## 7. Si algo falla

| Síntoma | Causa probable | Qué hacer |
|---|---|---|
| Entregas y descargas responden «El almacenamiento de archivos no está disponible» | Permiso de Drive caducado, sin red o cuota llena | `/health`: `token_caducado` → reautorizar (sección 2); `cuota` → liberar espacio en Drive; `red` → reintentar |
| Una descarga responde 404 «Archivo PDF no encontrado» o un error de integridad | El archivo falta en Drive o su SHA-256 no coincide con el registrado | No se entrega nada; restaurar desde un respaldo y avisar al responsable |
| `Demasiados intentos` al iniciar sesión | Límite de 8 inicios por 5 minutos | Esperar unos minutos |
| El respaldo termina con «RESPALDO RECHAZADO» | Hay documentos referenciados que no están en Drive | Revisar la lista; no corregir a mano la base; restaurar o avisar |
| Un contenedor no arranca | Revisar `docker compose logs --tail 100 api postgres web` (sin compartir datos personales) | No usar `down -v`: borra la base |

## 8. Límites conocidos y qué no se validó

- Datos sintéticos únicamente; una restauración de prueba no demuestra la recuperación de una producción.
- Hospedaje, otros proveedores y **móvil físico**: NO_VERIFICADOS. Vista móvil solo emulada en un navegador.
- El permiso de Drive en modo de prueba caduca cada 7 días; la cuota gratuita y los límites reales de Drive no se ejercieron a escala.
- Las copias antiguas ya entregadas a terceros no se pueden recuperar; los respaldos no están cifrados (D3).
- Interfaz: C11 corrigió los hallazgos H1 a H3 de C10 (desborde móvil, contraste y tablas). Quedan el hallazgo H4 (listas desplegables sin nombre accesible) y reglas de buenas prácticas de axe sin corregir; ver la evidencia de C11. Sin lector de pantalla real ni móvil físico.
