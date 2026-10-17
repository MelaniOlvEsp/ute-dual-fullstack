#!/bin/sh
set -eu
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" --set=app_password="$APP_DB_PASSWORD" <<'SQL'
CREATE ROLE ute_dual_app LOGIN PASSWORD :'app_password';
ALTER DATABASE ute_dual_c01 OWNER TO ute_dual_app;
GRANT CREATE, USAGE ON SCHEMA public TO ute_dual_app;
SET ROLE ute_dual_app;
\i /opt/ute/schema.sql
\i /opt/ute/migrations/003_grupos_incorporacion.sql
\i /opt/ute/migrations/004_obligaciones.sql
\i /opt/ute/migrations/005_entregas.sql
\i /opt/ute/migrations/006_revisiones.sql
\i /opt/ute/migrations/007_cierre.sql
\i /opt/ute/migrations/008_paquetes.sql
SQL
