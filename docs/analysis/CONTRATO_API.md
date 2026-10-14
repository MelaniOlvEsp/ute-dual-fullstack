# Contrato API: existente y objetivo

Estado: inventario estático y diseño PROPUESTO. No afirmar que las nuevas rutas estén implementadas. Fuente existente: routers en ute-api-clean/app/presentation/api/routers, route_contract.json y repositorios de ute-dual-frontend/src/infrastructure/repositories.

## Inventario actual

| Familia | Rutas principales existentes | Cambio requerido |
|---|---|---|
| Identidad | POST /auth/register, /login, /cambiar-password; GET /auth/me | Alinear esquema, sesiones y tres roles. |
| Tutores | POST/GET /auth/tutores; DELETE /auth/tutores/{usuario_id} | Baja lógica y revocación; confirmar contrato compatible. |
| Recuperación | POST /auth/alumnos/{matricula}/password-provisional | Conservar control tutor y cambio forzoso. |
| Alumno | POST /dual/alumno/; GET /dual/alumno/mis-reportes, /semana-actual | Sustituir selector secuencial por obligaciones independientes. |
| Revisión | GET/PATCH /dual/tutor/reportes[/{reporte_id}] | Versiones, enteros, trazabilidad y firma; corrección DP-02. |
| Empresa | /dual/tutor/empresas, /asignaciones, /alumnos/{matricula} | Fecha real de inicio/baja y continuidad entre períodos. |
| Calendario | /dual/tutor/cuatrimestre-actual, /abrir-cuatrimestre, /cierre | Separar recepción/evaluación y autorización coordinador. |
| Firma | POST/GET /dual/tutor/firma | Versionar sin alterar firmados históricos. |
| Grupos/expediente | /dual/carrera/grupos, /alumnos, /periodos | Historia por período y consulta propia del alumno. |
| Descargas | /dual/alumno/reporte/{id}/pdf; equivalentes tutor/carrera; exportar-csv, exportar-zip | Autorización de objeto y contenido binario privado. |
| Foro | /foro/publicaciones y reacciones | Validar lectura/publicación y navegación. |
| Buzón | /foro/buzon/, /mios, /{id}, respuestas, leído y cierre | Probar conversación completa y autorización. |

Los prefijos carrera/coordinador_dual heredados no representan roles nuevos. No renombrar todo sin beneficio: adaptar cliente y servidor en el mismo incremento.

## Contrato objetivo a concretar en cada spec

| Operación propuesta | Entrada esencial | Resultado/garantía | Spec |
|---|---|---|---|
| Consultar obligaciones | período opcional, identidad en sesión | ID, intervalo, estado, atraso, permiso de entregar y motivo de bloqueo | C04 |
| Entregar versión | obligación_id, fechas declaradas, nota entera, PDF multipart | reporte_id, version_id y pendiente de revisión; 201 solo tras persistencia | C05 |
| Revisar versión | version_id, acción, fechas/nota validadas, nota de rechazo, versión esperada | Revisión trazable, sin sobrescribir versión nueva por concurrencia | C06 |
| Cerrar recepción | periodo_id y confirmación del coordinador | Cierre idempotente con autor/instante, mantiene revisión | C07 |
| Finalizar evaluación | periodo_id | Falla si hay pendientes; congela resultados atómicamente | C07 |
| Consultar expediente | alumno autorizado, período opcional | Grupo histórico, aprobados, promedio, cantidad y carácter provisional/final | C08 |
| Descargar documento | ID autorizado, original/firmado según permisos | application/pdf y nombre seguro; nunca ruta del disco ni token Drive | C05/C08 |
| Publicar plantillas | Word/PDF y metadatos | Versión vigente completa, anterior conservada | C09 |

Estas son operaciones, no rutas definitivas. Antes de implementar cada spec debe fijar método, ruta, esquema, ejemplos y errores; actualizar OpenAPI/fixtures/repositorios y pruebas en el mismo cambio.

## Reglas de contrato

- Cliente no decide alumno propietario ni período escribiendo una etiqueta arbitraria.
- No inferir período objetivo de “único ciclo abierto”; usar obligación/período explícito.
- Fechas ISO YYYY-MM-DD; instantes con offset. Nota estrictamente entera, no truncar 8.5.
- Propuesta de error: código estable, mensaje y detalles de campos; nunca SQL, token ni stack al usuario.
- 401 sin sesión; 403 sin permiso; 404 objeto inexistente o ajeno según política consistente; 409 estado/conflicto; 413 tamaño; 422 datos inválidos.
- Reintento de cierre no duplica efectos. Doble click al entregar no crea dos versiones independientes aceptadas.
- Listados deben tener filtros y límites/paginación acordes al volumen; no descargar todos los PDFs al abrir tablero.
- Cambios incompatibles requieren actualización conjunta de backend/frontend y datos sintéticos.

Ejemplo conceptual de obligación: id, inicio_semana, fin_semana, periodo_id, estado_entrega, atrasado, puede_entregar, motivo_bloqueo. Diferenciar faltante de reporte pendiente de revisión; ningún “Pendiente” ambiguo en UI nueva.
