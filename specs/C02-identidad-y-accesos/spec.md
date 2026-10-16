# C02 — Identidad y accesos

Estado: DONE
Fecha: 2026-10-14
Responsable de aprobación: responsable del proyecto
Dependencias: C01 DONE, aprobado y cerrado en este chat.
Aprobación de implementación: recibida mediante IMPLEMENT C02 en este chat el 2026-10-14. C02-slug se resuelve a C02-identidad-y-accesos. Sin DP bloqueantes: DRAFT → READY → IN_PROGRESS.

## Problema y resultado esperado

C01 ya demostró registro/login/perfil, administración de tutor, cambio temporal, revocación y baja lógica básica con API y PostgreSQL reales. C02 debe completar la cobertura y corregir brechas de identidad/autorización que se reproduzcan, reutilizando ese código y evidencia. No reconstruir funciones aprobadas ni asumir que el smoke prueba toda la matriz de permisos.

Resultado: tres roles con permisos efectivos en servidor, matrícula autorizada como condición de registro, recuperación temporal segura, sesiones revocadas y acceso exclusivo del alumno a objetos propios. Las bajas de cuentas no destruyen referencias históricas.

## Fuentes y alcance

- [Plan maestro](../../docs/construction/PLAN_MAESTRO.md): C02, US-01/03, AC-02/03/04.
- [Reglas](../../docs/analysis/REGLAS_DE_NEGOCIO.md): RN-01 a RN-04, RN-28/29 en autorización y conservación.
- [Roles y permisos](../../docs/analysis/MATRIZ_DE_ROLES_Y_PERMISOS.md): MP-01 a MP-04 y controles transversales; comprobar fronteras de las rutas existentes restantes.
- [Criterios](../../docs/analysis/CRITERIOS_DE_ACEPTACION.md), [contrato API](../../docs/analysis/CONTRATO_API.md), [arquitectura](../../docs/analysis/DECISIONES_DE_ARQUITECTURA.md): ADR-01/06/07/09.
- [Evidencia C01](../C01-base-local/evidencia.md), [UI01](../UI01-navegacion-y-cuenta/spec.md) como ajuste visual separado.

Incluye:
1. Inventariar rutas protegidas existentes y su permiso/propietario; localizar diferencias reproducibles frente a la matriz. No crear funcionalidades académicas ausentes.
2. Registro institucional: matrícula cargada/autorizada y correo coincidente; rechazar matrícula ajena/no autorizada, duplicados e intento de suministrar roles privilegiados. Probar concurrencia de altas para evitar errores 500 o cuentas duplicadas.
3. Administración de tutores solo por coordinador; recuperación de alumno solo por tutor. Claves temporales entregadas una vez y cambio obligatorio; nunca registros de secretos. No crear autorregistro privilegiado.
4. Verificar generación/validación de contraseñas y coherencia API/cliente con el algoritmo existente; tratar límites reales en bytes sin truncamiento silencioso. No cambiar algoritmo por estética.
5. Recuperación, cambio de contraseña y baja invalidan tokens anteriores. Cuenta temporal solo accede al flujo de cambio; comprobar API además de navegación. Probar errores y reintentos sin perder el control de acceso.
6. Autorización por objeto en rutas existentes de reportes, expediente, descargas y buzón: alumno A no lee ni modifica objetos de B. Tutor transversal sin restricciones inventadas por carrera. El servidor decide permisos, no botones ni claims suministrados por el cliente.
7. Baja de cuenta conserva fila y referencias. No confundir desactivar cuenta con baja de incorporación Dual, que se resolverá en C03 conservando consulta histórica.
8. Actualizar contratos, fixtures, pruebas y documentación afectados por correcciones. Preview de pantallas de acceso/recuperación/gestión que cambien.

Excluye: modelo/historia de grupos, incorporación y nomenclatura (C03), calendario, versiones de reportes, firma, cierre académico, expediente integral, proveedor de archivos, conversación completa del buzón y publicación productiva. No cerrar UI01 automáticamente ni ejecutar limpiezas históricas.

## Decisiones

Confirmadas: tres roles, tutores transversales, registro autorizado, sin verificación/recuperación por email, cambio temporal obligatorio y bajas sin borrado.
Propuestas técnicas para aprobación: conservar endpoints y arquitectura; usar versión de credenciales existente; autorización de objeto en consultas/casos de uso; 404 para objeto ajeno o inexistente, 403 para rol sin permiso y 401 para sesión inválida. Mantener errores de validación coherentes sin exponer SQL/secretos.
Pendientes bloqueantes de negocio: ninguna. DP-01 a DP-11 pertenecen a incrementos posteriores según el plan. DP-05 no bloquea seguridad de identidad; usar fixtures con esquema actual sin decidir códigos de carreras ni promoción.

## Contratos y cambios previstos

Conservar POST /auth/register y /auth/login; GET /auth/me; POST /auth/cambiar-password; POST/GET /auth/tutores; DELETE /auth/tutores/{usuario_id}; POST /auth/alumnos/{matricula}/password-provisional. GET /auth/me conserva dual_activo como booleano independiente de empresa. DELETE de tutor permanece baja lógica.

No ampliar campos/roles aceptados del cliente ni exponer hashes/secretos en listados. Las respuestas de alta/recuperación temporal son el único punto de entrega de la clave temporal. Mantener DTO/OpenAPI y consumidor juntos si se demuestra necesidad de cambiar contrato. Antes de alterar rutas de objetos, documentar el mapa exacto ruta→permiso→propiedad y sus casos negativos.

Archivos previstos: ute-api-backend/app/application/use_cases/auth.py, presentation/api/routers/auth.py, domain/passwords.py, infrastructure/database/queries/auth.py y pruebas; guardas/consultas de objetos afectados; frontend application/use-cases/auth.js, repositorios, permisos y páginas de acceso/gestión/recuperación. No reescrituras amplias. SQL solo si una brecha probada lo exige, con cambio aditivo y destino local identificado; conservar volumen y datos C01.

## Verificación

| AC local | Recorrido | Evidencia requerida | Estado |
|---|---|---|---|
| C02-AC1 / AC-02 | Matrícula autorizada registra; ajena/no autorizada/correo discrepante y roles inyectados se rechazan; duplicado/concurrencia controlados | HTTP + PostgreSQL reales, cuentas sintéticas | PASS real: smoke C02 2026-10-15 |
| C02-AC2 / AC-03 | Alta de tutor y recuperación de alumno por roles permitidos; temporal no accede a recursos hasta cambiar | API real y navegador | PASS real: smoke C02 y recorrido visual 2026-10-15 |
| C02-AC3 / AC-03 | Tokens anteriores fallan tras cambio, recuperación y baja; clave temporal satisface validadores | API real y pruebas focales | PASS smoke real C02 y pruebas focales |
| C02-AC4 / AC-04 | Dos alumnos: sustituir IDs/matrículas en lectura, descarga y mutación no concede acceso cruzado; personal según matriz | Rutas reales con PostgreSQL; archivos sintéticos cuando aplique | PASS negativos y lecturas del smoke C02; PDF autorizado/proveedor e integral pendientes C05/C08 |
| C02-AC5 / RN-29 | Baja conserva cuenta y referencias a objetos previos; acceso de cuenta desactivada denegado | Comparación SQL antes/después sobre fixtures locales | PASS real C02: filas y referencias conservadas, sesiones revocadas |
| C02-AC6 | Login, temporal, recuperación y gestión muestran errores/resultado sin secretos persistentes ni navegación privilegiada | Preview navegador; build y pruebas afectadas | PASS visual 2026-10-15; build y pruebas PASS |

Reutilizar evidencia C01 cuando código/escenario sigan válidos. Añadir pruebas de comportamiento, no espejos de implementación. No repetir smoke sin cambios o duda concreta. Para archivos, una negativa de autorización debe ocurrir antes de consultar proveedor; eso no acredita una descarga real autorizada. Si no puede comprobarse el acceso autorizado, registrar su dependencia de C05/C08 y no afirmar AC-04 integral.

## Evidencia de implementación y revisión

Implementación autorizada y aplicada desde el 2026-10-14. Ver [entregables, pruebas, preview y limitaciones](evidencia.md) y [mapa exacto de rutas](rutas.md). Smoke HTTP/PostgreSQL C02 PASS aportado por el usuario el 2026-10-15; backend completo 41 pruebas PASS, frontend 21 pruebas PASS y build Vite PASS. Después del ajuste solicitado a temporales de 12 caracteres exactos, el usuario reconstruyó los contenedores: 18 pruebas focales PASS y validación en runtime PASS. La revisión formal del diff y los recorridos visuales de coordinador, tutor y alumno concluyó APPROVED sin defectos materiales. Revisión realizada por el mismo agente; no es independiente. Descarga PDF autorizada e integraciones excluidas permanecen NO_VERIFICADAS.

## Aprobaciones y cierre

Implementación: autorizada y completada dentro del alcance.
Cierre: aprobado por el responsable del proyecto el 2026-10-15 mediante `CLOSE C02 + NEXT SPEC`, después de aclarar que la referencia inicial a C03 era un error. Criterios con evidencia suficiente y revisión técnica/visual APPROVED.
Resumen final: identidad y accesos de los tres roles, registro autorizado, temporales y revocación, baja lógica, autorización por objeto y contratos asociados entregados. Limitaciones: proveedor/Drive, PDF autorizado, calendario, firma, versiones, expediente integral y producción no se comprobaron porque pertenecen a incrementos posteriores.
Siguiente: [C03 — Grupos e incorporación](../C03-grupos-e-incorporacion/spec.md), preparado en DRAFT; DP-05 bloquea READY.
Commit/push: no autorizados.
