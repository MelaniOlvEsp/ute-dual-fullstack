# C02 — Mapa de rutas y autorización

Inventario estático del código del 2026-10-14. No acredita ejecución HTTP. A = alumno, T = tutor, C = coordinador. Todos los guards protegidos consultan estado y versión de credenciales en BD; la cuenta temporal solo puede cambiar su contraseña.

| Método/ruta | Dependencia declarada | Propiedad y límite |
|---|---|---|
| POST `/auth/register` | `Público` | Identidad propia; tutores C; recuperación T. Registro autorizado público. |
| POST `/auth/login` | `limitar_intentos('login', max_intentos=8, ventana_segundos=300)` | Identidad propia; tutores C; recuperación T. Registro autorizado público. |
| GET `/auth/me` | `get_current_user` | Identidad propia; tutores C; recuperación T. Registro autorizado público. |
| POST `/auth/cambiar-password` | `get_change_password_user` | Identidad propia; tutores C; recuperación T. Registro autorizado público. |
| POST `/auth/tutores` | `get_coordinator` | Identidad propia; tutores C; recuperación T. Registro autorizado público. |
| GET `/auth/tutores` | `get_coordinator` | Identidad propia; tutores C; recuperación T. Registro autorizado público. |
| DELETE `/auth/tutores/{usuario_id}` | `get_coordinator` | Identidad propia; tutores C; recuperación T. Registro autorizado público. |
| POST `/auth/alumnos/{matricula}/password-provisional` | `get_tutor` | Identidad propia; tutores C; recuperación T. Registro autorizado público. |
| POST `/dual/alumno/` | `get_alumno_dual` | A: matrícula de sesión; PDF compara propietario antes del proveedor. |
| GET `/dual/alumno/mis-reportes` | `get_alumno_dual` | A: matrícula de sesión; PDF compara propietario antes del proveedor. |
| GET `/dual/alumno/semana-actual` | `get_alumno_dual` | A: matrícula de sesión; PDF compara propietario antes del proveedor. |
| GET `/dual/alumno/reporte/{reporte_id}/pdf` | `get_alumno_dual` | A: matrícula de sesión; PDF compara propietario antes del proveedor. |
| GET `/dual/tutor/reportes` | `get_coordinador_dual` | T transversal; firma por usuario. Excepción cierre: C. Abrir período y consultar el período actual: C (corregido en C04 por DP-04; antes de C04 eran de T). |
| PATCH `/dual/tutor/reportes/{reporte_id}` | `get_coordinador_dual` | T transversal; firma por usuario. Excepción cierre: C. Abrir período y consultar el período actual: C (corregido en C04 por DP-04; antes de C04 eran de T). |
| GET `/dual/tutor/empresas` | `get_coordinador_dual` | T transversal; firma por usuario. Excepción cierre: C. Abrir período y consultar el período actual: C (corregido en C04 por DP-04; antes de C04 eran de T). |
| POST `/dual/tutor/empresas` | `get_coordinador_dual` | T transversal; firma por usuario. Excepción cierre: C. Abrir período y consultar el período actual: C (corregido en C04 por DP-04; antes de C04 eran de T). |
| GET `/dual/tutor/asignaciones` | `get_coordinador_dual` | T transversal; firma por usuario. Excepción cierre: C. Abrir período y consultar el período actual: C (corregido en C04 por DP-04; antes de C04 eran de T). |
| POST `/dual/tutor/asignaciones` | `get_coordinador_dual` | T transversal; firma por usuario. Excepción cierre: C. Abrir período y consultar el período actual: C (corregido en C04 por DP-04; antes de C04 eran de T). |
| GET `/dual/tutor/alumnos/{matricula}` | `get_coordinador_dual` | T transversal; firma por usuario. Excepción cierre: C. Abrir período y consultar el período actual: C (corregido en C04 por DP-04; antes de C04 eran de T). |
| PATCH `/dual/tutor/alumnos/{matricula}` | `get_coordinador_dual` | T transversal; firma por usuario. Excepción cierre: C. Abrir período y consultar el período actual: C (corregido en C04 por DP-04; antes de C04 eran de T). |
| GET `/dual/tutor/alumnos-sin-reporte` | `get_coordinador_dual` | T transversal; firma por usuario. Excepción cierre: C. Abrir período y consultar el período actual: C (corregido en C04 por DP-04; antes de C04 eran de T). |
| GET `/dual/tutor/alumnos-atrasados` | `get_coordinador_dual` | T transversal; firma por usuario. Excepción cierre: C. Abrir período y consultar el período actual: C (corregido en C04 por DP-04; antes de C04 eran de T). |
| GET `/dual/tutor/cuatrimestre-actual` | `get_coordinator` | T transversal; firma por usuario. Excepción cierre: C. Abrir período y consultar el período actual: C (corregido en C04 por DP-04; antes de C04 eran de T). |
| POST `/dual/tutor/abrir-cuatrimestre` | `get_coordinator` | T transversal; firma por usuario. Excepción cierre: C. Abrir período y consultar el período actual: C (corregido en C04 por DP-04; antes de C04 eran de T). |
| POST `/dual/tutor/cierre` | `get_coordinator` | T transversal; firma por usuario. Excepción cierre: C. Abrir período y consultar el período actual: C (corregido en C04 por DP-04; antes de C04 eran de T). |
| GET `/dual/tutor/reporte/{reporte_id}/pdf` | `get_coordinador_dual` | T transversal; firma por usuario. Excepción cierre: C. Abrir período y consultar el período actual: C (corregido en C04 por DP-04; antes de C04 eran de T). |
| POST `/dual/tutor/firma` | `get_coordinador_dual` | T transversal; firma por usuario. Excepción cierre: C. Abrir período y consultar el período actual: C (corregido en C04 por DP-04; antes de C04 eran de T). |
| GET `/dual/tutor/firma` | `get_coordinador_dual` | T transversal; firma por usuario. Excepción cierre: C. Abrir período y consultar el período actual: C (corregido en C04 por DP-04; antes de C04 eran de T). |
| GET `/dual/carrera/periodos` | `get_coordinador_carrera` | Consulta T/C transversal; edición y grupos T. DELETE desactiva acceso, conserva expediente. |
| GET `/dual/carrera/alumnos` | `get_coordinador_carrera` | Consulta T/C transversal; edición y grupos T. DELETE desactiva acceso, conserva expediente. |
| GET `/dual/carrera/alumnos/{matricula}/reportes` | `get_coordinador_carrera` | Consulta T/C transversal; edición y grupos T. DELETE desactiva acceso, conserva expediente. |
| GET `/dual/carrera/reporte/{reporte_id}/pdf` | `get_coordinador_carrera` | Consulta T/C transversal; edición y grupos T. DELETE desactiva acceso, conserva expediente. |
| GET `/dual/carrera/alumnos/{matricula}/exportar-csv` | `get_coordinador_carrera` | Consulta T/C transversal; edición y grupos T. DELETE desactiva acceso, conserva expediente. |
| GET `/dual/carrera/alumnos/{matricula}/exportar-zip` | `get_coordinador_carrera` | Consulta T/C transversal; edición y grupos T. DELETE desactiva acceso, conserva expediente. |
| GET `/dual/carrera/grupos` | `get_tutor_academico` | Consulta T/C transversal; edición y grupos T. DELETE desactiva acceso, conserva expediente. |
| POST `/dual/carrera/grupos` | `get_tutor_academico` | Consulta T/C transversal; edición y grupos T. DELETE desactiva acceso, conserva expediente. |
| POST `/dual/carrera/grupos/{grupo_id}/alumnos` | `get_tutor_academico` | Consulta T/C transversal; edición y grupos T. DELETE desactiva acceso, conserva expediente. |
| POST `/dual/carrera/grupos/{grupo_id}/alumnos/individual` | `get_tutor_academico` | Consulta T/C transversal; edición y grupos T. DELETE desactiva acceso, conserva expediente. |
| PATCH `/dual/carrera/alumnos/{matricula}` | `get_tutor_academico` | Consulta T/C transversal; edición y grupos T. DELETE desactiva acceso, conserva expediente. |
| DELETE `/dual/carrera/alumnos/{matricula}` | `get_tutor_academico` | Consulta T/C transversal; edición y grupos T. DELETE desactiva acceso, conserva expediente. |
| POST `/foro/publicaciones` | `get_publicador` | Lectura autenticada; publicar/borrar T/C; reacciones A por usuario. DP-09 no se redefine. |
| GET `/foro/publicaciones` | `get_current_user` | Lectura autenticada; publicar/borrar T/C; reacciones A por usuario. DP-09 no se redefine. |
| DELETE `/foro/publicaciones/{publicacion_id}` | `get_publicador` | Lectura autenticada; publicar/borrar T/C; reacciones A por usuario. DP-09 no se redefine. |
| POST `/foro/publicaciones/{publicacion_id}/reaccion` | `get_reactor` | Lectura autenticada; publicar/borrar T/C; reacciones A por usuario. DP-09 no se redefine. |
| POST `/foro/buzon/` | `get_remitente` | Crear/míos A; detalle/respuesta propietario o T/C; listado/leído/cierre T/C. |
| GET `/foro/buzon/` | `get_current_user` | Crear/míos A; detalle/respuesta propietario o T/C; listado/leído/cierre T/C. |
| GET `/foro/buzon/mios` | `get_remitente` | Crear/míos A; detalle/respuesta propietario o T/C; listado/leído/cierre T/C. |
| GET `/foro/buzon/{mensaje_id}` | `get_current_user` | Crear/míos A; detalle/respuesta propietario o T/C; listado/leído/cierre T/C. |
| POST `/foro/buzon/{mensaje_id}/respuestas` | `get_current_user` | Crear/míos A; detalle/respuesta propietario o T/C; listado/leído/cierre T/C. |
| PATCH `/foro/buzon/{mensaje_id}/leido` | `get_current_user` | Crear/míos A; detalle/respuesta propietario o T/C; listado/leído/cierre T/C. |
| PATCH `/foro/buzon/{mensaje_id}/cerrar` | `get_current_user` | Crear/míos A; detalle/respuesta propietario o T/C; listado/leído/cierre T/C. |

## Evidencia negativa y límites

- `tests/test_c02_access.py`: PDF ajeno 404 sin proveedor; respuesta de buzón ajeno 404 sin escritura; cierre por alumno 403; recuperación/cambio y altas con repositorio simulado.
- `tests/test_api_permissions.py`: dependencias estáticas para administración, edición y cierre.
- `scripts/smoke_c02.py`: HTTP + PostgreSQL preparados para comparar A/B, PDF ajeno, lectura/mutación de expediente, CSV/ZIP, buzón, recuperación, cierre por tutor y referencias después de baja. PASS real aportado por usuario el 2026-10-15; ver evidencia.md.
- El alumno no tiene acceso al expediente administrativo: consulta sus reportes mediante `/dual/alumno/mis-reportes`; expediente propio integral corresponde a C08.
- Entrega no acepta matrícula externa: usa la sesión; revisión de reportes es T. No se ejecuta entrega/firma/descarga autorizada con proveedor en C02.
- MP-11 se aplica al guard existente; no se afirma que el cierre académico cumpla C07. MP-12/13 (plantillas) y DP-04/09/10 se completan en sus incrementos.
- Revisión técnica del mismo agente, no revisión independiente ni aprobación de cierre.
