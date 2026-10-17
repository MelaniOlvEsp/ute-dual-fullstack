# Registro de respaldos y pruebas de restauración

Lo mantiene el responsable de los respaldos (DP-11, decisión del 2026-10-17). Una fila por respaldo relevante (el semanal
y el previo a una finalización o a una depuración) y una por cada prueba de restauración (una por trimestre). No se anotan
credenciales, identificadores de Drive ni datos personales. Procedimiento: [GUIA_DE_USO_Y_OPERACION.md](GUIA_DE_USO_Y_OPERACION.md), sección 6.

| Fecha | Tipo | Id del respaldo | Resultado | Responsable | Notas |
|---|---|---|---|---|---|
| 2026-10-17 | Respaldo `periodo` (entorno de validación C10: base nueva y carpeta de Drive propias) | `20261017T094255Z-periodo` | íntegro: 12 documentos y volcado | Validación C10 (datos sintéticos) | Antes de una depuración |
| 2026-10-17 | Respaldo `depuracion` (mismo entorno, tras la depuración) | `20261017T094434Z-depuracion` | íntegro: 6 documentos; 6 depurados sin copia | Validación C10 (datos sintéticos) | Registro de depuraciones |
| 2026-10-17 | Prueba de restauración aislada del primero, aplicando el registro del segundo | `20261017T094255Z-periodo` | VERIFICADA: 6 documentos restaurados, 6 depurados no reaparecen, conteos y huellas coinciden, descargas de muestra correctas | Validación C10 (datos sintéticos) | Destino y carpeta eliminados con `-Descartar` |
| 2026-10-17 | Respaldo del entorno de desarrollo del proyecto (base con datos de pruebas anteriores) | — | RECHAZADO (código 2): 569 documentos referenciados sin archivo en Drive (herencia del modo local previo a C10A) | Validación C10 | Es el comportamiento esperado: no se da por respaldado lo incoherente |
