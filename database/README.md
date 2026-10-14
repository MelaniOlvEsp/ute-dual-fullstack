# Base de datos — ruta canónica C01

C01 usa una **BD nueva y vacía** dentro de Docker Compose; no hay datos productivos por migrar.

## Instalación

El servicio postgres ejecuta docker/init-db.sh sobre un volumen nuevo. Crea el usuario de aplicación sin superusuario, y aplica schema_dual_desde_cero.sql con ese rol. El esquema comprueba que public no contenga tablas, vistas o secuencias y aborta si ya existen. Se instala dentro de una transacción.

No ejecutar todos los SQL de esta carpeta. Reiniciar Compose conserva el volumen; los scripts de inicio de PostgreSQL no se vuelven a aplicar a un volumen ya inicializado. No borrar datos para resolver errores sin revisar su causa.

## Qué contiene el esquema C01

Doce tablas de la demo con acceso de tres roles, usuarios.activo, credential_version y firma de tutor. No contiene email_verificado ni tablas de Becas. El backend C01 ya deja de consultar esas columnas retiradas; la baja de tutor conserva la fila y revoca acceso.

Es una base compatible para arrancar, **no el modelo funcional final**. Permanecen cuatrimestre textual, semanas 1–18 y falta de versiones/historia académica; C03–C07 los resolverán. El catálogo heredado incluye Educación: su sustitución y nomenclatura oficial corresponden a DP-05/C03. Fixtures de C01 utilizan TIC.

## Archivos históricos

00_diagnostico.sql, 01_expand_compatible.sql, 01b_indices_online.sql, roles_migracion_manual.sql, 02_validar_y_endurecer.sql, 03_limpieza_final.sql, 04_seguridad_supabase_opcional.sql y 05_revision_rendimiento.sql son propuestas de migración/optimización de la demo. No forman parte del arranque C01.

La migración ute-api-clean/migrations/002_dual_roles_access.sql tampoco se aplica encima del esquema nuevo. Las antiguas afirmaciones de “31 tests del backend alineado” no constituyen evidencia del árbol actual.

## Seguridad y alcance

La API conecta como propietario de sus tablas para el piloto local, no como superusuario. RLS se conserva sin políticas públicas; no se usa Supabase Data API. PostgreSQL no publica puerto al host. No reutilizar esta configuración como diseño productivo sin revisar privilegios y operación.

El administrador local scripts/local_admin.py solo permite DB_NAME=ute_dual_c01 y loopback, o host postgres con C01_LOCAL_COMPOSE=true. init-schema no es necesario en Compose: el entrypoint ya lo ejecuta.

Validación real del esquema y smoke: ver [evidencia C01](../specs/C01-base-local/evidencia.md). Estado de infraestructura Docker pendiente de ejecución autorizada desde terminal local.
