# C11 — Accesibilidad y vista móvil

Estado: DONE
Fecha: 2026-10-17
Responsable de aprobación: responsable del proyecto
Dependencias: C10 DONE (2026-10-17). D1 y D2 resueltas el 2026-10-17 (tal como se recomendó); sin decisiones bloqueantes: solo falta la orden `IMPLEMENT C11` para pasar a READY. Es una spec de corrección: no agrega funciones, rutas ni datos.

## Problema y resultado esperado

La revisión visual de C10 (auditoría automática a 375 y 768 px, en claro y oscuro, de las pantallas de los tres roles) encontró tres hallazgos de interfaz que no se corrigieron porque C10 no agrega funciones ni corrige interfaz. Ninguno impide usar el sistema en escritorio, pero sí lo degradan en móvil y para personas con baja visión:

- **H1:** la pantalla «Cuentas de tutores» (coordinador) desborda 173 px a 375 px: el formulario y la columna «Acciones» salen de la pantalla ([GestionTutores.svelte](../../ute-dual-frontend/src/presentation/pages/dual/GestionTutores.svelte)).
- **H2:** contraste por debajo de 4.5:1 en textos secundarios y de acción: la pestaña activa «Anuncios» y los botones naranja con texto blanco (2.8:1), las etiquetas y encabezados en mayúscula del tema claro (≈2.5:1, el color `--text-disabled`) y varios textos del tema oscuro (≈3.5–4.0:1). La cifra sale de una aproximación automática y debe confirmarse con una herramienta de accesibilidad.
- **H3:** las tablas de versiones y de aprobados necesitan desplazamiento horizontal en pantallas angostas, con la acción «Ver» fuera de vista, y la barra de desplazamiento es clara en el tema oscuro.

Resultado esperado: ninguna pantalla desborda en horizontal a 320 px (salvo dentro del contenedor de una tabla de datos, que se desplaza solo él, con teclado y nombre accesible), los textos cumplen el contraste mínimo en ambos temas, la acción principal de cada fila es alcanzable sin desplazarse y la revisión visual a 1280 px que C10 dejó pendiente queda hecha.

## Fuentes y alcance

US/RN/AC: no hay AC nuevos del producto; mejora la usabilidad de AC-20 (visor) y de las pantallas de US-05/10/11/13. Pendientes heredados: hallazgos H1 a H3 y el escritorio a 1280 px de [evidencia C10](../C10-validacion-integral-local/evidencia.md).
Documentos enlazados: [plan maestro](../../docs/construction/PLAN_MAESTRO.md), [guía de uso y operación](../../docs/construction/GUIA_DE_USO_Y_OPERACION.md), [C10](../C10-validacion-integral-local/spec.md), [protocolo SDD-lite](../../docs/construction/PROTOCOLO_SDD_LITE.md).

Incluye:

1. H1: la pantalla «Cuentas de tutores» sin desborde de la página a 320 px (formulario y directorio en una columna; acciones accesibles).
2. H2: contraste mínimo en ambos temas para el texto normal (4.5:1), el texto grande (3:1) y los componentes de interfaz (3:1): tokens de color, pestañas, botones, etiquetas y encabezados de tablas, enlaces de acción.
3. H3: las tablas de datos dentro de un contenedor con desplazamiento propio, enfocable con el teclado y con nombre accesible; la acción de la fila no queda oculta; barra de desplazamiento coherente con el tema.
4. Verificación reproducible: el guion de auditoría que se usó en C10 (desborde, indicador de foco, etiquetas y contraste) se guarda en el repositorio y se ejecuta antes y después; se añade la revisión visual a 1280 px y una herramienta de accesibilidad para confirmar el contraste.

Excluye: funciones nuevas, rediseño de la marca, cambios de API, de base de datos o de archivos, el móvil físico (sigue NO_VERIFICADO), un lector de pantalla real (queda como NO_VERIFICADA salvo que se decida otra cosa), las tres observaciones menores del respaldo de C10 (operación, no interfaz) y WCAG AAA.

## Decisiones

Confirmadas: se corrige con tokens y estilos existentes sin reescribir componentes; el contraste se mide en los dos temas; ninguna corrección cambia datos ni permisos.

Resueltas por el responsable el 2026-10-17, tal como se recomendó (D1: opción a; D2: opción a). Se conserva el texto de las opciones:

- **D1 — Cómo cumplir el contraste con el naranja de la marca.** `--orange: #F97316` con texto blanco da 2.8:1. Opciones: (a) mantener `#F97316` como color decorativo y usar un naranja más oscuro (por ejemplo `#C2410C`, 5.2:1 con blanco) para fondos con texto y para texto naranja sobre fondo claro, ajustando `--text-disabled` a un gris de 4.5:1; (b) conservar el naranja y poner texto oscuro sobre él (≈6:1), lo que cambia el aspecto de botones y pestañas. Recomendación: (a), porque conserva la identidad en acentos e iconos y solo oscurece lo que lleva texto. Necesito tu decisión porque toca la marca.
- **D2 — Qué hacer con las tablas en pantallas angostas.** Opciones: (a) mantener la tabla en un contenedor con desplazamiento horizontal propio (enfocable y con nombre) y dejar visible la acción «Ver» de cada fila (primera columna o columna fija); (b) en móvil mostrar cada fila como una tarjeta apilada. Recomendación: (a), el cambio mínimo y el patrón que la guía de reflujo admite para tablas de datos; (b) cambia más la interfaz.

Propuestas técnicas incluidas en esta aprobación (sujetas a D1 y D2): variables de color separadas para fondo de acción y texto de acción; `overflow-x: auto` solo en el contenedor de cada tabla, con `tabindex="0"`, `role="region"` y `aria-label`; `min-width: 0` en los hijos de las cuadrículas que desbordan; la barra de desplazamiento con `color-scheme` o estilos del tema; un solo cambio de estilos compartidos en `global.css` en vez de parches por pantalla.

### Referencias de buenas prácticas consultadas

Consultadas el 2026-10-17 (criterio de diseño, no norma de la universidad):

- [WCAG 2.2: Reflow (1.4.10)](https://www.w3.org/WAI/WCAG22/Understanding/reflow) y [Deque: 1.4.10 Reflow](https://dequeuniversity.com/resources/wcag2.1/1.4.10-reflow): el contenido vertical debe funcionar sin desplazamiento en dos direcciones a 320 píxeles CSS (equivale a 400 % de zoom en 1280 px); las tablas de datos son una excepción.
- [Reflow y tablas: la excepción cubre solo la tabla](https://216digital.com/tag/1-4-10-reflow/) y [lista de verificación de desplazamiento horizontal](https://frontendchecklist.io/rules/css/horizontal-scroll): la tabla va en su propio contenedor con `overflow: auto`; el resto de la página no puede desbordar. Estas fuentes son guías de terceros; la búsqueda no cubrió el contenedor enfocable por teclado (`tabindex="0"` con nombre accesible), que se verifica contra 2.1.1 (Teclado) en la propia revisión.
- [Contraste mínimo 4.5:1 (1.4.3), guía de un sistema de diseño público](https://www.designsystem.qld.gov.au/styles/typography/accessibility): 4.5:1 para texto normal y 3:1 para texto grande; el texto de la guía cita WCAG 2.1 y 1.4.3 no cambia en 2.2 según el W3C.

## Contratos y cambios

Métodos/rutas/DTO y compatibilidad: sin cambios; el contrato (73 rutas) y los fixtures no se tocan.
Datos, restricciones y conservación: sin cambios.
Permisos y estados: sin cambios.
Archivos/módulos previstos: `ute-dual-frontend/src/global.css` (tokens y estilos compartidos); `Foro.svelte` (pestañas); `PeriodosDual.svelte`, `PlantillasDual.svelte`, `GestionTutores.svelte`; las tablas de versiones y de aprobados (`ReportesDual.svelte`, `MiExpediente.svelte` y `ExpedienteAlumno.svelte`); el guion de auditoría y la prueba de contraste de los tokens en `ute-dual-frontend/tests`.
Comportamiento ante fallos/reintentos: no aplica (solo presentación).

## Verificación

| AC | Prueba o recorrido | Nivel y datos | Resultado |
|---|---|---|---|
| C11-AC1 | Sin desborde horizontal de la página a 320 y 375 px en todas las pantallas de los tres roles, en claro y oscuro; «Cuentas de tutores» sin recortes | Auditoría automática en el navegador con cuentas sintéticas | REAL: 0 px de desborde a 320 px en tres roles, claro y oscuro |
| C11-AC2 | Contraste ≥ 4.5:1 (texto normal) y ≥ 3:1 (texto grande y componentes) en ambos temas, confirmado con una herramienta de accesibilidad además de la aproximación propia | Auditoría y herramienta de accesibilidad | REAL con axe-core (0 violaciones de contraste) y SIMULADA (tokens) |
| C11-AC3 | Cada tabla de datos se desplaza solo dentro de su contenedor, se alcanza con Tab, tiene nombre accesible y su acción principal es visible sin desplazarse | Navegador, teclado y auditoría | REAL |
| C11-AC4 | Revisión visual a 1280 px de las pantallas principales de cada rol en claro y oscuro (pendiente de C10) | Navegador a tamaño real | REAL parcial (coordinador y tutor a 1280 px; alumno no) |
| C11-AC5 | No hay regresión: pruebas de frontend, contrato y `smoke_c10.py` | Pruebas existentes y recorrido integral | REAL |

## Evidencia de implementación

Implementada el 2026-10-17 y verificada en el navegador integrado con cuentas sintéticas; ver [evidencia C11](evidencia.md) (cambios, auditoría con axe-core antes y después, hallazgo nuevo H4, lo no probado). Revisión: dos revisiones técnicas y visuales del mismo agente (CHANGES_REQUESTED con M1 y APPROVED). Sin push.

## Revisión

Veredicto: APPROVED (segunda revisión, 2026-10-17).
Revisor y modalidad (mismo agente / independiente): el mismo agente que implementó; técnica y visual (no independiente).
Hallazgos materiales: M1 (una etiqueta de la pantalla de revisión del tutor medía 4.49:1 sobre un fondo teñido de naranja y la auditoría no cubría vistas sin dirección propia).
Correcciones y verificación focal: `--text-disabled` a `#5B6B82`, pares con `--orange-light` en la prueba de contraste y rutas con `preparar` en la herramienta de auditoría; axe-core sin violaciones de contraste en revisión, buzón, perfil, login, registro y 404; ver la evidencia.
Limitaciones previstas: lector de pantalla real, móvil físico y otros navegadores NO_VERIFICADOS; el contraste se confirma con una herramienta pero no sustituye una auditoría de accesibilidad completa.

## Aprobaciones y cierre

Aprobación de implementación: D1 y D2 resueltas el 2026-10-17; el responsable autorizó la implementación con `IMPLEMENT C11` el 2026-10-17: sin decisiones bloqueantes, la spec pasó de DRAFT a READY y a IN_PROGRESS el mismo día. Sin commit ni push.
Aprobación de cierre: el responsable la otorgó con `CLOSE C11 + NEXT SPEC` el 2026-10-17, tras la segunda revisión APPROVED y sabiendo lo que no se verificó (lector de pantalla real, móvil físico, otros navegadores, zoom real al 400 %, diálogo de depuración, buzón con un hilo abierto, alumno y períodos a 1280 px) y que H4 y las reglas de buenas prácticas de axe siguen sin corregir. C11 queda DONE; el commit local de implementación se hizo con el cierre.
Resumen final: H1 (desborde móvil), H2 (contraste, D1 a) y H3 (tablas, D2 a) corregidos; 0 desbordes a 320 px y 0 violaciones de contraste con axe-core en las pantallas auditadas; 45 pruebas de frontend, contrato y `smoke_c10` en verde. Sin push.
Siguiente spec: [C12 — Accesibilidad estructural](../C12-accesibilidad-estructural/spec.md) (DRAFT), para H4 y las reglas de buenas prácticas de axe; el plan maestro no tenía más incrementos.
Commit/push: commit local con el cierre; push no autorizado.
