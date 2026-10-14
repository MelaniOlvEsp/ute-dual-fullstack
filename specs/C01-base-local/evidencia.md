# Evidencia de implementación C01

Fecha: 2026-10-14. Estado spec: IN_PROGRESS. Sin revisión formal ni aprobación de cierre.
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
