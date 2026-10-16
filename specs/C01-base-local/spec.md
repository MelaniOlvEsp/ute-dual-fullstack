# C01 — Base local reproducible

Estado: DONE
Fecha: 2026-10-14
Aprobación de implementación: recibida el 2026-10-14 mediante IMPLEMENT C01. C01-slug se resuelve a C01-base-local.
Dependencias: ninguna
Responsable de aprobación: responsable del proyecto

## Problema y resultado esperado

Hay código y una propuesta de esquema que no coinciden: consultas auth utilizan email_verificado y eliminación física de tutor; esquema nuevo elimina ese campo y describe baja lógica. No hay evidencia actual de instalación/compilación integral. Antes de cambiar calendario se necesita una base local verificable.

Resultado: arranque reproducible sobre BD nueva con fixtures sintéticos y diagnóstico real de pruebas, sin afirmar que el flujo completo ya está terminado.

## Fuentes

- [Estado y brechas](../../docs/analysis/ESTADO_ACTUAL_Y_BRECHAS.md)
- [Arquitectura](../../docs/analysis/DECISIONES_DE_ARQUITECTURA.md)
- [Reglas](../../docs/analysis/REGLAS_DE_NEGOCIO.md): RN-01, RN-29
- [Aceptación](../../docs/analysis/CRITERIOS_DE_ACEPTACION.md): AC-01
- [Validación local](../../docs/construction/VALIDACION_Y_OPERACION_LOCAL.md)
- [Plan maestro](../../docs/construction/PLAN_MAESTRO.md)

## Incluye

1. Inventario de dependencias, comandos y estructura real; revisar instrucciones de repositorio y estado Git si existe.
2. Ejecutar pruebas existentes y build con dependencias instaladas de forma reproducible. Registrar fallos de línea base antes de corregir.
3. Definir un esquema de arranque canónico para BD nueva; reconciliar consultas/columnas de identidad con demo sin resucitar verificación por email.
4. Crear fixtures sintéticos y comando administrativo local para primer coordinador, sin autorregistro público privilegiado.
5. Configuración de ejemplo sin secretos y guía de arranque API/frontend/PostgreSQL.
6. Smoke test real contra PostgreSQL: arranque, consulta de salud si existe o equivalente, login de fixture y perfil autorizado.
7. Documentar bloqueos del resto del producto como brechas; corregir solo los necesarios para base reproducible y pruebas del alcance.

## Excluye

No diseñar semanas basándose en supuestos; no implementar historial completo, cierre nuevo, firma nueva, buzón nuevo o plantillas administrables. No ejecutar migraciones sobre bases existentes, scripts destructivos ni despliegue. No renovar credenciales personales sin necesidad/autorización. No comprometer proveedor productivo.

## Decisiones de implementación propuestas

Conservar FastAPI/Svelte y roles JSONB mientras sean compatibles; no migrar a rol text solo por estética. La base vacía permite un esquema canónico nuevo; scripts anteriores quedan identificados como históricos. Dependencias de Drive no deben impedir verificar identidad local, sin declarar integración validada.

No hay DP de negocio bloqueante para este alcance. Destino concreto de PostgreSQL y disponibilidad de runtime se inspeccionan antes de actuar. Si no hay instancia autorizada, preparar configuración/script y pedir solo información o permiso indispensable; no marcar AC-01 aprobado.

## Archivos previstos

database: esquema de arranque y README con ruta inequívoca.
ute-api-backend: consultas/configuración/bootstrap y pruebas afectadas por incompatibilidad.
ute-dual-frontend: instalación/configuración solo si necesita corrección para build.
README_INTEGRACION.md: instrucciones verificadas, no resultados heredados.
No modificar masivamente archivos fuera del alcance.

## Criterios locales de cierre

| ID | Comprobación | Evidencia requerida |
|---|---|---|
| C01-AC1 | Instalación en BD vacía identificada sin depender de tablas previas | PostgreSQL REAL |
| C01-AC2 | Login/perfil de fixture no usa columna inexistente ni concede roles extra | API + PostgreSQL REAL |
| C01-AC3 | Frontend compila y sirve pantalla de acceso | Build REAL y navegador |
| C01-AC4 | Pruebas existentes ejecutadas y fallos clasificados | Comandos y resultados actuales |
| C01-AC5 | Arranque documentado y configuración sin secretos | Inspección y recorrido reproducido |

Un fallo preexistente fuera de alcance se registra con impacto y siguiente incremento; no se declara “suite aprobada” si falla. Si impide C01-AC1/2/3, se corrige o C01 permanece sin cierre.

## Evidencia

Entrega revisada y aceptada. Ver [evidencia y cierre](evidencia.md): arranque Compose en volumen nuevo, smoke HTTP/PostgreSQL PASS, pruebas de host, compilación y preview de acceso. Las limitaciones del producto completo permanecen explícitas.

## Revisión y cierre

Revisión: APPROVED en la última REVIEW / PREVIEW C01 de este chat; revisión técnica del diff y evidencia, preview de acceso y evidencia visual previa del coordinador. Mismo agente, no independiente.
Aprobación de cierre: otorgada explícitamente por el usuario el 2026-10-14 mediante CLOSE C01 + NEXT SPEC. Condición satisfecha: revisión APPROVED y evidencia suficiente para C01-AC1 a C01-AC5.
Siguiente: [C02 — Identidad y accesos](../C02-identidad-y-accesos/spec.md), DRAFT; no implementada por este cierre.
Commit/push: no autorizados.

## Registro de inicio

2026-10-14: DRAFT → READY por autorización explícita del usuario → IN_PROGRESS al iniciar implementación. No hay DP bloqueante para C01.

### Ajuste autorizado durante C01

El usuario solicita entorno local con Docker como PC-Refresh. Docker Compose pasa a ser la ruta canónica: PostgreSQL, API y frontend aislados, con volumen propio y puertos loopback. Se conserva el stack FastAPI/Svelte; no se copia el worker ni almacenamiento de PC-Refresh. Los intentos iniciales de PostgreSQL nativo son evidencia de diagnóstico, no el entorno de entrega. El cierre de C01 requiere comprobar el entorno Compose real.


## Cierre aprobado — 2026-10-14

IN_PROGRESS → DONE por aprobación humana posterior a revisión APPROVED. Entregado: base Docker con PostgreSQL/API/frontend, esquema canónico y usuario de aplicación, configuración local, bootstrap administrativo y fixtures, identidad compatible y smoke real. La corrección de dual_activo fue revisada con build y contrato API real.

No implica cierre de UI01, validación del producto completo ni autorización de commit/push. Historial integral, Drive, PDFs, firmas, calendario y restauración quedan para sus incrementos.
