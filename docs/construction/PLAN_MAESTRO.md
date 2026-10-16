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
| C09 — Foro, buzón y plantillas | Entrada al foro, conversación funcional y pareja Word/PDF administrable. | US-05/13/14; AC-21/22/23 | C08; DP-09 |
| C10 — Validación integral local | Recorrido completo, controles negativos, restauración, guía de uso y operación. | Todas; AC-24 | C09; responsable/retención DP-11 |

Dependencia lineal por simplicidad; permite correcciones pequeñas de infraestructura necesarias para el incremento activo. No adelantar módulos completos.

## Qué significa terminar cada incremento

Spec READY antes de código; implementación y evidencia proporcional; revisión contra diff final; correcciones verificadas; aprobación humana de cierre. DONE solo si AC del alcance se cumplen con evidencia adecuada. Integración externa no comprobada sigue NO_VERIFICADA.

C01 no debe declararse producto completo porque arranca. C10 requiere servicios reales del piloto; puede usar almacenamiento local aprobado, pero no declarar Drive validado si no se utilizó.

## Primer incremento

[C01-base-local](../../specs/C01-base-local/spec.md) está preparado en DRAFT. Fija línea base y elimina incompatibilidades inmediatas; no resuelve calendario a partir de supuestos.

Los incrementos posteriores se redactan como specs completas justo antes de ejecutarse. Esto evita diez specs extensas que queden desactualizadas después de corregir la base.

## Decisiones justo antes de necesitarlas

DP-01/03/04: antes del calendario. Resueltas el 2026-10-15 para C04: DP-01 completa, DP-03 y DP-04 en lo que C04 necesita (baja inclusiva; períodos manuales, America/Mexico_City, sin solapamiento). Quedan para C07 la etiqueta por cierre anticipado (DP-03) y la recepción simultánea (DP-04).
DP-05: resuelta el 2026-10-15; conservar catálogo, abreviaciones y nomenclatura de la base institucional y aplicar la promoción aprobada.
DP-06/08: antes de carga de reportes. DP-08, DP-12 (fechas declaradas: solo inicio ≤ fin) y DP-13 (entrega solo con período abierto) resueltas el 2026-10-15 para C05; DP-06 solo afecta el tratamiento especial de períodos vacacionales, que C05 no incluye.
DP-02/07: antes de revisión/firma. La spec C06 está en DRAFT desde el 2026-10-15 (C05 DONE) y DP-02, DP-07 y DP-08 ya están resueltas (DP-02/07 el 2026-10-16).
DP-11: antes de cierre/uso real.
DP-09: antes de cerrar comunicación.

## Alcance de la documentación actual

Define requisitos, aceptación, diseño propuesto, brechas y flujo de trabajo. No modifica código, SQL, credenciales, paquetes ni datos. Las instrucciones de operación existentes deberán actualizarse con resultados reales en C01/C10.
