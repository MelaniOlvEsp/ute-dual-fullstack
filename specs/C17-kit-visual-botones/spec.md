# C17 — Kit visual y botones coherentes

Estado: DONE (2026-11-08)
Fecha: 2026-11-08
Responsable de aprobación: responsable del proyecto
Dependencias: C14 DONE; C16 en curso (solo toca la imagen web, dependencias y foco del buzón: este incremento solo cambia estilos y clases de botones, sin tocar esos puntos). Cierra además los recorridos pendientes de [UI01](../UI01-navegacion-y-cuenta/spec.md) (alumno, tutor, móvil y cambio obligatorio), porque el recorrido visual de los tres roles es el mismo.

## Problema y resultado esperado

El responsable quiere que todo el ambiente visual sea coherente con su base original (`becas-ute-app`) y siente que hay botones que se ven feos. La comparación de `global.css` muestra que Dual ya comparte los tokens (naranja, grises Slate, radios, DM Sans, sombras) y los dos botones base `.btn-primary` y `.btn-outline`; la diferencia no está en los tokens sino en que **cada pantalla redefine sus propios botones**: 107 botones en 23 archivos, 49 reglas locales de botón en 17 archivos. Ejemplos: `.btn-link` copiado en 4 archivos, `.btn-danger` en 3 versiones distintas (relleno rojo, contorno con `!important`, solo texto), `.btn-primary` redefinido en 3 pantallas con peso 700 y sin sombra (el original es 600 con sombra), `.btn-revisar` y `.btn-ver` idénticos con otro nombre, `.btn-back` duplicado, y botones sin estado de foco ni deshabilitado coherentes.

Resultado esperado: un solo juego de botones definido en `global.css` con los valores de la base original (primario, secundario/contorno, peligro, peligro en contorno, enlace, volver y compacto), con foco visible y estado deshabilitado uniformes, usado por todas las pantallas; los estilos locales duplicados desaparecen. Ninguna función, texto, permiso ni ruta cambia.

## Fuentes y alcance

US/RN/AC: sin AC nuevos del producto; mejora de coherencia visual (continuación de UI01, C11 y C12).
Documentos enlazados: [UX_Y_FLUJOS](../../docs/analysis/UX_Y_FLUJOS.md), [UI01](../UI01-navegacion-y-cuenta/spec.md), [C11](../C11-accesibilidad-y-vista-movil/spec.md) (decisión del naranja de acción), [C12](../C12-accesibilidad-estructural/spec.md). Referencia visual de solo lectura: `becas-ute-app/src/global.css`.

Incluye:

1. **Kit de botones en `global.css`**, con los valores de la base original: `.btn-primary` (naranja de acción, 14 px, peso 600, radio 10 px, sombra), `.btn-outline`, `.btn-danger` (relleno rojo), `.btn-danger-outline`, `.btn-link` (texto subrayado), `.btn-back` (volver, texto secundario), y los modificadores `.btn-sm` (compacto: 6 px 14 px, 13 px, radio 8 px; sustituye a `.btn-revisar` y `.btn-ver`) y `.btn-auto` (ancho por contenido; `.btn-primary` conserva el ancho completo del original para formularios). Foco visible de 2 px con `outline-offset`, estado deshabilitado uniforme y transición única.
2. **Sustituir los estilos locales duplicados** de esos botones en las pantallas y componentes (lista en «Archivos previstos»), con la misma apariencia que la base original.
3. **Revisión visual de todas las pantallas de los tres roles** (alumno, tutor y coordinador) en escritorio y móvil, en tema claro y oscuro, y cerrar con ella los recorridos pendientes de UI01 (alumno, tutor, móvil y cambio obligatorio de contraseña).

Excluye: backend, API, datos, permisos, textos, rutas y lógica; rediseño de la estructura o de las pantallas; tarjetas clicables (`plantilla-btn`, `mensaje-card`), pestañas (`tab-btn`, `tab-doc`), botones de icono (`icon-btn`, `eye-btn`, `modal-close`, `account`, `logout-btn` del menú) y la zona de carga de archivo (`btn-file`), que conservan su estilo propio y solo se revisan para que usen los mismos tokens y el mismo foco; los pendientes de C16; SvelteKit o cualquier biblioteca de componentes.

## Decisiones

Confirmadas por el responsable en esta conversación: «escoge la mejor opción y lo que ya quede listo» y «redáctala, empiézala y ciérrala». Las dos decisiones siguientes las tomó el agente con esa autorización y quedan registradas:

- **D1 — Color del botón primario.** El original usa `#F97316` con texto blanco (2.8:1, no cumple WCAG). C11 (D1, aprobada por el responsable) ya fijó que todo lo que lleva texto usa el naranja de acción `#C2410C` (5.2:1) y que `#F97316` queda como acento decorativo (sombras y rellenos suaves). Se conserva esa decisión: es la única diferencia intencional con el original y no se revierte para no perder el contraste.
- **D2 — Alcance de la unificación.** Se unifican los botones de acción (primario, secundario, peligro, enlace, volver, compacto). Las tarjetas clicables, pestañas, botones de icono y la zona de carga se dejan fuera (ver «Excluye»): son controles de otro tipo y unificarlos exigiría rediseñar su estructura.

Propuestas técnicas incluidas: variables CSS nuevas solo si hacen falta (`--btn-sombra`, `--btn-sombra-hover`), clases globales en vez de un componente Svelte para no tocar la lógica ni la sintaxis legacy de componentes, y una prueba automatizada que impide volver a definir botones locales con los nombres del kit.

Pendientes bloqueantes (DP): ninguno.

## Contratos y cambios

Métodos/rutas/DTO y compatibilidad: sin cambios de API ni de contrato (73 rutas).
Datos, restricciones y conservación: ninguno.
Permisos y estados: sin cambios.
Archivos/módulos previstos: `ute-dual-frontend/src/global.css`; botones en `ReportesDual`, `CoordinadorDual`, `CoordinadorCarrera`, `PeriodosDual`, `PlantillasDual`, `GestionTutores`, `RecuperarAlumno`, `MiExpediente`, `NotFound`, `Foro`, `Login`, `Register`, `CambiarPassword`, `ExpedienteAlumno`, `ArchivoDepuracion`, `DepuracionDialogo`, `FirmaTutor`, `FiltrosBarra`, `BuzonDetalleModal`, `PerfilModal`, `VisorPDF`; prueba nueva en `ute-dual-frontend/tests/`.
Comportamiento ante fallos/reintentos: no aplica (solo presentación). Si una pantalla se ve peor que antes, se restaura el estilo local de ese botón y se anota.

## Verificación

| AC | Prueba o recorrido | Nivel y datos | Resultado |
|---|---|---|---|
| C17-AC1 | `global.css` define el kit completo con los valores de la base original y la única diferencia es el naranja de acción (D1); contraste de cada variante ≥ 4.5:1 en claro y oscuro | Comparación de código y cálculo de contraste | REAL: tokens y botones comparados con `becas-ute-app`; única diferencia el naranja de acción (D1); contraste cubierto por `contraste.test.js` |
| C17-AC2 | Ningún componente redefine `.btn-primary`, `.btn-outline`, `.btn-danger`, `.btn-danger-outline`, `.btn-link`, `.btn-back` ni `.btn-sm`; desaparecen `.btn-revisar` y `.btn-ver` | Prueba automatizada sobre los `.svelte` | SIMULADA: `botones.test.js` (3 pruebas) |
| C17-AC3 | Recorrido visual de las pantallas de coordinador, tutor y alumno con los botones unificados, escritorio y móvil, tema claro y oscuro, sin desbordes ni botones fuera de estilo | Navegador real, datos sintéticos | REAL: coordinador, tutor y alumno, escritorio y móvil, claro y oscuro; axe 0 violaciones y 0 desborde en 16 combinaciones |
| C17-AC4 | Foco por teclado visible en todas las variantes y estado deshabilitado reconocible | Navegador real y axe-core | REAL: foco por teclado 2 px con desplazamiento; deshabilitados en gris; la métrica `sinFoco` de la herramienta no se usa (falta Tab previo) |
| C17-AC5 | UI01 pendiente: identidad de cuenta de alumno y tutor, cambio de contraseña voluntario y obligatorio, menú móvil | Navegador real, cuentas sintéticas | REAL parcial: menú y cuenta de alumno y tutor, cambio voluntario y menú móvil; NO_VERIFICADA en navegador el cambio obligatorio |
| C17-AC6 | Frontend compila, pruebas existentes (48), contrato y build en verde | Pruebas y `vite build` | REAL: 62/62, contrato 1/1 y compilación de la imagen web |

## Evidencia de implementación

Ver [evidencia.md](evidencia.md) (2026-11-08). Resumen: kit de botones en `global.css` con los valores de la base original, estilos locales duplicados retirados, prueba automatizada que impide reintroducirlos y recorrido visual real de los tres roles. Se corrigieron además dos defectos de C16 que impedían abrir la interfaz (expresión regular de `web-config.sh` y rutas `component=` con Svelte 5), anotados para su revisión.

## Revisión

Veredicto: APPROVED (revisión técnica y visual del mismo agente; la visual en el navegador integrado de la aplicación).
Revisor y modalidad (mismo agente / independiente): mismo agente, sin revisión independiente.
Hallazgos materiales: durante el recorrido visual aparecieron (1) «Dar de baja» y «Ver Expediente» partidos en dos líneas, (2) «Guardar firma» y otros botones de acción a ancho completo fuera de formularios, (3) la imagen web de C16 no arrancaba (expresión regular de `web-config.sh`) y (4) las rutas con `component=` fallaban con Svelte 5 y dejaban en blanco inicio de sesión, registro, cambio de contraseña y 404.
Correcciones y verificación focal: (1) y (2) con `white-space: nowrap` en `.btn-sm` y `btn-auto`/`btn-sm` en esos botones, comprobados de nuevo en pantalla; (3) y (4) con los dos arreglos mínimos descritos en la evidencia, comprobados en el navegador y con la imagen reconstruida; frontend 62/62 y contrato 1/1 tras el último cambio.
Limitaciones: el cambio obligatorio de contraseña no se comprobó en el navegador; los arreglos de C16 deben confirmarse al cerrar C16; sin móvil físico. Previstas: la comparación con la base original es de código y visual en el navegador, no una captura pixel a pixel; sin móvil físico; el naranja de acción es más oscuro que el original por C11.

## Aprobaciones y cierre

Aprobación de implementación: el responsable pidió redactar, empezar y cerrar la spec el 2026-11-08; DRAFT → READY → IN_PROGRESS el mismo día; sin decisiones bloqueantes. Sin commit ni push.
Aprobación de cierre: el responsable ordenó cerrarla («redáctala, empiézala y ciérrala», 2026-11-08).
Resumen final: un solo juego de botones (primario, contorno, peligro, peligro en contorno, enlace, volver, compacto y ancho automático) en `global.css` con los valores de la base original `becas-ute-app` (salvo el naranja de acción de C11), estilos locales duplicados retirados de 17 archivos, prueba automatizada que evita reintroducirlos, recorrido visual de los tres roles en escritorio y móvil, claro y oscuro, sin violaciones de axe. Cierra además los recorridos pendientes de UI01. Evidencia en [evidencia.md](evidencia.md).
Siguiente spec: ninguna; queda confirmar los dos arreglos que hizo C17 en C16 al cerrar C16.
Commit/push: no autorizados salvo indicación explícita.
