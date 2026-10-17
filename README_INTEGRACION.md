# Portal UTE — entorno local con Docker (C01)

Estado: C01 a C10 cerrados (C10 = validación integral). Requisitos funcionales en [docs/README.md](docs/README.md). Uso y operación del piloto: [docs/construction/GUIA_DE_USO_Y_OPERACION.md](docs/construction/GUIA_DE_USO_Y_OPERACION.md).

## Arranque canónico

Requiere Docker Desktop iniciado con contenedores Linux y Docker Compose. No necesitas instalar PostgreSQL/Python/Node en el host. Ejecutar desde esta carpeta en PowerShell:

```powershell
.\scripts\setup-local.ps1
docker.exe compose up --build -d --wait
docker.exe compose ps
```

El setup genera .env raíz con secretos aleatorios, sin sobrescribir uno existente. No mostrar `docker compose config` completo ni compartir .env; para validar usar `docker.exe compose config --quiet`.

- Frontend: http://127.0.0.1:5174/login
- API/health: http://127.0.0.1:8001/health
- API/OpenAPI: http://127.0.0.1:8001/docs
- PostgreSQL: solo red interna de Compose, sin puerto publicado.
- Proyecto Compose: ute-dual-c01; volumen propio postgres-data.

Los puertos 5174/8001 evitan los habituales 5173/3000 de PC-Refresh; pueden cambiarse en .env raíz. El build copia el código: después de modificarlo, repetir up --build. No se monta .env del backend ni credenciales Drive en las imágenes.

## Base inicial

PostgreSQL inicializa una BD nueva ute_dual_c01 con el esquema canónico de [database](database/README.md). La API utiliza ute_dual_app, sin privilegios de superusuario. El esquema se carga únicamente la primera vez con volumen vacío. Reiniciar no borra ni vuelve a crear tablas.

No ejecutar las migraciones/limpiezas heredadas para arrancar C01. No usar down -v: elimina el volumen. Si hay un fallo de inicialización, revisar logs y destino antes de decidir cualquier recuperación; no borrar volumen automáticamente.

## Primer coordinador

```powershell
docker.exe compose exec api python scripts/local_admin.py create-coordinator --email coordinador.local@ute.edu.mx --name "Coordinador local"
```

El comando pide contraseña oculta (12 caracteres mínimo, mayúscula, minúscula y número; máximo 72 bytes por bcrypt). No existe autorregistro público de coordinadores. En el primer login se exige cambiar la contraseña.

Para datos sintéticos adicionales:

```powershell
docker.exe compose exec api python scripts/local_admin.py seed-demo
```

Solicita una clave para las tres cuentas sintéticas: tutor.c01@ute.edu.mx, 990000001@ute.edu.mx y 990000002@ute.edu.mx. Crea dos grupos/períodos distintos y una empresa ficticia. Solo opera con tablas académicas vacías y no sobrescribe registros. Esta carga de demo no sustituye los flujos de C03.

## Verificación

```powershell
docker.exe compose exec api python -m unittest discover -s tests -q
docker.exe compose exec web npm test
docker.exe compose exec web npm run build
docker.exe compose --profile verification run --rm smoke
```

Smoke crea cuentas sintéticas únicas y prueba por HTTP real + PostgreSQL real: health, coordinador administrativo, cambio obligatorio, revocación, alta tutor/alumno, perfiles, permisos y baja lógica. No imprime claves ni tokens. Conserva las filas sintéticas y no elimina datos. El limitador de login puede rechazar ejecuciones repetidas dentro de cinco minutos; esperar ese intervalo antes de repetir.

La prueba de contratos adicional se puede ejecutar en host con Node:

```powershell
node --test integration-tests/api-contract.test.mjs
```

Esta última es SIMULADA. No equivale al smoke ni al recorrido integral.

## Operación

```powershell
docker.exe compose logs --tail 100 api postgres web
docker.exe compose stop
docker.exe compose start
```

No compartir logs sin revisar que no incluyan datos personales. No publicar el puerto PostgreSQL ni reutilizar secretos del piloto.

## Estado verificado de esta entrega

Ver la evidencia de cada spec en [specs/README.md](specs/README.md) (la de C01 describe la base; la de C10, el recorrido integral y la recuperación).

Drive no es necesario para login/health, pero sí para guardar y descargar cualquier PDF (C10A: contrato de almacenamiento con Drive; sin autorizar, esas operaciones responden 503 a propósito). Ver «Almacenamiento en Drive» en [VALIDACION_Y_OPERACION_LOCAL.md](docs/construction/VALIDACION_Y_OPERACION_LOCAL.md).
