# Base de datos — ruta canónica C01

C01 usa una **BD nueva y vacía** dentro de Docker Compose; no hay datos productivos por migrar.

## Instalación

El servicio postgres ejecuta `docker/init-db.sh` sobre un volumen nuevo. Crea el usuario de aplicación sin superusuario, aplica `schema_dual_desde_cero.sql` y después `migrations/003_grupos_incorporacion.sql`, `migrations/004_obligaciones.sql`, `migrations/005_entregas.sql`, `migrations/006_revisiones.sql`, `migrations/007_cierre.sql`, `migrations/008_paquetes.sql` y `migrations/009_depuracion.sql` con ese rol. El esquema base comprueba que `public` no contenga tablas, vistas o secuencias y aborta si ya existen. Cada archivo se instala dentro de una transacción.

No ejecutar todos los SQL de esta carpeta. Reiniciar Compose conserva el volumen; los scripts de inicio de PostgreSQL no se vuelven a aplicar a un volumen ya inicializado. Para actualizar un volumen C01 existente a C03 desde PowerShell, ejecutar únicamente:

```powershell
docker compose cp database/migrations/003_grupos_incorporacion.sql postgres:/tmp/m3.sql
docker compose exec -T postgres sh -c 'PGPASSWORD="$APP_DB_PASSWORD" psql -v ON_ERROR_STOP=1 -h 127.0.0.1 -U ute_dual_app -d ute_dual_c01 -f /tmp/m3.sql'
```

Para C04 a C08B repetir los dos comandos con `004_obligaciones.sql` (`/tmp/m4.sql`), `005_entregas.sql` (`/tmp/m5.sql`), `006_revisiones.sql` (`/tmp/m6.sql`) `007_cierre.sql` (`/tmp/m7.sql`), `008_paquetes.sql` (`/tmp/m8.sql`) y `009_depuracion.sql` (`/tmp/m9.sql`), en ese orden. La 008 y la 009 son idempotentes: se pueden reaplicar sin error. Los originales de reportes viven en el volumen `dual-uploads` de Compose (`/workspace/ute-api-backend/uploads/dual`), que sobrevive a reconstrucciones de la imagen; no se versiona ni se publica. La migración 004 aborta sin cambios si existen períodos con fechas solapadas; corrígelos antes (en una base local de pruebas, alinear sus fechas a las de su etiqueta). Se usa `-f` y no una canalización de PowerShell porque esta altera los caracteres con tilde del catálogo y la migración abortaría por carrera desconocida.

La migración toma un bloqueo transaccional y aborta sin cambios si encuentra una carrera fuera de las tres aprobadas o más de una incorporación activa por matrícula. No borrar datos para resolver ese diagnóstico: revisar y cerrar explícitamente la incorporación anterior.

## Qué contiene el esquema C01

Doce tablas de la demo con acceso de tres roles, usuarios.activo, credential_version y firma de tutor. No contiene email_verificado ni tablas de Becas. El backend C01 ya deja de consultar esas columnas retiradas; la baja de tutor conserva la fila y revoca acceso.

Después de C03, el catálogo contiene TII, Logística y Mercadotecnia; `alumno_grupo_periodo` conserva pertenencias por período y `alumnos_dual` conserva incorporaciones con fechas de inicio/baja. `alumnos.grupo_id` (derivado de la pertenencia del período más reciente) y `alumnos_dual.cuatrimestre` (ya opcional y sin escribirse) permanecen como compatibilidad transitoria; la vigencia de una incorporación en un período se calcula por fechas. Siguen pendientes las obligaciones, versiones, cierre y expediente final de C04–C08.

## Archivos históricos

00_diagnostico.sql, 01_expand_compatible.sql, 01b_indices_online.sql, roles_migracion_manual.sql, 02_validar_y_endurecer.sql, 03_limpieza_final.sql, 04_seguridad_supabase_opcional.sql y 05_revision_rendimiento.sql son propuestas de migración/optimización de la demo. No forman parte del arranque C01.

La migración ute-api-clean/migrations/002_dual_roles_access.sql tampoco se aplica encima del esquema nuevo. Las antiguas afirmaciones de “31 tests del backend alineado” no constituyen evidencia del árbol actual.

## Seguridad y alcance

La API conecta como propietario de sus tablas para el piloto local, no como superusuario. RLS se conserva sin políticas públicas; no se usa Supabase Data API. PostgreSQL no publica puerto al host. No reutilizar esta configuración como diseño productivo sin revisar privilegios y operación.

El administrador local scripts/local_admin.py solo permite DB_NAME=ute_dual_c01 y loopback, o host postgres con C01_LOCAL_COMPOSE=true. init-schema no es necesario en Compose: el entrypoint ya lo ejecuta.

Validación real del esquema y smokes: ver [evidencia C01](../specs/C01-base-local/evidencia.md) y [evidencia C03](../specs/C03-grupos-e-incorporacion/evidencia.md).
