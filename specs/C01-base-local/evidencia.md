# Evidencia de implementación C01

Fecha: 2026-10-14. Estado actual: DONE. Revisión APPROVED y cierre humano autorizado; ver acta al final. Los apartados anteriores al acta conservan evidencia histórica, no el estado vigente.
No hay repositorio .git en esta carpeta; no se hizo commit/push. Copias de archivos previos y logs locales en work/c01, ignorados. El manifiesto de cambios identifica archivos y hashes para revisión.

## Línea base

- Python 3.12.10, Node 24.20.0, npm 11.19.0; PostgreSQL 18 disponible en host.
- Docker CLI 29.8.2, Compose 5.6.0; motor inaccesible desde sandbox: permission denied al named pipe dockerDesktopLinuxEngine.
- Frontend: 20 tests aprobados; contrato: 1 prueba, 51 llamadas contra 51 rutas (SIMULADA).
- Backend inicial: 16 tests cargados, 2 errores de importación por loguru ausente en Python global.
- Build inicial: faltaba Vite instalado. Tras npm ci apareció EPERM en fs.realpathSync.native del sandbox.
- Se inició un cluster nativo exclusivo en work/c01/postgres durante diagnóstico; no se validó esquema/API. pg_ctl confirmó después que no seguía ejecutándose. No se usaron servicios ni bases existentes.
- El usuario corrigió el objetivo de entorno a Docker; la ruta nativa dejó de ser entregable.

## Comprobaciones realizadas

| Verificación | Resultado | Evidencia y alcance |
|---|---|---|
| Instalación Python original en .venv aislado | Completa | REAL; caché/temp dentro del proyecto |
| Resolución de dependencias directas y lock reducido | 55 paquetes fijados | REAL resolución con constraints de la línea base; imagen Linux pendiente |
| pip check | Sin requisitos rotos | REAL en .venv host; contiene extras históricos, no prueba imagen Docker mínima |
| unittest discover -s tests -q | 28 tests OK | REAL ejecución; persistencia/servicios simulados, 2 tests nuevos de configuración/arranque |
| compileall app scripts | Correcta | REAL sintaxis |
| npm test | 20 OK | REAL ejecución; HTTP simulado |
| Contratos HTTP | 1 OK / 51 operaciones | SIMULADA; no servidor |
| npm run build | 97 módulos, artefactos dist generados | REAL host; fallback temporal de realpath en work/c01, sin modificar Vite |
| Advertencias build | Accesibilidad/CSS heredadas | Registradas, fuera del alcance de base C01 |
| docker.exe compose config --quiet | Correcta | REAL validación sintáctica, no conecta al motor |
| docker compose up/build/health | NO_VERIFICADA | Motor inaccesible por permisos del entorno |
| Smoke HTTP + PostgreSQL Compose | NO_VERIFICADA | scripts/smoke_c01.py preparado; no ejecutado con motor real |
| Navegador /login | NO_VERIFICADA | Intento nativo 127.0.0.1:5173 agotó tiempo; Docker objetivo 5174 pendiente |
| Drive/PDF/flujo integral | NO_VERIFICADA | Fuera de C01 |

## Criterios de C01

- C01-AC1: pendiente PostgreSQL real en Compose.
- C01-AC2: pendiente smoke de login/perfil sobre API + PostgreSQL reales.
- C01-AC3: build host verificado; imagen Docker y navegador pendientes.
- C01-AC4: pruebas existentes ejecutadas y fallos de línea base clasificados.
- C01-AC5: guía/configuración escritas; recorrido Docker pendiente.

No convertir pendientes en aprobados por contar con scripts o mocks.

## Cómo completar evidencia

Desde raíz en terminal local con Docker Desktop:

```powershell
docker.exe compose up --build -d --wait
docker.exe compose ps
docker.exe compose exec api python -m unittest discover -s tests -q
docker.exe compose exec web npm test
docker.exe compose exec web npm run build
docker.exe compose --profile verification run --rm smoke
```

Abrir http://127.0.0.1:5174/login y comprobar pantalla, consola/errores y login de cuenta sintética. Guardar resultados sin secretos. El smoke crea datos sintéticos y consume siete intentos de login; esperar cinco minutos antes de repetir para respetar el limitador.

Registrar versión de imágenes/contenedores y actualizar esta tabla tras ejecución real. Mantener IN_PROGRESS hasta revisión y aprobación humana; no iniciar C02.

### Corrección posterior a REVIEW / PREVIEW C01

- PerfilModal ahora usa exclusivamente alumno.dual_activo del contrato /auth/me; no deduce la inscripción por la presencia de empresa.
- Smoke ampliado: comprueba dual_activo=false para alumno sin asignación y dual_activo=true/empresa=null para alumno activo sin empresa.
- Build frontend posterior a la corrección: REAL, correcto, usando resolve.preserveSymlinks=true solo en la ejecución local por EPERM de Windows. No se repitieron suites ya válidas.
- Smoke real: PENDIENTE de ejecutar en PowerShell del usuario; Docker continúa rechazando el acceso al named pipe desde la sesión del agente. No se declara PASS ni se cierra C01.
- Comando preparado: docker compose --profile verification run --build --rm smoke. Guardar salida en work/c01/smoke-compose.log y registrar resultado después de recibirla.

## Resultado posterior: smoke Compose PASS

Fecha: 2026-10-14. Ejecución por el usuario en PowerShell; salida aportada en el chat y corroborada leyendo work/c01/smoke-compose.log. Esta sección actualiza los pendientes históricos del smoke anteriores; no representa cierre ni nueva aprobación de revisión.

Comando: docker compose --profile verification run --build --rm smoke.
Resultado: PASS C01. Imagen ute-dual-c01-smoke construida y API Healthy. HTTP y PostgreSQL REALES.

Comprobaciones del script ejecutado: health; creación administrativa de coordinador; bloqueo con contraseña temporal; cambio obligatorio e invalidación de token anterior; login/perfil del coordinador; alta y acceso del tutor; registro y perfil del alumno; denegación del listado de tutores a tutor/alumno; perfil único con dos asignaciones activas; baja lógica del tutor con revocación y fila conservada. También se verificó dual_activo=false sin asignación y dual_activo=true con empresa=null en alumno activo.

C01-AC2: evidencia real del smoke disponible para revisión. Arranque inicial con volumen nuevo y contenedores saludables documentado por el usuario previamente en este chat; health HTTP 200 y recorrido visual del coordinador comprobados por el agente. Las pruebas y builds previos no se repitieron.

Limitaciones: este smoke no verifica conservación integral de expedientes/versiones, restauración, Drive, PDFs, firmas ni calendario. La inspección visual de alumno/tutor y móvil sigue pendiente en UI01; la validación API de dual_activo no la sustituye. No se inspeccionaron directamente imágenes/digests desde el agente por restricción del canal Docker.

Estado: IN_PROGRESS. Pendiente nueva revisión; sin cierre, commit ni push.

## Acta de cierre C01 — 2026-10-14

Revisión final: APPROVED, por el mismo agente (no independiente), contra spec, requisitos, diff real y evidencia. Aprobación humana: mensaje CLOSE C01 + NEXT SPEC de este chat. Estado definitivo de este incremento: DONE.

| Criterio | Evidencia suficiente aceptada |
|---|---|
| C01-AC1 | Salida inicial del usuario: volumen ute-dual-c01_postgres-data creado y tres servicios Healthy; esquema inicial usado por API y smoke reales. |
| C01-AC2 | work/c01/smoke-compose.log: PASS, HTTP/PostgreSQL reales; perfiles, restricciones comprobadas, cambio obligatorio, revocación, fila del tutor conservada tras baja y contrato dual_activo. |
| C01-AC3 | Compilación final correcta (99 módulos); workaround local preserveSymlinks por EPERM sin cambiar Vite; imagen web construida por usuario y /login inspeccionado visualmente en navegador. |
| C01-AC4 | 28 pruebas backend registradas; 20 frontend aprobadas; contrato simulado 1 prueba/51 operaciones; errores iniciales y advertencias heredadas clasificados. Las pruebas simuladas no se presentan como integración real. |
| C01-AC5 | Guía Compose, setup sin sobrescribir .env, Dockerfile ajustado a carpeta real, exclusiones de secretos y puertos loopback inspeccionados; arranque reproducido por el usuario. |

Entregado: entorno local FastAPI/PostgreSQL/Svelte, esquema de base nueva, primer coordinador administrativo, fixtures sintéticos, identidad compatible y pruebas base. El smoke fue ejecutado por el usuario y su log leído por el agente; el canal Docker siguió restringido para el agente. No se volvieron a ejecutar pruebas válidas para cerrar.

Límites aceptados: baja lógica probada no equivale a historial completo de expediente/versiones. Drive, PDFs, firmas, calendario, restauración y flujo integral siguen NO_VERIFICADA. Preview de alumno/tutor y móvil pendiente en UI01, que no se cierra aquí. Referencia visual de revisión: captura c01-login-review.png entregada en el chat.

C02 preparado en DRAFT; sin implementación. No commit/push. Los estados IN_PROGRESS y pendientes anteriores en este archivo describen etapas históricas y quedan sustituidos por esta acta para C01.
