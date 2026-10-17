# Guía de prueba con lector de pantalla (C12)

Objetivo: comprobar, con una persona y un lector de pantalla real, que los cinco recorridos principales se entienden de principio a fin sin ver la pantalla. Las revisiones automáticas (axe-core, `tools/auditoria-ui.js`) no sustituyen esta prueba. Duración: unos 30 a 40 minutos. La hace el responsable del proyecto (decisión D1 de C12, 2026-10-17); el resultado se anota en la tabla de abajo y en la evidencia de C12. No anotes contraseñas ni datos personales.

## Preparación

1. Arranca el sistema (`docker compose up -d --wait`) y abre `http://127.0.0.1:5174/login` en **Chrome** o **Edge**.
2. Cuentas: usa las cuentas sintéticas de `.secretos/cuentas_prueba.txt` (un alumno con reportes, el asesor y el coordinador). No uses cuentas reales.
3. Lector de pantalla (elige uno):
   - **Narrador de Windows:** `Windows + Ctrl + Intro` para activarlo y desactivarlo. `Bloq Mayús + Espacio` activa un control; `Bloq Mayús + F5` abre la lista de elementos.
   - **NVDA** (gratuito, nvaccess.org): `Ctrl` detiene la lectura; `Insertar + Espacio` alterna el modo de exploración; `H` salta entre encabezados, `D` entre regiones, `F` entre campos de formulario, `T` entre tablas.
4. Cierra otras aplicaciones con sonido y usa auriculares. Si puedes, cierra los ojos o apaga el monitor mientras recorres cada flujo.

## Qué observar en todos los recorridos

- Al abrir cada página, el lector anuncia el título y el encabezado principal (`h1`) y se puede saltar la barra de navegación a la región principal.
- Cada campo, lista desplegable y botón se anuncia con un nombre que dice para qué sirve (no «cuadro combinado» ni «botón» a secas).
- Las tablas se anuncian como tabla con sus encabezados de columna, y el contenedor desplazable se puede enfocar con Tab.
- Los avisos (error, éxito, estado) se leen sin que tengas que buscarlos.
- Nada obliga a usar el ratón.

## Recorridos

| # | Recorrido | Cuenta | Pasos |
|---|---|---|---|
| 1 | Inicio de sesión | Alumno | Abrir `/login`; llenar correo y clave solo con teclado; enviar; comprobar que se anuncia el foro. Probar también una clave incorrecta y comprobar que el error se lee. |
| 2 | Foro | Alumno | Recorrer los anuncios con `H`; cambiar a la pestaña «Buzón»; abrir y cerrar el menú lateral con teclado. |
| 3 | Entregar un reporte | Alumno | En «Mis reportes» localizar una semana con entrega pendiente; leer su estado; abrir «Ver versiones» y leer la tabla de versiones. |
| 4 | Revisión y firma | Asesor | En «Revisar y firmar reportes» filtrar por estado; abrir «Revisar»; leer los datos del estudiante; usar «Aprobar y firmar» o «Rechazar» (en un reporte de prueba). |
| 5 | Expediente | Alumno y coordinador | Alumno: «Mi expediente», elegir período y abrir un documento. Coordinador: «Expedientes», filtrar por carrera, abrir un expediente. |

## Resultado (llenar)

| # | Lector y navegador | ¿Se entiende de principio a fin? | Qué no se entendió o faltó (pantalla y elemento) |
|---|---|---|---|
| 1 | | | |
| 2 | | | |
| 3 | | | |
| 4 | | | |
| 5 | | | |

Fecha, quién la hizo y versión del lector: ____________________

Cada punto que no se entienda se registra como hallazgo de interfaz con la pantalla y el elemento; se corrige en una spec de corrección, no dentro de esta guía. Un recorrido no probado queda NO_VERIFICADA.
