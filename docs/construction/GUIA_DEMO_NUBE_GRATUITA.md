# Demo temporal en la nube (sin costo mensual)

Esta guía prepara una demo aislada para revisión académica. No usar datos personales ni información real de alumnos.

## Servicios

- Frontend Svelte como sitio estático gratuito en Render.
- API FastAPI como servicio gratuito en Render.
- PostgreSQL nuevo en Supabase Free.
- Archivos PDF y documentos en una carpeta privada del Drive de la maestra, mediante OAuth de usuario.

Render Free duerme la API después de 15 minutos sin tráfico; el primer acceso posterior puede tardar cerca de un minuto. Render Free Postgres no se usa porque expira a los 30 días. Supabase Free permite una base pequeña, pero puede pausarla si queda inactiva por una semana. Reactivarla desde el panel antes de una revisión.

## Preparación necesaria antes de publicar

1. Crear un proyecto nuevo en Supabase Free destinado solo a la demo.
2. Verificar que `public` no tenga tablas y, en Supabase SQL Editor, instalar `database/schema_dual_desde_cero.sql` y después las migraciones `003` a `010` en orden. No ejecutar los scripts de diagnóstico/limpieza ni usar una BD con datos existentes.
3. En la carpeta del proyecto, generar `.env` con `scripts/setup-local.ps1` y construir la imagen API con Docker. Ejecutar `docker compose run --no-deps --rm api python scripts/bootstrap_demo_cloud.py --host <host-de-supabase> --user <usuario-de-supabase> --confirm-target SUPABASE-DEMO --email coordinador.demo@ute.edu.mx --name "Coordinación de demo" --seed-demo`. La herramienta pide de forma oculta la contraseña de la BD, la contraseña provisional del coordinador y la contraseña común de las cuentas sintéticas; exige confirmar el hostname exacto y aborta si ya hay usuarios. No usar datos de alumnos reales.
4. Importar `render.yaml` como Blueprint desde la raíz del repositorio. La plantilla crea frontend y API, y conecta automáticamente sus URLs públicas.
5. En el servicio API, completar `DB_HOST`, `DB_NAME=postgres`, `DB_USER` y `DB_PASSWORD` con los datos de conexión del proyecto Supabase (pestaña Connect; preferir Session Pooler si la conexión directa no funciona desde Render). El usuario de Session Pooler puede incluir el sufijo `.ref-del-proyecto`. No guardar credenciales en Git ni pegarlas en chats.
6. En Google Cloud, crear un cliente OAuth de tipo **Aplicación de escritorio**, habilitar Drive API y añadir la cuenta Workspace de la maestra como usuaria de prueba si el proyecto está en modo Testing. Guardar el JSON de cliente en `.secretos/client_secret.json` localmente.
7. Ejecutar localmente `docker compose --profile drive run --rm --service-ports drive-autorizar`. La maestra inicia sesión en Google en el navegador de la computadora donde corre ese comando y acepta el alcance `drive.file`; no compartir su contraseña. El script crea la carpeta «Formación Dual (piloto)» en su Drive y escribe `drive_token.json` y `drive_config.json` en `.secretos/`.
8. En Render, servicio `ute-dual-api-demo` → Environment → Secret Files, crear `drive_token.json` y pegar el contenido del archivo local con el mismo nombre. En Environment, poner `DRIVE_CARPETA_ID` con el valor `carpeta_id` de `.secretos/drive_config.json`; desplegar de nuevo. Nunca subir esos archivos al repositorio ni enviarlos por chat.
9. Revisar `/health`, iniciar sesión con cuentas sintéticas y recorrer carga/descarga de un PDF de prueba. Confirmar que aparece en la carpeta del Drive de la maestra.

La herramienta `scripts/bootstrap_demo_cloud.py` solo crea el coordinador de demo y las cuentas sintéticas. `scripts/local_admin.py` sigue restringido a la base local y no se debe apuntar a Supabase.

Este flujo reutiliza el token OAuth de usuario que el adaptador Drive ya entiende. El consentimiento se hace una vez en el navegador local; el servicio usa el token alojado como Secret File en Render. Si el proyecto OAuth sigue en estado Testing, la autorización de Drive puede expirar a los 7 días; reautorizar y reemplazar el Secret File si hace falta. Si la política de Workspace bloquea la app, el administrador de la universidad deberá permitirla.

## Limitaciones del plan gratuito

- La API puede tardar en despertar después de estar inactiva.
- La base de Supabase puede pausarse por inactividad y el plan Free no ofrece respaldos administrados descargables.
- Exportar una copia de la base antes y después de la evaluación y conservarla fuera de la nube.
- No tratar esta demo como alojamiento de producción. Los límites y condiciones de los planes gratuitos pueden cambiar.

