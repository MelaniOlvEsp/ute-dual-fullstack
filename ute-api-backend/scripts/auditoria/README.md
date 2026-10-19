# Guiones de auditoría y de carga (C14)

Herramientas de verificación con **HTTP y PostgreSQL reales sobre Compose local**. No forman parte del producto, usan datos
sintéticos que se conservan y no imprimen contraseñas ni tokens. Las cuentas se crean por SQL y los tokens se firman con la
clave local, para no agotar el límite de inicios de sesión (8 por 5 minutos por IP).

Se ejecutan en el contenedor `smoke` (perfil `verification`), que ya trae las dependencias y la red de la API. Si cambias
guiones, añade `--build` para que la imagen los incluya. Para conservar el estado y los resultados entre ejecuciones monta
una carpeta del equipo en `AUDITORIA_DIR`:

```bash
docker compose --profile verification run --rm --build -v "${PWD}/.auditoria-tmp:/auditoria" -e AUDITORIA_DIR=/auditoria smoke python scripts/auditoria/carga.py setup 12
```

(`.auditoria-tmp` no se versiona; bórrala al terminar. Sin `-v` el estado vive solo dentro de cada contenedor y no se
comparte entre pasos.)

| Guion | Qué comprueba |
|---|---|
| `rutas.py` | Recorre **todas** las operaciones de `/openapi.json` sin sesión y con sesión de alumno, tutor y coordinador: nada responde 5xx, sin sesión no hay datos, cada rol recibe 403 donde no le corresponde y las cargas malformadas dan 4xx. Usa identificadores que no existen, así que no modifica datos reales. |
| `carga.py` | Flujo completo con N alumnos y carga: `setup N`, `alumnos DESDE HASTA W RPM` (entregas), `revisar W RPM` (aprobar y firmar), `cerrar` (cierre y finalización con comprobación de promedios), `lecturas DESDE HASTA W RPM` (expediente y ZIP del alumno), `paquete` (ZIP de la carrera), `limite` (ráfaga contra el limitador), `carrera DESDE HASTA HILOS` (lecturas simultáneas de obligaciones), `sonda SEGUNDOS`, `integridad`, `informe`. |
| `retroactiva.py` | C14-D3: alta con inicio en 2015 y baja de cuatro semanas antes de la primera lectura; comprueba que el alta no crea filas, que la baja crea solo hasta la baja y que ninguna fila queda más allá de ella. |

## Notas

- El limitador de la API es de 240 solicitudes por minuto por usuario, 120 por IP sin sesión y 1200 por IP en total.
  `Ritmo(rpm)` mantiene cada guion por debajo; si lo superas la API responde 429 con `Retry-After` (es lo esperado).
- Entre ejecuciones largas reinicia la API (`docker compose restart api`) para vaciar los contadores del limitador.
- Para repetir un smoke muchas veces (p. ej. `smoke_c04.py`), reinicia la API antes de cada ejecución: el smoke inicia sesión
  varias veces y el límite de inicios de sesión es de 8 por 5 minutos por IP.
- Las pruebas con Drive real usan `ALMACENAMIENTO=drive` (valor por omisión del Compose local) y dejan archivos sintéticos.
