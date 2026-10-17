# Evidencia C09 — Foro, buzón y plantillas

Fecha: 2026-10-17. Estado de la spec: DONE (cerrada el 2026-10-17; sin push).
Clases: REAL = HTTP, PostgreSQL y almacenamiento reales del Compose local (datos sintéticos); SIMULADA = pruebas con dobles; NO_VERIFICADA = no observado.

## Resumen por criterio

| Criterio | Clase | Fuente |
|---|---|---|
| C09-AC1 / AC-21 pareja Word/PDF atómica, vigente única, versiones inmutables | REAL; fallos del almacenamiento y de la base SIMULADA | `smoke_c09.py`, `test_c09_foro_plantillas.py` |
| C09-AC2 cargas maliciosas y permisos de publicación | REAL | smoke C09 |
| C09-AC3 / AC-22 foro como inicio y alumno sin anuncios por API | REAL parcial (coordinador y alumno en pantalla; tutor solo por prueba de `homeFor`) | smoke C09, navegador integrado, JS |
| C09-AC4 / AC-23 conversación alumno, tutor, coordinador, alumno | REAL | smoke C09 |
| C09-AC5 política del hilo cerrado (D1) | REAL | smoke C09 |
| C09-AC6 moderación de anuncios (D2) | REAL | smoke C09 |
| C09-AC7 recorridos visuales | REAL parcial | navegador integrado |

## Ejecuciones

- Backend `python -m unittest discover -s tests`: 237 pruebas OK (23 nuevas en `test_c09_foro_plantillas.py`: validación del DOCX con todas sus negativas, límites de carga y claves del almacenamiento sobre archivos reales, publicación atómica con fallos del segundo archivo y de la base, descarga con nombres generados, hilo cerrado, reapertura, enlace de hilos, moderación de anuncios y contratos SQL). Casos de uso SIMULADA; validación y almacenamiento REAL sobre archivos y ZIP en memoria o temporales.
- JS: 40/40 (la prueba de `homeFor` ahora espera `/foro`; una nueva de la descarga de plantilla). Contrato de integración: 75 llamadas del frontend contra 73 rutas. Vite build sin avisos nuevos propios (el aviso de región desplazable de `PlantillasDual` es el mismo patrón que en C08).
- Smoke C09 PASS con HTTP, PostgreSQL y almacenamiento reales, dos corridas: permisos (tutor y alumno 403, sin sesión 401, cualquier rol descarga); diez cargas inválidas rechazadas con 422 o 413 sin filas ni archivos sueltos; publicación válida con descarga byte a byte, nombres generados y metadatos sin claves de almacenamiento; segunda versión que reemplaza a la vigente dejando la anterior intacta y descargable con su hash; la base rechaza modificar, restablecer o borrar versiones; conversación completa con orden y roles; otro alumno 404; hilo cerrado 409 para los tres roles, marcar leído no lo reabre y la base rechaza la respuesta directa; hilo nuevo enlazado (ajeno 404, abierto 409); reapertura solo del personal e idempotente; anuncios: alumno 403, otro tutor 403, autor y coordinador eliminan, el anuncio se conserva con quién lo eliminó, deja de listarse y la base rechaza editarlo o restablecerlo.
- Regresión: smokes C01 a C08B PASS (C02 recorre el buzón y el foro y no requirió cambios).
- Migración `010_plantillas_foro.sql`: aplicada dos veces a la base local sin error; instalación en base nueva (esquema + 003 a 010, 010 dos veces) sin errores. La plantilla Word real y el PDF que estaban como archivos estáticos pasan la validación (el Excel se rechaza como Word).

## Visual REAL (navegador integrado, datos sintéticos)

Coordinador: el login termina en `/foro` y ve el icono de eliminar en todos los anuncios con el texto «(moderación)»; «Plantilla del reporte» muestra la versión vigente con Word y PDF, el formulario para publicar la pareja con nota opcional y el historial con la versión vigente marcada. Alumno: el login termina en `/foro`, sin iconos de eliminar; en «Buzón» el hilo cerrado muestra «Este hilo está cerrado y es de solo lectura. Si necesitas seguir con el tema, abre un hilo nuevo» y el botón «Abrir un hilo nuevo sobre este tema», que lleva al formulario con el aviso «Continúas el hilo cerrado «Duda de horas»» y la opción de quitar el enlace; en «Mis reportes» las plantillas son dos botones de la versión vigente (sin enlaces estáticos) y la ruta pública antigua ya no entrega el archivo.

## Defectos encontrados y corregidos durante la implementación

- Una cadena mal escapada dejó el modal del buzón con un error de sintaxis (el servidor de desarrollo lo mostró al cargar); se corrigió antes de la verificación.
- La fecha de publicación de la plantilla mostraba el día en UTC mientras el historial mostraba la hora local: ahora ambas usan fecha y hora locales.
- Marcar un hilo como leído habría reabierto uno cerrado (la consulta no filtraba el estado): ahora solo cambia hilos en «Enviado».

## NO_VERIFICADO / limitaciones

- Revisión independiente: no hubo; la revisión técnica fue del mismo agente (en ella se recorrió además el login de tutor en pantalla: aterriza en `/foro`, elimina solo sus anuncios y ve las acciones del buzón).
- No se subieron archivos desde el formulario del navegador (el navegador integrado no permite elegir archivos): la publicación se probó por HTTP real y la pantalla se vio con una versión publicada por la API; el estado «aún no hay plantilla vigente» solo está cubierto por pruebas.
- El login de tutor no se recorrió en pantalla; teclado completo, tema oscuro y móvil físico; apertura de la plantilla en Word real o en otros editores.
- La validación del DOCX no revisa relaciones externas ni objetos incrustados más allá de macros, rutas, tamaño y compresión; no hay análisis antivirus.
- La plantilla inicial la publica el coordinador; no hay carga automática de los archivos antiguos (siguen en el historial de git: `ute-dual-frontend/public/plantillas/`). El Excel de asistencia queda fuera del sistema (D3).
- Sin notificaciones por correo; Drive y cualquier proveedor externo siguen NO_VERIFICADOS. Respaldos y restauración son de C10 (DP-11).

## Decisiones aplicadas

D1 (hilo cerrado de solo lectura, cierre y reapertura solo del personal, hilo nuevo enlazado), D2 (autor y coordinador eliminan, eliminación lógica conservada, sin edición) y D3 (plantilla administrable Word + PDF; Excel fuera del sistema) del 2026-10-17, registradas en DP-09.

## Acta de cierre

La revisión técnica concluyó APPROVED el 2026-10-17 sin defectos materiales. El responsable otorgó aprobación de cierre el 2026-10-17 con `CLOSE C09 + NEXT SPEC`. C09 queda DONE con las limitaciones de la spec. El commit local de implementación se hizo con el cierre; no hay push.
