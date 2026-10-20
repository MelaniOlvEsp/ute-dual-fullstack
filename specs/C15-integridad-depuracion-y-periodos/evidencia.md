# Evidencia C15 — integridad de depuración y períodos

Fecha local: 2026-10-19 (America/Mexico_City). Base del trabajo: HEAD `d28b26d`, cambios sin commit. Spec **IN_PROGRESS**, revisión técnica del mismo agente **APPROVED**, cierre humano pendiente.

## Cambios y garantías

- La cancelación usa una actualización condicional con `clock_timestamp()` después de obtener el bloqueo: solo dentro de la gracia y con cero intentos. Sin fila devuelta, responde 409 y no libera documentos. Cancelar una purga ya cancelada sigue siendo idempotente.
- El primer intento se confirma antes de tocar el almacenamiento. Cada documento se borra y se marca en una transacción independiente. Un fallo posterior no revierte los archivos previamente archivados; el reintento omite ese progreso. Si el proceso cae entre borrado y commit, repite el borrado del archivo ausente de forma idempotente. Las cifras de respuesta son las de todo el alcance.
- Se conserva `programada` hasta completar: representa también trabajo pendiente de reintento. No hubo migración ni nuevos estados/rutas. `intentos` cuenta ahora ejecuciones iniciadas, no solo errores.
- La pantalla usa un controlador comprobable sin dependencias de UI o transporte. Identifica cada solicitud con una secuencia, invalida resumen/confirmación al cambiar período y descarta respuestas y errores antiguos. Captura el ID y etiqueta confirmados, revalida identidad/permisos y bloquea doble envío y cambios durante la operación.
- Se actualizó el smoke C08B, que aún exigía que ningún documento quedara archivado después de un fallo. Ahora verifica progreso confirmado, referencia conservada y cancelación 409. No se ejecutó ese smoke integral contra el piloto.

## Comprobaciones ejecutadas

| Comprobación | Comando/pasos | Entorno | Resultado y clase |
|---|---|---|---|
| Backend completo | `python -m unittest discover -s tests -q` | Python 3.12, contenedor temporal sin red, repo montado de solo lectura, `ALMACENAMIENTO=memoria`, DB inaccesible | **324/324**, ninguna omitida. Dependencias externas SIMULADAS; ejecución REAL |
| PostgreSQL C15 | `python /workspace/integration-tests/test_c15_purgas_postgres.py` | PostgreSQL 16-alpine nuevo, esquema y migraciones reales, red interna propia, almacenamiento temporal sintético | **8/8**, SQL/bloqueos/commits/archivos REALES; fallos inyectados y fechas de fixtures SIMULADOS |
| Frontend completo | `node --test tests/*.test.js` | Node local, Svelte 4/Vite 5 del lockfile existente | **59/59**, incluye 11 nuevas con promesas SIMULADAS |
| Build | `node node_modules/vite/bin/vite.js build` | Vite 5.4.21 | **OK**, 117 módulos; avisos previos de CSS/accesibilidad, sin fallo de compilación |
| Contrato | `node --test integration-tests/api-contract.test.mjs` | Node local, repositorios HTTP y fixture existentes | **1/1**, 75 llamadas contra 73 rutas; transporte SIMULADO |
| Preview | `/tests/fixtures/c15/index.html` en Vite local :5185 | Componente real en navegador integrado, API SIMULADA y `fetch` deshabilitado | A retenida → B → respuesta A tardía mantiene B; finalización envía B; cambiar selección descarta confirmación A; cierre envía A; selector/apertura/doble envío bloqueados durante ambas acciones |
| Revisión | Diff contra spec, lectura de nuevos archivos y `git diff --check` | Mismo agente | **APPROVED**, sin revisión independiente; sin errores de whitespace |
| Entorno actualizado | `docker compose up -d --build --no-deps api web` | Compose `ute-dual-c01` existente | API/web reconstruidos, PostgreSQL y volúmenes conservados. `/health` 200 con Drive `ok`, frontend `/login` 200; hashes fuente/contenedor coinciden |

Las ocho pruebas PostgreSQL cubren: fallo del segundo archivo y reintento, gracia/cancelación idempotente, vencimiento exacto, intento iniciado, vencimiento mientras se espera un bloqueo, interrupción entre borrado y commit, cancelación de tarea y trabajadores/cancelación concurrentes. En concurrencia `SKIP LOCKED` puede ceder la tarea entre documentos; se verificó que otro ciclo la completa sin duplicar borrados confirmados.

La primera ejecución de la prueba concurrente asumía que el mismo trabajador siempre terminaría. Se corrigió esa expectativa para comprobar el comportamiento acordado de cesión/reintento; se recreó la base efímera y las ocho pruebas pasaron. No se ocultó un fallo funcional ni se relajó la garantía de conservación.

## Repetir pruebas sin tocar el piloto

Unitarias backend (PowerShell desde la raíz del repo, usando la imagen ya construida):

```powershell
$repo = (Get-Location).Path
docker run --rm --network none -e ALMACENAMIENTO=memoria -e DB_HOST=127.0.0.1 -e DB_PORT=1 --mount "type=bind,source=$repo,target=/workspace,readonly" ute-dual-c01-api python -m unittest discover -s tests -q
```

Integración PostgreSQL: exige base vacía y rechaza cualquier host/nombre distinto de los siguientes. No reutilizar el volumen del piloto. Los nombres deben estar libres antes de comenzar:

```powershell
$repo = (Get-Location).Path
docker network create --internal ute-dual-c15-test
docker run -d --name ute-dual-c15-postgres --network ute-dual-c15-test --tmpfs /var/lib/postgresql/data -e POSTGRES_DB=ute_dual_c15_test -e POSTGRES_HOST_AUTH_METHOD=trust postgres:16-alpine
docker exec ute-dual-c15-postgres pg_isready -U postgres -d ute_dual_c15_test
# Continuar cuando pg_isready indique que acepta conexiones.
docker run --rm --network ute-dual-c15-test -e ALMACENAMIENTO=memoria -e 'C15_TEST_DSN=host=ute-dual-c15-postgres dbname=ute_dual_c15_test user=postgres' --mount "type=bind,source=$repo,target=/workspace,readonly" ute-dual-c01-api python /workspace/integration-tests/test_c15_purgas_postgres.py
# Retirar exclusivamente los recursos efímeros creados para esta prueba:
docker rm -f ute-dual-c15-postgres
docker network rm ute-dual-c15-test
```

El contenedor de prueba no publica puertos, usa una red interna y tmpfs; la confianza sin contraseña es exclusiva de ese entorno desechable. No se monta `.secretos` como credenciales ni se configura Drive.

Frontend: desde `ute-dual-frontend`, `node --test tests/*.test.js` y `node node_modules/vite/bin/vite.js build`. Contrato desde raíz: `node --test integration-tests/api-contract.test.mjs`. Preview repetible: [instrucciones](../../ute-dual-frontend/tests/fixtures/c15/README.md).

## Límites y cierre

- No se borraron archivos de Drive para probar la corrección. El borrado externo real de Drive no se revalidó; las regresiones usan archivos locales sintéticos y la semántica idempotente existente del adaptador.
- No se ejecutaron cierres ni finalizaciones sobre períodos del piloto. El cableado y la interacción de pantalla se comprobaron con el componente real y API simulada; los contratos/rutas no cambiaron.
- No se corrieron todos los smokes históricos ni pruebas de carga, lector de pantalla o móvil físico. Los otros hallazgos de auditoría siguen fuera de C15.
- Una transacción sigue abarcando como máximo un borrado externo para serializarlo sin introducir leases o infraestructura nueva; no abarca el lote. La atomicidad entre PostgreSQL y Drive se obtiene mediante reintento, no mediante rollback del archivo.
- No se ejecutaron migraciones, limpiezas históricas, commit o push. C15 permanece IN_PROGRESS hasta aprobación humana de cierre, según AGENTS.md y SDD Lite.
- Al terminar se retiraron el contenedor `ute-dual-c15-postgres`, su red interna y el servidor de preview :5185. Permanecen únicamente los tres servicios habituales de `ute-dual-c01`, todos saludables. Se guardó una captura del preview sintético de confirmación.

## Acta de cierre

El responsable aprobó el cierre el 2026-10-19 con «apruebo el cierre de C15» y autorizó el commit. La evidencia anterior describe el corte de implementación; C15 queda DONE. No hay autorización de push.
