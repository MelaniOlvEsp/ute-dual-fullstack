# API Formación Dual

FastAPI + PostgreSQL. Arranque canónico C01 con Docker desde la raíz: [guía](../README_INTEGRACION.md).

## Comandos desde raíz

```powershell
docker.exe compose up --build -d --wait
docker.exe compose exec api python -m unittest discover -s tests -q
docker.exe compose --profile verification run --rm smoke
```

Health verifica conexión de BD; startup espera una conexión real y exige SECRET_KEY de al menos 32 caracteres. No necesita credenciales Drive para iniciar identidad. Si PostgreSQL falla, no declarar listo el servicio.

requirements.in enumera dependencias directas; requirements.txt fija transitivas conservando las versiones de la línea base cuando eran necesarias. Se retiraron paquetes de Supabase, psycopg2, uuid y otros no importados por el código. Los paquetes exclusivos de Windows llevan marcador de plataforma. No se cambió el framework.

scripts/local_admin.py proporciona creación administrativa de coordinador y fixtures. La configuración de .env del backend es solo para ejecución nativa opcional; Compose usa variables del servicio y excluye todos los .env de la imagen.

## Organización

domain: reglas puras; application: casos de uso y puertos; infrastructure: persistencia, configuración, PDF y Drive; presentation: API y middleware. No hay envío de correo ni Becas.

C01 alinea identidad con esquema sin email_verificado, evita perfiles duplicados por asignaciones y respeta usuarios.activo. Calendario, versiones, firma visual y cierre nuevo quedan para siguientes specs.

[Evidencia](../specs/C01-base-local/evidencia.md). No se considera validada la integración real hasta que el smoke pase en Docker.
