# Evidencia C11 — Accesibilidad y vista móvil

Fecha: 2026-10-17. Estado de la spec: DONE (cerrada el 2026-10-17; sin push).
Clases: REAL = navegador integrado contra el sistema real con cuentas sintéticas; SIMULADA = comprobación de tokens sin navegador; NO_VERIFICADA = no observado.

## Resumen por criterio

| Criterio | Clase | Fuente |
|---|---|---|
| C11-AC1 sin desborde horizontal a 320 px | REAL: 0 px de desborde en las pantallas auditadas de los tres roles (tutor: 7 pantallas a 320 y 768 px; coordinador: 5 a 320 px; alumno: 3 a 320 px), en claro y oscuro | `ute-dual-frontend/tools/auditoria-ui.js` |
| C11-AC2 contraste | REAL con axe-core 4.10.2: 0 violaciones de `color-contrast` en las pantallas auditadas, en ambos temas (antes: 7 por pantalla en claro y hasta 6 en oscuro en el alumno; 104 textos con contraste bajo en la bandeja del tutor a 375 px en claro según la aproximación de C10); SIMULADA: 5 pruebas de los tokens (`tests/contraste.test.js`) | auditoría y `contraste.test.js` |
| C11-AC3 tablas con desplazamiento propio, teclado y acción visible | REAL: todas las tablas de datos tienen contenedor `role="region"` con `tabindex="0"` y nombre; la acción de la fila queda fija a la derecha (directorio de tutores, expediente, archivo y depuración, directorio de alumnos, bandeja); axe sin `scrollable-region-focusable` | auditoría y capturas |
| C11-AC4 revisión visual a 1280 px | REAL parcial: directorio de alumnos en claro y oscuro (coordinador), foro (coordinador) y bandeja del tutor; alumno a 1280 px y «Períodos» no se revisaron visualmente (solo a 320 px con la auditoría) | navegador integrado |
| C11-AC5 sin regresión | REAL: 45 pruebas de frontend (40 + 5 de contraste), 1 de contrato y `smoke_c10.py` PASS; la compilación de Vite termina con las mismas advertencias previas | pruebas y smoke |

## Qué cambió (solo presentación; sin API, datos ni permisos)

- **H2 (D1, opción a):** `global.css` separa el naranja de acción y de texto del naranja de la marca: `--orange` y `--orange-action` pasan a `#C2410C` (5.2:1 con blanco; en el tema oscuro el texto naranja usa `#FB923C`), los fondos con texto blanco usan `--orange-action`, `--text-disabled` pasa a `#5B6B82` (5.1:1 sobre blanco y sobre fondos teñidos de naranja; `#94A3B8` en oscuro) y los textos de error y éxito usan `--error-text` y `--success-text` (los fondos de acción `#DC2626` y `#15803D` cumplen con blanco). El `#F97316` de la marca solo queda en sombras y rellenos suaves. Los colores del tipo de archivo de la plantilla (Word y PDF) tienen variante para el tema oscuro.
- **H3 (D2, opción a):** clase `.col-accion` (columna fija a la derecha con el borde inferior conservado) en las tablas con acción; contenedores con desplazamiento enfocables y con nombre (`GestionTutores`, `CoordinadorCarrera`, `CoordinadorDual`, `PeriodosDual`, `ReportesDual`; ya lo tenían `ExpedienteAlumno`, `ArchivoDepuracion` y `PlantillasDual`); barra de desplazamiento con `color-scheme: dark` en el tema oscuro; tres listas con desplazamiento (`empresa-list`) enfocables.
- **H1:** `GestionTutores.svelte` usa `minmax(0, 1fr)` y `min-width: 0` (la pista de la cuadrícula se ensanchaba con la tabla), y el campo nativo de archivo no ensancha la página en 320 px (`input[type="file"] { max-width: 100% }`; era un desborde de 12 px en la bandeja del tutor).
- Herramientas: `tools/auditoria-ui.js` (desborde, foco, etiquetas y axe-core por iframe, en varios anchos y temas) y `tests/contraste.test.js`.

## Revisión y corrección (2026-10-17)

La revisión técnica y visual (mismo agente, no independiente) concluyó CHANGES_REQUESTED con un defecto material. **M1:** en la pantalla de revisión del tutor, la etiqueta «Nota de la empresa» medía 4.49:1 (`--text-disabled` `#64748B` sobre el panel `#FFF7F1`), por debajo del 4.5:1 de C11-AC2; la prueba de tokens solo medía contra `bg-card` y `bg-page` y la auditoría no incluía vistas sin dirección propia. **Corrección:** `--text-disabled` pasa a `#5B6B82`; `contraste.test.js` añade los pares con `--orange-light` (la prueba habría detectado el valor anterior); `auditoria-ui.js` admite rutas con una función `preparar` que lleva la página a un estado (abrir una revisión, una pestaña, un diálogo). **Verificación (REAL, axe-core, como tutor, 375 y 1024 px, claro y oscuro):** revisión de un reporte, buzón del foro y modal de perfil sin violaciones de contraste ni desbordes (la revisión conserva las reglas de buenas prácticas ya listadas); los botones «Aprobar y firmar» y «Rechazar» tampoco tienen violaciones. Frontend 45 pruebas OK, contrato OK y la compilación de Vite sin errores. En el modal de perfil el auditor reporta 5 controles «sin foco»: son los controles de la página que quedan detrás del diálogo y no se pueden enfocar; no es un defecto del producto (artefacto de la medición). Se confirmó además que los contrastes marginales de la pestaña inactiva del foro en oscuro eran un artefacto de transiciones detenidas del navegador integrado (con las transiciones desactivadas hay 0 violaciones). Siguen sin auditarse el login, el registro, el diálogo de depuración y el buzón con un hilo abierto. Revisión focal (mismo agente): cambio acotado a un token, una prueba y la herramienta de auditoría, sin hallazgos nuevos.

## Hallazgos nuevos (no corregidos: fuera de H1 a H3)

- **H4:** axe informa `select-name` (listas desplegables sin nombre accesible): 3 en la bandeja del tutor y 2 en el directorio de alumnos.
- Reglas de buenas prácticas de axe sin corregir: `landmark-one-main`, `region`, `page-has-heading-one`, `heading-order` y `landmark-unique` en varias pantallas (por ejemplo Mis reportes no declara una región principal).
- `.btn-ver` (directorio de alumnos) conserva su fondo blanco en el tema oscuro (aspecto previo; el contraste cumple).

## Observaciones de la medición

La aproximación propia de C10 marcaba de más (emojis, transiciones de color al cambiar de tema); por eso C11 usa axe-core y espera 2 s tras cambiar el tema. Para que el indicador de foco se evalúe, hay que pulsar Tab una vez en la página antes de auditar (sin ello el navegador no aplica `:focus-visible` al enfocar por programa).

## Lo que NO se probó

- Lector de pantalla real, móvil físico, otros navegadores y zoom real al 400 % (se emuló el ancho de 320 px).
- Alumno a 1280 px y la pantalla de períodos a 1280 px (solo a 320 px); coordinador y alumno a 768 px (solo el tutor).
- El flujo de «Revisar» y la firma con el nuevo estilo de botones no se repitieron más allá de la carga de la bandeja.
## Acta de cierre

La segunda revisión técnica y visual (mismo agente) concluyó APPROVED el 2026-10-17 sin defectos materiales, después de corregir M1; además se auditaron login, registro y 404 (sin violaciones de contraste ni desbordes). El responsable otorgó la aprobación de cierre con `CLOSE C11 + NEXT SPEC` sabiendo que no se probaron lector de pantalla real, móvil físico, otros navegadores, zoom real al 400 %, el diálogo de depuración, el buzón con un hilo abierto ni alumno y períodos a 1280 px, y que H4 y las reglas de buenas prácticas de axe siguen abiertas. C11 queda DONE. El commit local de implementación se hizo con el cierre; no hay push.

