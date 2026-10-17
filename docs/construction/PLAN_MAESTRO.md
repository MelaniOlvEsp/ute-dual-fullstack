# Plan maestro de construcción

Estado inicial: documentación creada; ningún incremento implementado o aceptado por esta entrega. Trabajar un incremento por vez, reutilizando código útil de la demo. No reescribir el sistema desde cero.

## Backlog y secuencia

| Incremento | Resultado concreto | US / AC | Dependencias y decisiones |
|---|---|---|---|
| C01 — Base local reproducible | Inventario ejecutable, esquema inicial coherente en BD vacía, fixtures, comandos y pruebas base. | AC-01 | Ninguna DP funcional bloquea diagnóstico/base. |
| C02 — Identidad y accesos | Registro autorizado, tres roles, temporales/revocación, bajas lógicas y autorización de objeto. | US-01/03; AC-02/03/04 | C01 |
| C03 — Grupos e incorporación | Matrículas por grupo, historia por período, empresa/inicio/baja, carreras correctas. | US-02/04; AC-05 | C02; DP-05 resuelta 2026-10-15 |
| C04 — Calendario y pendientes | Obligaciones individuales y compartidas por alumno/tutor, períodos por fechas, semanas parciales. | US-07; AC-06/07/08 | C03; DP-01/03/04 |
| C05 — Entregas y versiones | PDF real, nota entera, entregas independientes y reenvíos sin pérdida. | US-06/09; AC-09/10/11 | C04 DONE; DP-08/12/13 (DP-06 no bloquea) |
| C06 — Revisión y firma | Correcciones trazables, rechazo con nota y firmado visualmente validado. | US-08; AC-12/13 | C05; DP-02/07/08 |
| C07 — Cierre y calificación | Cierre manual de recepción, revisión posterior, finalización y promedio. | US-11/12; AC-14/15/16/17/18 | C06; DP-04/11 |
| C08 — Expediente y visor | Historia propia y del personal, descarga privada y visor fiable. | US-10/11; AC-04/19/20 | C07 |
| C08B — Archivo y depuración | Depuración de los archivos de un período tras descargar el paquete ZIP: advertencia, confirmación y «Conservar todo»; se conservan notas, promedios y el historial. | DP-14 (RN-25/RN-29) | C08 DONE (2026-10-16); C08B DONE (2026-10-17); DP-14 resuelta 2026-10-16 (detalle y respaldos DP-11 al redactar la spec) |
| C09 — Foro, buzón y plantillas | Entrada al foro, conversación funcional y pareja Word/PDF administrable. | US-05/13/14; AC-21/22/23 | C08; DP-09 |
| C10A — Almacenamiento en Drive (DONE 2026-10-17, probado con Drive real) | Contrato de almacenamiento privado con adaptador de Drive (cuenta de prueba, OAuth), sin archivos locales; los smokes C01–C09 pasan con Drive. | RN-12/16/25; AC-10/11/24; DP-08 | C09 DONE; decisión del responsable 2026-10-17; D1 (autenticación) y D2 (temporales) |
| C10 — Validación integral local (DONE 2026-10-17) | Recorrido completo, controles negativos, respaldo y restauración en Drive, guía de uso y operación. | Todas; AC-24 | C10A DONE; DP-11 resuelta (D1); C10 DONE (2026-10-17) |

Dependencia lineal por simplicidad; permite correcciones pequeñas de infraestructura necesarias para el incremento activo. No adelantar módulos completos.

## Qué significa terminar cada incremento

Spec READY antes de código; implementación y evidencia proporcional; revisión contra diff final; correcciones verificadas; aprobación humana de cierre. DONE solo si AC del alcance se cumplen con evidencia adecuada. Integración externa no comprobada sigue NO_VERIFICADA.

C01 no debe declararse producto completo porque arranca. C10 requiere servicios reales del piloto; el almacenamiento del piloto es Drive (C10A) y C10 lo validó con la cuenta de pruebas realmente utilizada (evidencia de C10).

## Primer incremento

[C01-base-local](../../specs/C01-base-local/spec.md) está preparado en DRAFT. Fija línea base y elimina incompatibilidades inmediatas; no resuelve calendario a partir de supuestos.

Los incrementos posteriores se redactan como specs completas justo antes de ejecutarse. Esto evita diez specs extensas que queden desactualizadas después de corregir la base.

## Decisiones justo antes de necesitarlas

DP-01/03/04: antes del calendario. Resueltas el 2026-10-15 para C04: DP-01 completa, DP-03 y DP-04 en lo que C04 necesita (baja inclusiva; períodos manuales, America/Mexico_City, sin solapamiento). Quedan para C07 la etiqueta por cierre anticipado (DP-03) y la recepción simultánea (DP-04).
DP-05: resuelta el 2026-10-15; conservar catálogo, abreviaciones y nomenclatura de la base institucional y aplicar la promoción aprobada.
DP-06/08: antes de carga de reportes. DP-08, DP-12 (fechas declaradas: solo inicio ≤ fin) y DP-13 (entrega solo con período abierto) resueltas el 2026-10-15 para C05; DP-06 solo afecta el tratamiento especial de períodos vacacionales, que C05 no incluye.
DP-02/07: antes de revisión/firma. La spec C06 pasó a READY el 2026-10-16 y a IN_PROGRESS el mismo día (C05 DONE); DP-02, DP-07 y DP-08 ya están resueltas (DP-02/07 el 2026-10-16).
DP-11: antes de cierre/uso real. La spec C07 se cerró el 2026-10-16 (DP-04, DP-03 y DP-11 resueltas el mismo día). La spec C08 se cerró el 2026-10-16 (exportación ZIP y visor implementados; DP-14 define el archivo y la depuración, que se implementa en C08B). La spec C08B se cerró el 2026-10-17 (D1 a D3 resueltas el 2026-10-16; depuración de archivos implementada). La spec C09 se cerró el 2026-10-17 (D1 a D3 resueltas el mismo día: política del hilo cerrado y moderación de anuncios, DP-09, y plantilla administrable Word + PDF). La spec C10 se cerró el 2026-10-17 (D1 a D4 resueltas; recorrido integral, respaldo y restauración probados con Drive real; hallazgos de interfaz H1 a H3 pendientes de una spec de corrección). El 2026-10-17 el responsable decidió que los archivos y los respaldos viven en Drive y no se guarda nada local (base de datos en Docker en el equipo, cuenta de Google de prueba): se añadió C10A (almacenamiento en Drive) antes de C10, con D1 y D2 resueltas el mismo día (cuenta de pruebas con OAuth y reautorización cada 7 días, y archivos temporales transitorios; falta la orden de pasar a READY); la política de respaldos de C10 (DP-11) quedó resuelta el 2026-10-17 (responsable el responsable del proyecto, copia semanal y antes de cada finalización o depuración, 8 semanales y 4 mensuales, prueba de restauración trimestral).
DP-09: antes de cerrar comunicación.

## Alcance de la documentación actual

Define requisitos, aceptación, diseño propuesto, brechas y flujo de trabajo. No modifica código, SQL, credenciales, paquetes ni datos. Las instrucciones de operación existentes deberán actualizarse con resultados reales en C01/C10.
