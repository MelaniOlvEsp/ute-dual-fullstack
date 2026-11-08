# Evidencia C17 — Kit visual y botones coherentes

Fecha: 2026-11-08. Entorno: Docker Compose local (API con almacenamiento `local` solo durante la revisión visual, porque el permiso de Drive estaba caducado; restablecido al valor por omisión al terminar), web servida por la imagen nginx de C16 reconstruida con estos cambios, navegador integrado de la aplicación de escritorio. Datos sintéticos de `scripts/auditoria/carga.py` (12 alumnos con entregas); las sesiones se iniciaron con tokens sintéticos firmados con la clave local, sin contraseñas, y se borraron al terminar (`sessionStorage` y la carpeta de estado). Clases: REAL (navegador y pruebas reales), SIMULADA, NO_VERIFICADA.

## Cambio

- `global.css`: kit de botones con los valores de la base original (`becas-ute-app`): `.btn-primary` y `.btn-outline` (ya existían; se añadió estado deshabilitado del contorno y `:hover:not(:disabled)`), `.btn-danger`, `.btn-danger-outline`, `.btn-link`, `.btn-back`, `.btn-sm` (compacto, sin salto de línea), `.btn-auto` (ancho por contenido) y foco visible uniforme (2 px, desplazamiento de 2 px). Única diferencia intencional con el original: el naranja de acción `#C2410C` de C11 (D1) en lugar de `#F97316` (contraste 5.2:1 con blanco).
- Se retiraron los estilos locales duplicados: `.btn-link` (4 archivos), `.btn-danger` (3 variantes), `.btn-primary` redefinido (`PlantillasDual`, `DepuracionDialogo`, `NotFound`), `.btn-revisar` y `.btn-ver` (ahora `btn-outline btn-sm btn-auto`), `.btn-back` (2), `.btn-eliminar` (ahora `btn-danger-outline`), `.btn-add-fila` y `.link-quitar` (ahora `btn-link` con solo su colocación). Se ajustaron al ancho del contenido los botones de acción de filas y barras: `Dar de baja` (antes en dos líneas), `Guardar firma`, `Publicar pareja`, las acciones de `PeriodosDual` y `DepuracionDialogo`, `Volver al inicio`.
- Sin cambios de textos, rutas, lógica, API ni permisos.

## Fuera de la spec, necesarios para poder revisar la interfaz (C16)

La imagen web de C16 (nginx, Svelte 5) no arrancaba ni mostraba el inicio de sesión; se corrigieron dos defectos mínimos de ese trabajo para poder verificar, y quedan anotados para la revisión de C16, que no tiene `evidencia.md`:
1. `docker/web-config.sh`: la expresión regular de validación de `VITE_API_URL` tenía mal escapados los corchetes (`[A-Za-z0-9._:\[\]-]`, en POSIX el `]` cierra la clase) y rechazaba `http://127.0.0.1:8001`, por lo que el contenedor salía con «VITE_API_URL no válida». Ahora `[][A-Za-z0-9._:-]`.
2. `src/App.svelte`: las rutas con `component={...}` (`/`, `/login`, `/register`, `/cambiar-password` y el 404) lanzaban `TypeError: Cannot read properties of undefined (reading 'before')` con Svelte 5 y dejaban la página en blanco; se pasaron a la forma con contenido (`<Route path="/login"><Login /></Route>`), la misma que ya usan las demás rutas.

## C17-AC1 — Kit con los valores de la base original: REAL

Comparación de `global.css` de Dual contra `becas-ute-app/src/global.css`: los tokens (grises Slate, radios, DM Sans, sombras, naranja de marca, errores y éxito) y `.btn-primary`/`.btn-outline` coinciden salvo el naranja de acción (D1). Contraste: `tests/contraste.test.js` (C11) ya cubre blanco sobre `--orange-action`, `--error` y `--success` y `--error-text` sobre la tarjeta en los dos temas; el hover del peligro (`#B91C1C`) es más oscuro que `--error` y solo mejora el contraste con blanco.

## C17-AC2 — Sin botones locales duplicados: SIMULADA (prueba automatizada)

`tests/botones.test.js` (3 pruebas): el kit existe con 14 px, peso 600, radio del token y relleno `12px 24px`, `.btn-sm` y `.btn-auto` definidos y foco en todas las variantes; ningún `.svelte` redefine una clase del kit (se permite refinar un contexto, p. ej. `.lista-versiones .btn-link.activo`) ni conserva `.btn-revisar`, `.btn-ver` o `.btn-eliminar`. Comprobado con ejemplos que la expresión detecta `.btn-primary {`, `.btn-primary:disabled, .btn-danger {` y `.btn-outline:hover {` y no `.lista .btn-link.activo`. Frontend: 62 pruebas OK (48 + las nuevas de C15/C16 + 3 de C17) y contrato 1/1.

## C17-AC3 — Recorrido visual: REAL (parcial en el detalle por rol)

Con datos sintéticos, en el navegador integrado:
- Coordinador: Períodos (claro y oscuro, con el resumen de 48 semanas y el botón rojo «Cerrar recepción»), Tutores (directorio con «Dar de baja» compacto), Carrera (directorio con «Ver Expediente» y «Actualizar»), Foro y Plantilla del reporte.
- Tutor: Bandeja de reportes (botones «Revisar», «Actualizar», «Guardar firma») y pantalla de revisión (volver, enlaces «Abrir en pestaña nueva», «Descargar»).
- Alumno: Reportes Dual (plantillas, «Entregar reporte») y menú móvil.
- Móvil 375 px (Carrera, Tutores, Cambiar contraseña y 404) y escritorio 1280 px, tema claro y oscuro en Períodos y Tutores: sin desbordes ni botones fuera de estilo.
- Auditoría con axe-core (`tools/auditoria-ui.js`) en Períodos, Tutores, Carrera y Foro, 375 y 1280 px, claro y oscuro (16 combinaciones): **0 violaciones de axe y 0 px de desborde** en todas.

No se recorrió cada diálogo de confirmación ni todas las pestañas de Carrera (promociones, carga masiva); sus botones usan las mismas clases verificadas arriba.

## C17-AC4 — Foco y deshabilitado: REAL (con una limitación de la herramienta)

Con el teclado en «Abrir período»: coincide `:focus-visible` y el contorno pasa a naranja de acción de 2 px con desplazamiento de 2 px (la medición inmediata mostró 1.6 px porque el kit hereda `transition: all 0.2s` del original y el navegador en segundo plano la detiene a medias; a los 600 ms ya es la regla). La función `sinFoco` de `auditoria-ui.js` marcó todos los controles de las 16 combinaciones, incluidos los que no se tocaron, porque su propia nota exige pulsar Tab antes y el recorrido por iframes no lo hace; esa cifra no se usa como evidencia. Estados deshabilitados: «Crear cuenta de tutor», «Guardar firma» y «Publicar aviso» se ven en gris con texto atenuado y cursor `not-allowed`.

## C17-AC5 — Pendientes de UI01: REAL (parcial)

- Identidad de cuenta y menú por rol: alumno (nombre, rol, «Ver mi perfil», Anuncios y buzón, Mis reportes, Mi expediente) y tutor (nombre, rol y sus siete secciones) verificados; coordinador ya verificado en UI01.
- Cambio de contraseña voluntario (`/cambiar-password` con sesión normal): texto neutral, «Contraseña actual», «Cancelar y volver», en móvil.
- Menú móvil: se abre y muestra el menú del rol.
- **NO_VERIFICADA en navegador:** el cambio **obligatorio** (`must_change_password`): requiere una cuenta con ese estado y no se creó una por la interfaz; su comportamiento queda cubierto solo por `auth.test.js` (guardas) y por la revisión de código de UI01.

## C17-AC6 — Compilación y pruebas: REAL

Imagen web reconstruida varias veces (incluye `npm run build` de Vite sin errores; los avisos de accesibilidad de Svelte son los preexistentes de `CoordinadorCarrera` y `BuzonDetalleModal`), frontend 62/62 y contrato 1/1 con `node:22-alpine`. El backend no cambió.

## Limitaciones

- La comparación con la base original es de código y de pantallas en el navegador, no pixel a pixel; el naranja de acción es más oscuro que el original por C11 (decisión del responsable).
- Sin móvil físico. Cambio obligatorio de contraseña sin comprobar en navegador.
- C16 sigue IN_PROGRESS: los dos arreglos de arriba no sustituyen su revisión ni su evidencia; el responsable debe confirmarlos al cerrar C16.
- `VisorPDF` (botón «Reintentar» sobre el panel oscuro) y los controles de otro tipo (tarjetas clicables, pestañas, botones de icono, zona de carga, decisiones Aprobar/Rechazar) conservan su estilo propio por diseño (D2).
