# Prompts de trabajo

Guía humana; los bloques no son instrucciones automáticas por leer este archivo. Reemplazar CXX/ruta por la spec correspondiente. “Preview” aquí incluye revisión técnica y visual cuando aplica.

## 1. Implementación

```text
Formación Dual — IMPLEMENT CXX
Autorizo implementar specs/CXX-slug/spec.md conforme a su alcance.
Lee AGENTS.md, la spec y los documentos enlazados. Si no tiene decisiones bloqueantes, registra esta autorización, pasa de DRAFT a READY y luego a IN_PROGRESS.
Reutiliza el código existente, completa el incremento y actualiza contratos, fixtures y documentación afectados.
Verifica los criterios de aceptación con pruebas proporcionales. Distingue evidencia real, simulada y no verificada.
Si una decisión nueva es indispensable, detén solo esa conducta y presenta la decisión concreta; continúa lo independiente.
Entrega resultado, pruebas y limitaciones. Deja la spec IN_PROGRESS.
No hagas commit ni push y no adelantes el siguiente incremento.
```

## 2. Revisión / preview

```text
Formación Dual — REVIEW / PREVIEW CXX
Revisa el resultado contra specs/CXX-slug/spec.md, los requisitos enlazados y el diff real.
Comprueba funcionamiento, permisos, conservación del historial, contratos y evidencia de pruebas.
Si cambió interfaz o PDF, muestra el resultado y verifica visualmente los recorridos afectados.
No modifiques código durante esta revisión. No repitas pruebas con evidencia válida salvo una duda concreta.
Reporta solo defectos materiales, con escenario, impacto y ubicación.
Concluye APPROVED o CHANGES_REQUESTED, aclara qué revisión fue técnica/visual y qué integraciones no se comprobaron.
No cierres la spec ni hagas commit/push.
```

Para revisión independiente, añadir: “Usa un subagente reviewer de solo lectura; entrégale la spec, el diff y la evidencia. No le encargues implementar correcciones.”

## 3. Correcciones, si se requieren

```text
Formación Dual — FIX CXX
Autorizo corregir los hallazgos de la última revisión de CXX.
Corrige dentro del alcance aprobado, ejecuta pruebas afectadas y realiza una revisión focal de los cambios.
No amplíes el alcance, no cierres la spec y no hagas commit/push.
```

## 4. Cierre y siguiente spec

```text
Formación Dual — CLOSE CXX + NEXT SPEC
Otorgo aprobación de cierre de CXX, sujeto a que el resultado revisado esté aprobado y sus criterios tengan evidencia suficiente.
Marca DONE y registra lo entregado, pruebas, limitaciones y esta aprobación.
Consulta el plan maestro y prepara o actualiza la siguiente spec en DRAFT.
Presenta únicamente las decisiones que bloqueen ese siguiente incremento.
No implementes la siguiente spec. No hagas commit ni push.
```

## Primer mensaje listo para usar

```text
Formación Dual — IMPLEMENT C01
Autorizo implementar specs/C01-base-local/spec.md.
Sigue el prompt IMPLEMENT de docs/construction/PROMPTS_DE_TRABAJO.md y AGENTS.md.
```

No enviar este último mensaje hasta revisar C01. La autorización para crear documentación no equivale a autorización para ejecutar SQL o implementar C01.
