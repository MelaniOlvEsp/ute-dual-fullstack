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
| GET `/dual/alumno/expediente` | `get_alumno_dual` | A: la matrícula sale de la sesión, nunca de un parámetro; sustituye al retirado `/dual/alumno/mis-reportes` (C08). |
| GET `/dual/alumno/obligaciones` | `get_alumno_dual` | A: matrícula de sesión (C04). |
| POST `/dual/alumno/obligaciones/{obligacion_id}/entrega` | `get_alumno_dual` | A: solo obligaciones propias; ajena o inexistente 404; período abierto (C05, DP-13). La ruta heredada `POST /dual/alumno/` y `GET /dual/alumno/semana-actual` se retiraron en C05. |
| GET `/dual/alumno/reportes/{reporte_id}/versiones` | `get_alumno_dual` | A: solo reportes propios; ajeno 404 (C05). |
| GET `/dual/alumno/reportes/{reporte_id}/versiones/{numero}/pdf` | `get_alumno_dual` | A: solo versiones propias; ajena 404 (C05). `?documento=firmado` solo si la versión fue aprobada (C06). |
| GET `/dual/alumno/paquete` | `get_alumno_dual` | A: solo su propio ZIP, durante 7 días desde la finalización del período (C08); sustituye al retirado `/dual/alumno/reporte/{id}/pdf`. |
| GET `/dual/tutor/reportes` | `get_coordinador_dual` | T transversal; firma por usuario. Excepción cierre: C. Abrir período y consultar el período actual: C (corregido en C04 por DP-04; antes de C04 eran de T). |
| GET `/dual/tutor/reportes/{reporte_id}` | `get_coordinador_dual` | T transversal (C06): detalle con versiones, decisiones y correcciones; A y C 403. |
| POST `/dual/tutor/reportes/{reporte_id}/versiones/{numero}/revision` | `get_coordinador_dual` | T transversal (C06, MP-08): aprobar con firma o rechazar con observación una versión concreta; A y C 403. Sustituye al retirado `PATCH /dual/tutor/reportes/{reporte_id}`. |
| GET `/dual/tutor/reportes/{reporte_id}/versiones/{numero}/pdf` | `get_coordinador_dual` | T transversal (C06): original o `?documento=firmado` de una versión; A y C 403. |
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
| GET `/dual/tutor/periodos` y `/dual/tutor/periodos/{periodo_id}/resumen` | `get_consulta_periodos` | T y C consultan el estado y los promedios de los períodos (C07). |
| POST `/dual/tutor/periodos/{periodo_id}/cierre-recepcion` y `/finalizacion` | `get_coordinator` | Solo C (MP-11, C07); T y A 403. Sustituyen al retirado `POST /dual/tutor/cierre` (cierre por etiqueta). |
| GET `/dual/carrera/paquetes/alumno/{matricula}` y `/dual/carrera/paquetes/carrera/{codigo}` | `get_tutor_academico` | Solo T (C08, DP-14): paquete ZIP de un período finalizado; C y A 403. Sustituyen al retirado `/dual/tutor/reporte/{id}/pdf`. |
| POST `/dual/tutor/firma` | `get_coordinador_dual` | T transversal; firma por usuario. Excepción cierre: C. Abrir período y consultar el período actual: C (corregido en C04 por DP-04; antes de C04 eran de T). |
| GET `/dual/tutor/firma` | `get_coordinador_dual` | T transversal; firma por usuario. Excepción cierre: C. Abrir período y consultar el período actual: C (corregido en C04 por DP-04; antes de C04 eran de T). |
| GET `/dual/carrera/periodos` | `get_coordinador_carrera` | Consulta T/C transversal; edición y grupos T. DELETE desactiva acceso, conserva expediente. |
| GET `/dual/carrera/alumnos` | `get_coordinador_carrera` | Consulta T/C transversal; edición y grupos T. DELETE desactiva acceso, conserva expediente. |
| GET `/dual/carrera/alumnos/{matricula}/expediente` | `get_coordinador_carrera` | Consulta T/C transversal (C08); A 403. Sustituye al retirado `/alumnos/{matricula}/reportes`. |
| GET `/dual/carrera/reportes/{reporte_id}/versiones/{numero}/pdf` | `get_coordinador_carrera` | Consulta T/C transversal (C08): solo versiones aprobadas (original o firmado); A 403. Sustituye al retirado `/reporte/{id}/pdf`. |
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
- El alumno no tiene acceso al expediente administrativo: consulta lo propio mediante `/dual/alumno/expediente` y `/dual/alumno/paquete` (C08; la ruta heredada `/mis-reportes` se retiró).
- Entrega no acepta matrícula externa: usa la sesión; revisión de reportes es T. No se ejecuta entrega/firma/descarga autorizada con proveedor en C02.
- MP-11 se aplica al guard existente; no se afirma que el cierre académico cumpla C07. MP-12/13 (plantillas) y DP-04/09/10 se completan en sus incrementos.
- Revisión técnica del mismo agente, no revisión independiente ni aprobación de cierre.
