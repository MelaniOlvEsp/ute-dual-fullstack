# Evidencia C12 — Accesibilidad estructural

Fecha: 2026-10-17. Estado de la spec: DONE (cerrada el 2026-10-17; sin commit ni push).
Clases: REAL = navegador integrado contra el sistema real con cuentas sintéticas y axe-core 4.10.2 (todas las reglas, no solo contraste); SIMULADA = comprobación estática de los `.svelte`; NO_VERIFICADA = no observado.

## Resumen por criterio

| Criterio | Clase | Fuente |
|---|---|---|
| C12-AC1 cero violaciones de axe en pantallas y estados de los tres roles | REAL: 0 violaciones (reglas WCAG y de buenas prácticas), 0 desbordes, 0 controles sin foco y 0 sin etiqueta en: sesión, registro y 404; alumno (foro, reportes, versiones abiertas, expediente, visor del PDF) a 320 y 1280 px en claro y oscuro; coordinador (foro, períodos, tutores, plantilla, directorio, expediente, diálogo de depuración, buzón con un hilo abierto) a 1280 px en claro y oscuro (el buzón también a 320 px); tutor (7 pantallas, revisión, buzón con un hilo abierto y expediente) a 1280 px en claro y oscuro, repetido tras la última corrección, y (con el perfil) a 320 px en claro | `tools/auditoria-ui.js` |
| C12-AC2 nombre accesible en cada lista desplegable y `main` + `h1` por página | REAL (axe) y SIMULADA (`tests/estructura.test.js`, 3 pruebas) | auditoría y prueba estática |
| C12-AC3 cobertura de estados antes sin auditar | REAL: diálogo de depuración, buzón con hilo abierto, visor del PDF, versiones abiertas y alumno y períodos a 1280 px incluidos | auditoría con rutas `preparar` |
| C12-AC4 recorridos con lector de pantalla | NO_VERIFICADA: el responsable decidió el 2026-10-17 no hacer la prueba con lector de pantalla; la guía queda por si se hace después | [GUIA_PRUEBA_LECTOR_DE_PANTALLA.md](../../docs/construction/GUIA_PRUEBA_LECTOR_DE_PANTALLA.md) |
| C12-AC5 sin regresión | REAL: 48 pruebas de frontend (45 + 3), 1 de contrato, `smoke_c10.py` PASS, compilación de Vite con las mismas advertencias previas | pruebas y smoke |

## Línea base (axe, al empezar C12) y qué cambió

- **H4 (`select-name`):** 3 listas sin nombre en la bandeja del tutor y 2 en el directorio de alumnos, todas del componente `FiltrosBarra` (carrera, grupo, estado). Ahora tienen `aria-label`, y la barra declara `role="search"`.
- **Región principal:** `landmark-one-main` y `region` en Mis reportes, la bandeja del tutor, el directorio de alumnos y las pantallas de sesión, registro y cambio de contraseña: sus contenedores raíz pasan a `<main>` (sin cambiar estilos).
- **Encabezado de primer nivel:** `page-has-heading-one` en el directorio, el grupo de alumnos y el expediente: `<h1 class="sr-only">` por vista; la revisión del tutor también lo tiene. `heading-order` en la bandeja del tutor: «Firma del tutor académico» pasa de `h3` a `h2` conservando su tamaño.
- **Región repetida:** `landmark-unique` en la plantilla (la sección y la tabla se llamaban igual): la tabla pasa a «Tabla de versiones publicadas».
- **Hallazgos nuevos de la cobertura (corregidos en `BuzonDetalleModal.svelte`):** (a) el fondo del diálogo era un `<button>` que contenía el diálogo (`nested-interactive`): ahora es un `div role="presentation"` que cierra al hacer clic fuera (comprobado), y (b) los botones «Marcar como leído», «Cerrar hilo» y «Reabrir hilo» tomaban el fondo gris del navegador y en el tema oscuro quedaban naranja sobre gris (≈2:1): ahora no tienen fondo.
- **Cosmético heredado de C11:** el resaltado de la celda de acción al pasar el cursor solo ocurre donde la fila se resalta (directorio de alumnos).
- **Herramienta:** `tools/auditoria-ui.js` desactiva transiciones al medir (en un navegador en segundo plano se detenían a medias y daban contrastes falsos).

## Revisión y corrección (2026-10-17)

La revisión técnica y visual (mismo agente, no independiente) concluyó CHANGES_REQUESTED con dos defectos materiales. **M1:** la prueba estática de páginas se saltaba las que no usan `<Navbar>` (sesión, registro y cambio de contraseña): quitar el `<main>` de `Login` no la hacía fallar. **M2:** la fila de AC1 afirmaba 0 violaciones del tutor a 1280 px cuando esa medición se hizo antes de corregir `heading-order`. **Corrección:** `estructura.test.js` revisa todas las páginas de `pages/` sin excepciones y comprueba que las páginas de autenticación y principales están en la lista; con una copia modificada (un `<select>` sin `aria-label` y `Login` sin `<main>`) fallan las dos pruebas. El tutor se repitió a 1280 px en claro y oscuro (7 pantallas, revisión, buzón con un hilo abierto y expediente, ambos temas): axe sin violaciones, 0 desbordes y 0 controles sin foco. Frontend 48 pruebas OK y contrato OK. Revisión focal (mismo agente): cambio acotado a una prueba y a la evidencia, sin hallazgos nuevos.

## Hallazgos nuevos (no corregidos)

- **H5:** el diálogo del buzón no mueve el foco al abrirse ni cierra con Escape si el foco quedó en la tarjeta que lo abrió (el clic fuera sí lo cierra). Es un problema de manejo del foco de los diálogos, fuera del alcance de esta spec; conviene confirmarlo con la prueba de lector de pantalla.
- Advertencias de Svelte que ya existían (superposición con `on:click` sin teclado en el directorio de alumnos).
- Los 5 controles «sin foco» que la auditoría marca en los diálogos son de la página que queda detrás del diálogo; no es un defecto.

## Lo que NO se probó

- **Lector de pantalla real (AC4):** el responsable decidió no hacerla; NO_VERIFICADA.
- Móvil físico, otros navegadores y zoom real al 400 %.
- Tutor a 320 px en el tema oscuro; coordinador a 320 px salvo el buzón.
- El diálogo de depuración se abrió sin confirmar (para prepararlo se generó el paquete ZIP de una carrera y período de prueba, que queda registrado en la base de desarrollo).
## Acta de cierre

La cuarta revisión técnica (mismo agente) concluyó APPROVED el 2026-10-17 sin defectos materiales. El responsable otorgó la aprobación de cierre con `CLOSE C12 + NEXT SPEC` sabiendo que no se probaron el lector de pantalla real (decisión del responsable; AC4 NO_VERIFICADA), el móvil físico, otros navegadores ni el zoom real al 400 %, y que H5 (manejo del foco de los diálogos) sigue abierto. C12 queda DONE. No se hizo commit ni push.

