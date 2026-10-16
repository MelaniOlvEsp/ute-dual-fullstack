# C02 — Evidencia de implementación

Implementación: 2026-10-14. Verificación y cierre: 2026-10-15. Estado DONE. Autorizaciones IMPLEMENT C02 y CLOSE C02 registradas en la spec. Sin commit/push ni implementación de C03.

## Entregado

- Registro autorizado bloquea la matrícula durante el alta; INSERT de alumno/tutor resuelve conflictos únicos como 409. DTO rechaza campos extra, incluidos roles.
- El perfil `/auth/me` informa `dual_activo` a partir de la incorporación activa y no de que exista una empresa asignada; una incorporación válida sin empresa ya no se presenta como inactiva.
- Contraseñas: 12–128 puntos de código y máximo 72 bytes UTF-8, categorías Unicode Ll/Lu/Nd compartidas por API/cliente. Login rechaza entradas mayores a 72 bytes antes de bcrypt. Temporales de 12 caracteres garantizan mayúscula, minúscula y dígito además del componente aleatorio.
- Cambio de contraseña bloquea la cuenta y vuelve a comprobar credential_version; una recuperación concurrente no puede ser sobrescrita con sesión obsoleta. Contraseña actual incorrecta devuelve 400 y conserva sesión para reintentar.
- PDF de otro alumno e hilos ajenos devuelven 404. Cierre de buzón reservado a personal. Guard de cierre de período reservado a coordinador; calendario no rediseñado.
- DELETE de alumno ahora desactiva cuenta, revoca sesiones y desautoriza registro sin borrar alumno, asignaciones, reportes o mensajes. No representa baja de incorporación Dual. Interfaz explica esta diferencia; no se agregó reactivación de cuentas.
- [Mapa de rutas](rutas.md), contrato API, pruebas y smoke C02 actualizados. Sin cambios de esquema ni migraciones.

## Evidencia disponible

| Verificación | Naturaleza | Resultado |
|---|---|---|
| Backend `unittest discover -s tests -q` | Ejecución REAL; repositorios/proveedor SIMULADOS, contratos estáticos | 41 pruebas PASS el 2026-10-15 en Python 3.12 del host con dependencias existentes |
| Frontend `node --test tests/*.test.js` | Ejecución REAL; HTTP SIMULADO | 21 pruebas PASS |
| Build Vite | REAL, compilación | PASS, 99 módulos; advertencias previas de accesibilidad/CSS. Resolución temporal preserveSymlinks en host Windows, no incorporada a configuración del producto |
| Smoke C01 previo | REAL, ejecutado por usuario con HTTP/PostgreSQL | Evidencia heredada: no sustituye los cambios de C02 |
| Smoke C02 | REAL, ejecutado por usuario; HTTP/PostgreSQL con fixtures sintéticos | PASS C02 el 2026-10-15 tras reconstruir API/web; salida aportada en el chat |
| Preview de cambios C02 | REAL, Docker local y navegador | PASS: recorridos de coordinador, tutor y alumno verificados el 2026-10-15 |
| Temporal de 12 caracteres | REAL, Docker local | Reconstrucción Healthy; 18 pruebas focales PASS y generador validado en runtime |

Las pruebas focales cubren conflictos, claves temporales, límites Unicode/bcrypt, cambio con versión obsoleta, error de contraseña actual, PDF ajeno sin proveedor, respuesta de buzón ajeno sin escritura, cierre prohibido y baja sin consultas destructivas. Son simulaciones de repositorio. El smoke aportado posteriormente acredita concurrencia SQL, revocación real y conservación de referencias para los escenarios del script.

## Ejecución real aportada por el usuario

El 2026-10-15 el usuario aportó la salida completa: imágenes API/web reconstruidas, tres contenedores Healthy, 41 pruebas del backend OK dentro de Docker y PASS C02. Copia de la salida: [docker-2026-10-15.txt](docker-2026-10-15.txt). El mensaje NativeCommandError corresponde a la salida de progreso por stderr y no impidió completar la ejecución. No se repitieron las pruebas.

## Comandos de reproducción (ya ejecutados)

El motor Docker no fue accesible desde esta sesión. Estos comandos reconstruyen API/web, conservan el volumen y crean fixtures sintéticos nuevos; no eliminan datos ni imprimen credenciales. Detenerse si un comando falla.

```powershell
docker compose up --build -d --wait api web
docker compose exec api python -m unittest discover -s tests -q
New-Item -ItemType Directory -Force work/c02 | Out-Null
docker compose --profile verification run --build --rm smoke python scripts/smoke_c02.py 2>&1 | Tee-Object work/c02/smoke-compose.log
```

Resultado esperado: `PASS C02`. El script verifica altas concurrentes (201/409), autorización de registro, roles, recuperación, revocación, objetos A/B y referencias de reporte/buzón tras bajas. No valida archivos PDF reales. Consume ocho logins por IP; ante 429 esperar cinco minutos antes de repetir, sin desactivar el limitador. Mantiene fixtures para inspección, sin registrar sus claves.

## Preview real después de reconstruir

1. Coordinador: perfil y cambio de contraseña; alta de tutor; temporal mostrada solo como resultado; buzón con acciones de personal.
2. Tutor: cambio obligatorio, recuperación de alumno y gestión individual. La confirmación de «Desactivar acceso» explica que conserva expediente y la diferencia frente a la baja de Dual; se canceló la operación de preview. No se mostró acción de cierre de período reservada al coordinador.
3. Alumno: perfil y buzón propio. El hilo permite responder y no expone acciones de marcar leído/cerrar reservadas al personal.
4. Navegación y estados principales fueron comprobados en el despliegue Docker local. No hubo cambios PDF en C02.

Drive/proveedor de archivos, PDF autorizado, calendario, versiones, firma, expediente integral y despliegue productivo NO_VERIFICADOS. Se preserva el estado de UI01.

## Revisión y acta de cierre

La revisión formal del diff, permisos, conservación histórica, contratos y evidencia concluyó APPROVED el 2026-10-15, sin defectos materiales. La parte técnica revisó código, contratos y resultados de pruebas; la parte visual recorrió coordinador, tutor y alumno en Docker local. Fue revisión del mismo agente, no independiente.

El responsable del proyecto otorgó aprobación de cierre de C02 el 2026-10-15, aclarando que su texto inicial `CLOSE C03` se refería a C02. Se marca DONE con las integraciones anteriores expresamente no verificadas. C03 queda solo documentada en DRAFT; no se implementó.
