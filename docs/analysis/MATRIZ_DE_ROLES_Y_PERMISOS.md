# Roles y permisos objetivo

A = alumno, T = tutor académico, C = coordinador Dual. “Propio” siempre se comprueba en servidor. El nombre histórico de una ruta no concede permisos.

| ID | Operación | A | T | C |
|---|---|---|---|---|
| MP-01 | Login y cambio de contraseña | Propio | Propio | Propio |
| MP-02 | Registro institucional autorizado | Propio | No | No |
| MP-03 | Crear/listar/desactivar tutores | No | No | Sí |
| MP-04 | Recuperar acceso de alumno | No | Sí | No |
| MP-05 | Crear grupos/cargar alumnos/cambiar grupo | No | Sí | No |
| MP-06 | Empresas/incorporación/baja de Dual | No | Sí | No |
| MP-07 | Entregar y reenviar reportes | Propio y recepción abierta | No | No |
| MP-08 | Revisar/corregir/aprobar/rechazar | No | Todas las carreras | No |
| MP-09 | Cargar firma académica | No | Propia | No |
| MP-10 | Consultar expediente/PDF aprobado | Propio | Todas las carreras | Todas las carreras |
| MP-11 | Cerrar recepción/finalizar evaluación | No | No | Sí |
| MP-12 | Publicar plantillas | No | No | Sí |
| MP-13 | Descargar plantillas/ver foro | Sí | Sí | Sí |
| MP-14 | Publicar anuncios | No | Sí | Sí |
| MP-15 | Iniciar buzón | Propio | No | No |
| MP-16 | Ver/responder buzón | Hilos propios | Todos | Todos |
| MP-17 | Marcar leído/cerrar buzón | No | Sí | Sí |
| MP-18 | Abrir períodos (y consultar el período actual) | No | No | Sí (DP-04 resuelta el 2026-10-15: apertura manual por el coordinador) |

## Controles transversales

Autenticar y autorizar cada consulta, descarga y mutación, incluidos IDs adivinados, CSV y ZIP. No depender de ocultar botones. No exponer URLs públicas para documentos privados. Perfil con clave temporal solo accede al flujo necesario para cambiarla.

Revocar sesiones al recuperar credenciales o desactivar cuenta. Dar de baja de Dual no equivale a desactivar la cuenta: el alumno conserva consulta histórica y entregas anteriores permitidas.

Las capacidades de borrar publicaciones, administrar hilos cerrados, reabrir períodos o rectificar notas finales no se amplían por analogía: DP-09 / DP-10. Auditar mutaciones de revisión, cierre, plantilla, pertenencia y baja; no registrar claves ni contenido de documentos.
