# UI01 — Navegación y cuenta con continuidad visual

Estado: IN_PROGRESS
Fecha: 2026-10-14
Aprobación de implementación: recibida en este chat; DRAFT → READY → IN_PROGRESS el 2026-10-14. Ajuste aprobado: tarjeta Mi perfil con estilo del perfil académico existente para coordinador y tutor, conservando perfil del alumno.
Dependencias: base local C01; coordinar su ejecución sin declarar C01 cerrado.

## Problema y resultado esperado

El usuario solicita recuperar la comodidad visual del proyecto becas-ute-app tras separar Dual. El navbar actual perdió iconos, indicación de sección activa y estilos tipográficos de los enlaces. No identifica la cuenta del coordinador. Cambiar contraseña aparece entre módulos académicos y presenta siempre instrucciones de contraseña temporal.

Resultado propuesto: conservar la estructura de Dual y recuperar el lenguaje visual anterior, con identidad de cuenta accesible para los tres roles y una presentación coherente del cambio de contraseña.

## Fuentes

- ../../docs/analysis/UX_Y_FLUJOS.md
- ../../docs/analysis/REGLAS_DE_NEGOCIO.md: RN-01, RN-03, RN-04.
- ../../docs/construction/PROTOCOLO_SDD_LITE.md
- Referencia visual de solo lectura: becas-ute-app/src/lib/components/layout/Navbar.svelte, src/global.css e index.html.
- Comparación estática realizada el 2026-10-14; apariencia en navegador pendiente de verificar.

## Alcance propuesto

1. Recuperar iconos SVG de línea, tamaños, espaciado, radios y estados hover/activo del menú anterior, adaptados a las rutas y tres roles actuales de Dual. Sin módulos ni roles de Becas.
2. Mantener DM Sans: ambos proyectos ya la declaran y cargan igual. Recuperar en los enlaces del menú font-family heredada, tamaño 14px y pesos 500/600; verificar carga efectiva en navegador antes de atribuir diferencias a la fuente.
3. Mostrar nombre y rol de la sesión; ofrecer Mi cuenta con nombre, correo y rol para coordinador, tutor y alumno. Usar datos de la sesión existente, sin edición ni nuevos endpoints. Conservar acceso al perfil académico del alumno.
4. Mover Cambiar contraseña a Mi cuenta. Mantener Cerrar sesión claramente accesible y separado de la navegación académica.
5. Diferenciar la pantalla de cambio por must_change_password: obligatorio con explicación de contraseña temporal y sin salida a páginas protegidas; voluntario con texto neutral, campo Contraseña actual y acción Cancelar/Volver a una ruta autorizada. Mantener validaciones, revocación de sesión y retorno al login tras éxito.
6. Sustituir controles de contraseña con emojis por iconos coherentes, etiquetas accesibles y confirmación de resultado integrada en la interfaz. No cambiar la política de contraseñas ni la API.
7. Mantener tema claro/oscuro y navegación móvil; acceso por teclado, foco visible, Escape y devolución de foco al cerrar menús o diálogos. El menú oculto no debe dejar controles enfocables.

## Exclusiones y límites

No modificar backend, SQL, datos, permisos, reglas académicas ni estructura por capas. No copiar el navbar antiguo completo con roles/rutas heredados. No editar becas-ute-app. No guardar credenciales de pruebas en documentos ni código. No implementar antes de aprobar esta spec.

## Archivos previstos

ute-dual-frontend/src/presentation/components/layout/Navbar.svelte; componente de cuenta reutilizable si resulta necesario; presentation/pages/auth/CambiarPassword.svelte. Revisar PerfilModal y sus consumidores para preservar el perfil académico sin duplicación. Ajustes de estilos limitados a estos componentes salvo necesidad verificada.

## Aceptación y validación

| ID | Comprobación | Evidencia requerida |
|---|---|---|
| UI01-AC1 | Iconos, tipografía y estados visibles recuperan el estilo de la referencia | Comparación visual real |
| UI01-AC2 | Sección activa distingue rutas con vista=grupos/empresas | Navegación real |
| UI01-AC3 | Cada rol identifica su cuenta y conserva solo sus opciones autorizadas | Recorrido por los tres roles |
| UI01-AC4 | Cambio voluntario permite volver y no exige falsamente cambiar una temporal | Navegador con cuenta normal |
| UI01-AC5 | Cambio obligatorio mantiene bloqueo previo y tras éxito requiere login | Cuenta sintética temporal; comprobar guardas |
| UI01-AC6 | Menús y cuenta funcionan en móvil/escritorio, ambos temas y teclado | Preview real y revisión de foco |
| UI01-AC7 | Frontend compila y no rompe pruebas existentes | Build y pruebas pertinentes |

Resultados: NO_VERIFICADA; solo comparación de código realizada. Presentar preview al usuario antes del cierre. Añadir pruebas nuevas solo si verifican comportamiento relevante, especialmente distinción obligatorio/voluntario.

## Revisión y cierre

Revisión: pendiente. Aprobación humana de cierre: pendiente.
C01 sigue IN_PROGRESS. UI01 no sustituye C02 ni completa el producto.
Commit/push: no autorizados.

## Evidencia de implementación — 2026-10-14

- Autorización: usuario aprobó tarjeta Mi perfil inspirada en la del alumno; implementado en este chat.
- Navbar: iconos SVG compartidos, tipografía y estados activos por ruta/vista, nombre/rol y acceso a tarjeta; rutas exclusivas de Dual.
- PerfilModal reutilizado para los tres roles. Conserva campos académicos y empresa del alumno, consultados al abrir; muestra carga/error sin ocultar identidad. Coordinador/tutor muestran nombre, correo y rol.
- Diálogos nativos con foco contenido, Escape, cierre por fondo y devolución de foco. Cambio de contraseña dentro de tarjeta; pantalla distingue obligatorio/voluntario, permite cancelar solo el voluntario y muestra confirmación integrada tras invalidar sesión.
- REAL: 20/20 pruebas existentes del frontend pasan, ejecutadas desde ute-dual-frontend.
- REAL: build Vite final correcto (99 módulos) con resolve.preserveSymlinks=true como opción de ejecución local, sin modificar vite.config.js. Build convencional bloqueado por EPERM en realpath de Windows, incluso en copia de trabajo. Persisten avisos de accesibilidad/CSS en componentes ajenos; componentes de layout modificados sin esos avisos en build final.
- NO_VERIFICADA: recorrido visual móvil/escritorio, carga efectiva de fuente, cambio de contraseña y roles mediante navegador. Apertura de preview local falló por ERR_CONNECTION_TIMED_OUT. No se cambiaron contraseñas ni datos.
- NO_VERIFICADA: reconstrucción de contenedor web; canal Docker devuelve permission denied a esta sesión. Requiere ejecutar docker compose up --build -d --wait --no-deps web en PowerShell del usuario.
- Revisión de código: mismo agente, sin revisión independiente. No se observaron cambios de backend/permisos; aprobación final pendiente de recorrido visual.
- Estado: IN_PROGRESS. No se marca DONE ni se cierra C01. Sin commit/push.

### Verificación real posterior en Docker

Se abrió la página actualizada en 5174 con la sesión del coordinador: menú con iconos/activo, tarjeta con correo/rol, cambio voluntario con texto neutral y Cancelar y volver funcionando. No se modificaron credenciales.
Hallazgo: nombre vacío porque decodeSession no incluye nombre. Corregido Navbar para consultar /auth/me al montar y al abrir perfil; reutiliza la respuesta académica del alumno. No cambia permisos ni el JWT. Compilación final y 20/20 pruebas pasan nuevamente.
Pendiente: reconstruir web con esta corrección y verificar nombre visible. Recorridos de tutor/alumno, cambio obligatorio y móvil siguen pendientes; UI01 permanece IN_PROGRESS.

### Corrección de contrato tras revisión

PerfilModal consume alumno.dual_activo; conserva empresa como información independiente del estado de inscripción. Build posterior correcto. Smoke C01 ampliado para comprobar el campo real de API en alumnos con/sin asignación y activo sin empresa; ejecución real pendiente. Mantener IN_PROGRESS hasta la siguiente revisión.

### Evidencia recibida del smoke C01

2026-10-14: PASS del smoke Compose ejecutado por el usuario, corroborado en work/c01/smoke-compose.log. Incluye dual_activo=false sin asignación y dual_activo=true sin empresa. Ver ../C01-base-local/evidencia.md. No sustituye preview visual de los roles alumno/tutor ni móvil; UI01 sigue IN_PROGRESS.
