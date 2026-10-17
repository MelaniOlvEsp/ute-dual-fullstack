# Validación y operación local

Referencia de validación y operación local. Los comandos de las secciones marcadas «verificado» se ejecutaron de verdad en C01 a C10 (resultados en la evidencia de cada spec; los de C10 en [evidencia C10](../../specs/C10-validacion-integral-local/evidencia.md)); el procedimiento de uso y operación está en [GUIA_DE_USO_Y_OPERACION.md](GUIA_DE_USO_Y_OPERACION.md). No requiere servicios publicados.

## Preparación en C01

1. Inventariar Python/Node/PostgreSQL disponibles y dependencias fijadas por proyecto. No copiar secretos al informe.
2. Crear BD nueva exclusiva del piloto y usuario adecuado; confirmar destino antes de ejecutar SQL.
3. Fijar script de instalación canónico tras reconciliar backend y esquema. No ejecutar todos los scripts de database en orden sin revisión.
4. Crear fixtures sintéticos de coordinador, tutor y dos alumnos de grupos/períodos distintos. Claves de prueba locales no reutilizadas.
5. Configurar variables desde ejemplos sin imprimir secretos. Variables DB_*, SECRET_KEY, FRONTEND_URL, CORS_ORIGINS y VITE_API_URL según configuración real.
6. Si se usa Drive, renovar credenciales y carpeta privada; el nombre histórico GMAIL_CREDENTIALS_PATH no implica envío de correo.
7. Registrar comandos verificados en README_INTEGRACION.md; no asumir que npm ci sirve sin lockfile válido.

## Comprobaciones existentes

Comandos verificados con Docker (no requieren Python ni Node en el host; las pruebas están dentro de la imagen, reconstruir con docker compose up -d --build api tras cambiar código):

```text
docker compose exec -T api python -m unittest discover -s tests          # 276 pruebas OK (2026-10-17)
docker compose exec -T -e ALMACENAMIENTO=memoria api python -m unittest discover -s tests
```

Desde ute-dual-frontend, después de instalación reproducible:

```text
npm test
npm run build
npm run dev
```

Desde raíz:

```text
node --test integration-tests/api-contract.test.mjs
```

Verificado el 2026-10-17: 276 pruebas de backend, 40 de frontend y 1 de contratos (51 operaciones simuladas) en verde. La prueba de contratos usa simulación, no PostgreSQL ni Drive reales. Los smokes por incremento (docker compose --profile verification run --rm --build smoke python scripts/smoke_cNN.py, de C01 a C10; reiniciar la API entre ejecuciones por el límite de 8 inicios de sesión cada 5 minutos) son la regresión real con HTTP, PostgreSQL y Drive; scripts/smoke_c10.py es el recorrido integral.

## Matriz de verificación

| Nivel | Comprobar | Evidencia necesaria |
|---|---|---|
| Dominio | Semanas parciales, límites período, atraso, nota entera, promedio | Tests deterministas con reloj fijo |
| Persistencia | FK, unicidad, versiones, cierre concurrente | PostgreSQL real aislado |
| API | Roles/propiedad, estado cerrado, contratos y errores | Solicitudes reales más tests negativos |
| Archivos | Original y firmado, fallos/reintentos, privados | Lectura binaria real del proveedor elegido |
| UI | Upload, visor, buzón, navegación y cierre | Navegador real, pantallas relevantes sin PII |
| Integral | Incorporación → entrega → revisión → expediente → cierre | Recorrido reproducible con cuentas sintéticas |
| Recuperación | BD y documentos consistentes tras restaurar | Restauración a destino nuevo aislado |

## Recorrido de aceptación local

Crear grupo y alumno; configurar empresa/inicio; registrar alumno; ingresar al foro; descargar plantillas; entregar dos semanas; rechazar una y reenviar; aprobar con firma; comprobar historia y expediente; cerrar recepción con otra entrega pendiente; verificar bloqueo de archivo y aprobación posterior; finalizar; comprobar promedio. Abrir un segundo período según política aprobada y confirmar que el primero no cambia.

Probar también acceso cruzado alumno A/B, rol tutor intentando cierre, fallo de almacenamiento, PDF corrupto, duplicación de envío, conversación completa del buzón y descarga de períodos anteriores.

## Respaldo y restauración (C10, verificado)

Reglas (DP-11, 2026-10-17): responsable = el responsable del proyecto; copia semanal y otra antes de cada finalización o depuración; 8 recientes y 4 mensuales; una prueba de restauración por trimestre en un destino aislado; destino Drive; sin cifrar solo con datos sintéticos (D3). Órdenes: ./scripts/respaldo.ps1 (crear, -Orden listar|verificar|podar) y ./scripts/restaurar.ps1 -Id <id> -Descartar; detalle y registro en [GUIA_DE_USO_Y_OPERACION.md](GUIA_DE_USO_Y_OPERACION.md) y [REGISTRO_DE_RESPALDOS.md](REGISTRO_DE_RESPALDOS.md). El respaldo guarda el volcado de PostgreSQL, una copia de los documentos y un manifiesto en Drive; se rechaza si la base referencia archivos ausentes; la restauración corre en un proyecto Compose y una carpeta de Drive nuevos y verifica conteos, huellas, SHA-256 y descargas de muestra. Las credenciales (.secretos/) nunca viajan en el respaldo. El piloto local no garantiza disponibilidad cuando se apaga el equipo. Selección de alojamiento se investiga aparte con límites actuales y consentimiento de publicación.

## Almacenamiento en Drive (C10A)

Los archivos del piloto (originales y firmados de los reportes, la plantilla común y, en C10, los respaldos) viven en una carpeta privada de Drive; la base de datos corre en Docker en el equipo. Las credenciales se guardan en `.secretos/` (ignorada por git) y nunca se pegan en el chat ni se registran.

Autorización de la cuenta de pruebas (una sola vez, y de nuevo cuando caduque):

1. En Google Cloud crea un proyecto, habilita la API de Drive, configura la pantalla de consentimiento (usuario externo, la cuenta de pruebas como usuario de prueba) y crea un cliente OAuth de tipo «Aplicación de escritorio». Descarga su JSON y guárdalo como `.secretos/client_secret.json`.
2. Ejecuta `docker compose --profile drive run --rm --service-ports drive-autorizar`, abre en el navegador la dirección que imprime y acepta con la cuenta de pruebas. El script guarda `.secretos/drive_token.json` y crea la carpeta raíz «Formación Dual (piloto)» anotando su identificador en `.secretos/drive_config.json`.
3. Reinicia la API (`docker compose up -d api`) y comprueba `http://127.0.0.1:8001/health`: `almacenamiento.estado` debe ser `ok`.
4. Con la aplicación en modo de prueba el token caduca a los 7 días (`token_caducado` en `/health`): repite el paso 2. Si la universidad ofrece una cuenta de Workspace, el cambio de autenticación es de configuración y no cambia los casos de uso.

Regresión sin Drive (solo desarrollo): `ALMACENAMIENTO=local` usa una carpeta local de pruebas (volumen `dual-uploads`); no es el modo del piloto. Con el valor predeterminado (`drive`) y sin autorización las operaciones con archivos responden 503 y `/health` informa `sin_configurar`. Para correr los smokes C01 a C09 con Drive real, autoriza y ejecuta cada uno con `docker compose --profile verification run --rm smoke python scripts/smoke_cNN.py`; `scripts/smoke_c10a.py` comprueba la salud, la falla cerrada y, con Drive autorizado, el ciclo completo de guardar, leer, eliminar y la ausencia de papelera y de temporales.
## Registro en la spec

No registrar contraseñas, tokens, archivos personales ni rutas de credenciales. Incluir fecha, revisión del código, entorno, comando/recorrido, resultado y limitación. Marcar proveedor no utilizado como NO_VERIFICADA. Una prueba de restauración de fixtures no demuestra recuperación de producción.
