# C12 — Accesibilidad estructural

Estado: DRAFT
Fecha: 2026-10-17
Responsable de aprobación: responsable del proyecto
Dependencias: C11 DONE (2026-10-17). D1 y D2 (más abajo) pendientes: bloquean pasar a READY. Es una spec de corrección: no agrega funciones, rutas ni datos. El plan maestro no tenía más incrementos; esta spec cierra los pendientes de accesibilidad que C11 dejó registrados.

## Problema y resultado esperado

C11 corrigió el desborde móvil, el contraste y las tablas, y dejó sin corregir lo que la auditoría con axe-core seguía marcando fuera de su alcance. Lo que queda afecta sobre todo a quien usa un lector de pantalla o navega con el teclado:

- **H4 (`select-name`, impacto serio):** listas desplegables sin nombre accesible: 3 en la bandeja del tutor y 2 en el directorio de alumnos (filtros de carrera, de grupo y de estado). Un lector de pantalla anuncia «cuadro combinado» sin decir para qué sirve.
- **Estructura de la página (`landmark-one-main`, `region`, `page-has-heading-one`, `heading-order`, `landmark-unique`):** varias pantallas no declaran una región principal (`<main>`), tienen contenido fuera de regiones, no empiezan con un `h1` o saltan niveles de encabezado, y una pantalla repite una región con el mismo nombre. Son reglas de buenas prácticas de axe (no criterios WCAG), pero permiten saltar la navegación y orientarse con un lector de pantalla.
- **Cobertura:** quedaron sin auditar el diálogo de depuración, el buzón con un hilo abierto y alumno y períodos a 1280 px, y nunca se probó con un lector de pantalla real.
- **Cosmético heredado de C11:** en las tablas sin resaltado de fila, pasar el cursor resalta solo la celda de acción.

Resultado esperado: cero violaciones de axe (reglas WCAG y de buenas prácticas) en todas las pantallas y estados de los tres roles, en claro y oscuro, y una comprobación con lector de pantalla de los recorridos principales (o su registro explícito como NO_VERIFICADA, según D1).

## Fuentes y alcance

US/RN/AC: sin AC nuevos del producto; mejora la usabilidad de todas las pantallas. Pendientes heredados: H4 y reglas de axe de la [evidencia de C11](../C11-accesibilidad-y-vista-movil/evidencia.md).
Documentos enlazados: [plan maestro](../../docs/construction/PLAN_MAESTRO.md), [guía de uso y operación](../../docs/construction/GUIA_DE_USO_Y_OPERACION.md), [C11](../C11-accesibilidad-y-vista-movil/spec.md), [protocolo SDD-lite](../../docs/construction/PROTOCOLO_SDD_LITE.md).

Incluye:

1. H4: nombre accesible para cada lista desplegable (etiqueta visible asociada o `aria-label`), sin cambiar su comportamiento.
2. Estructura: una región `<main>` por página, un `h1` al comienzo del contenido principal, encabezados sin saltos de nivel, el contenido dentro de regiones y regiones repetidas con nombres distintos. Sin cambiar el aspecto (los estilos de los encabezados no dependen del nivel).
3. Cobertura de la auditoría: el diálogo de depuración, el buzón con un hilo abierto, el visor del PDF, alumno y períodos a 1280 px, agregados a la herramienta con rutas `preparar` (C11); el guion pasa a ser el criterio de salida.
4. El resaltado de la celda de acción solo cuando el resto de la fila también se resalta.
5. Comprobación con lector de pantalla (según D1) de: inicio de sesión, foro, entrega de un reporte, revisión y firma, expediente.

Excluye: funciones nuevas, rediseño, cambios de API, datos o archivos, móvil físico, WCAG AAA y las tres observaciones menores del respaldo de C10 (son de operación, no de interfaz; se registran aparte).

## Decisiones

Confirmadas: se corrige con cambios de marcado y estilos mínimos sin reescribir componentes; el resultado se mide con axe-core (versión fijada) y el guion de `tools/auditoria-ui.js`; ninguna corrección cambia datos ni permisos.

Pendientes bloqueantes (con recomendación):

- **D1 — Lector de pantalla.** Las revisiones automáticas no sustituyen a una persona con un lector de pantalla. Opciones: (a) el responsable (o quien designe) recorre los cinco recorridos con Narrador de Windows o NVDA y anota lo que no se entiende; yo preparo la guía de la prueba y registro el resultado; (b) se declara NO_VERIFICADA y la spec se cierra solo con las comprobaciones automáticas. Recomendación: (a), con un recorrido corto y una guía de pasos; si no es posible ahora, (b) sin bloquear el resto.
- **D2 — Alcance respecto del respaldo.** Opciones: (a) esta spec solo trata la interfaz y las tres observaciones del respaldo (guardas al ejecutar subcomandos a mano, documentar `probar-fallos` y poda concurrente) quedan para una spec de operación aparte cuando se vaya a usar con datos reales; (b) incluirlas aquí. Recomendación: (a), para no mezclar interfaz y operación.

Propuestas técnicas incluidas en esta aprobación (sujetas a D1 y D2): `<main id>` en el contenedor de cada página (y `<nav>`/`<header>` donde ya hay navegación), `h1` visible por pantalla (o `sr-only` si el diseño ya lo muestra de otra forma), `aria-label` o `<label>` asociado en cada `<select>`, y una prueba que falle si un `<select>` o una página nueva no tienen nombre o `main` (revisión estática de los `.svelte`).

### Referencias de buenas prácticas consultadas

Consultadas el 2026-10-17 (criterio de diseño, no norma de la universidad):

- [Deque: Page must have one main landmark (`landmark-one-main`)](https://dequeuniversity.com/rules/axe/4.4/landmark-one-main) y [Deque: Page must contain a level-one heading (`page-has-heading-one`)](https://dequeuniversity.com/rules/axe/4.4/page-has-heading-one): regla de buenas prácticas de Deque (no un criterio WCAG): una sola región principal para saltar lo repetido y un `h1` al comienzo del contenido principal.
- [Lista de reglas de axe y `heading-order`](https://webhint.io/docs/user-guide/hints/hint-axe/semantics/): los niveles de encabezado solo deben aumentar de uno en uno.
- La búsqueda no devolvió una fuente para `select-name` ni para su correspondencia con WCAG 4.1.2 (Nombre, función, valor) y 1.3.1 (Información y relaciones); eso se confirma contra las descripciones oficiales de las reglas de axe-core al implementar.

## Contratos y cambios

Métodos/rutas/DTO y compatibilidad: sin cambios; el contrato (73 rutas) y los fixtures no se tocan.
Datos, restricciones y conservación: sin cambios.
Permisos y estados: sin cambios.
Archivos/módulos previstos: las páginas y componentes de `ute-dual-frontend/src/presentation` que no declaran `main` o `h1` (`ReportesDual`, `CoordinadorCarrera`, `CoordinadorDual`, `PlantillasDual`, login y registro entre otras, según la auditoría), los `<select>` de los filtros de `CoordinadorDual` y `CoordinadorCarrera`, `global.css` (resaltado de la celda de acción) y `tools/auditoria-ui.js` (rutas nuevas).
Comportamiento ante fallos/reintentos: no aplica (solo presentación).

## Verificación

| AC | Prueba o recorrido | Nivel y datos | Resultado |
|---|---|---|---|
| C12-AC1 | Cero violaciones de axe (todas las reglas, incluidas las de buenas prácticas) en todas las pantallas y estados de los tres roles, a 320 y 1280 px, en claro y oscuro | Auditoría en el navegador con cuentas sintéticas | NO_VERIFICADA |
| C12-AC2 | Cada lista desplegable tiene nombre accesible y cada página una región principal y un `h1`; una prueba estática lo comprueba | Prueba de frontend sobre los `.svelte` | NO_VERIFICADA |
| C12-AC3 | Cobertura: diálogo de depuración, buzón con hilo abierto, visor del PDF, alumno y períodos a 1280 px dentro de la auditoría | Navegador | NO_VERIFICADA |
| C12-AC4 | Los cinco recorridos con lector de pantalla se entienden de principio a fin (según D1) | Persona con Narrador o NVDA, o NO_VERIFICADA | NO_VERIFICADA |
| C12-AC5 | Sin regresión: pruebas de frontend, contrato y `smoke_c10.py`; el aspecto no cambia | Pruebas existentes y revisión visual | NO_VERIFICADA |

## Evidencia de implementación

Sin ejecución: spec en DRAFT. Añadir solo después de implementar, con fecha, entorno, revisión del código y clase REAL/SIMULADA/NO_VERIFICADA.

## Revisión

Veredicto: pendiente.
Revisor y modalidad (mismo agente / independiente): pendiente.
Hallazgos materiales: no aplica antes de implementación.
Correcciones y verificación focal: no aplica.
Limitaciones previstas: móvil físico y otros navegadores NO_VERIFICADOS; sin un lector de pantalla real el resultado de AC4 queda NO_VERIFICADA.

## Aprobaciones y cierre

Aprobación de implementación: pendiente (D1 y D2, y la orden de pasar a READY).
Aprobación de cierre: pendiente.
Resumen final: pendiente.
Siguiente spec: no hay más incrementos en el plan maestro; el siguiente paso natural es el uso real (hospedaje, cifrado de respaldos y datos reales), que necesita decisiones del responsable.
Commit/push: no autorizados salvo indicación explícita.
