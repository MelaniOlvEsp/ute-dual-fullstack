# C11 — Accesibilidad y vista móvil

Estado: DRAFT
Fecha: 2026-10-17
Responsable de aprobación: responsable del proyecto
Dependencias: C10 DONE (2026-10-17). D1 y D2 (más abajo) pendientes: bloquean pasar a READY. Es una spec de corrección: no agrega funciones, rutas ni datos.

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

Pendientes bloqueantes (con recomendación):

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
| C11-AC1 | Sin desborde horizontal de la página a 320 y 375 px en todas las pantallas de los tres roles, en claro y oscuro; «Cuentas de tutores» sin recortes | Auditoría automática en el navegador con cuentas sintéticas | NO_VERIFICADA |
| C11-AC2 | Contraste ≥ 4.5:1 (texto normal) y ≥ 3:1 (texto grande y componentes) en ambos temas, confirmado con una herramienta de accesibilidad además de la aproximación propia | Auditoría y herramienta de accesibilidad | NO_VERIFICADA |
| C11-AC3 | Cada tabla de datos se desplaza solo dentro de su contenedor, se alcanza con Tab, tiene nombre accesible y su acción principal es visible sin desplazarse | Navegador, teclado y auditoría | NO_VERIFICADA |
| C11-AC4 | Revisión visual a 1280 px de las pantallas principales de cada rol en claro y oscuro (pendiente de C10) | Navegador a tamaño real | NO_VERIFICADA |
| C11-AC5 | No hay regresión: pruebas de frontend, contrato y `smoke_c10.py` | Pruebas existentes y recorrido integral | NO_VERIFICADA |

## Evidencia de implementación

Sin ejecución: spec en DRAFT. Añadir solo después de implementar, con fecha, entorno, revisión del código y clase REAL/SIMULADA/NO_VERIFICADA.

## Revisión

Veredicto: pendiente.
Revisor y modalidad (mismo agente / independiente): pendiente.
Hallazgos materiales: no aplica antes de implementación.
Correcciones y verificación focal: no aplica.
Limitaciones previstas: lector de pantalla real, móvil físico y otros navegadores NO_VERIFICADOS; el contraste se confirma con una herramienta pero no sustituye una auditoría de accesibilidad completa.

## Aprobaciones y cierre

Aprobación de implementación: pendiente (D1 y D2, y la orden de pasar a READY).
Aprobación de cierre: pendiente.
Resumen final: pendiente.
Siguiente spec: no hay otro incremento en el plan maestro; el responsable decide si hace falta una spec de operación (observaciones menores del respaldo) o el paso al uso real.
Commit/push: no autorizados salvo indicación explícita.
