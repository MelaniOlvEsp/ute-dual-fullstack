# Protocolo SDD Lite

## Autoridades y estado

Responsable del proyecto confirma requisitos y acepta entregas. AGENTS.md rige ejecución, análisis define comportamiento, plan organiza incrementos y spec concreta el alcance. Ante contradicción con instrucción reciente del usuario, aplicar esa instrucción y actualizar documentos afectados. No importar requisitos de PC-Refresh.

Estados: DRAFT → READY → IN_PROGRESS → DONE.
La revisión usa veredictos APPROVED o CHANGES_REQUESTED; no son estados de spec.

## Preparación

Crear spec breve con problema, alcance, exclusiones, referencias US/RN/AC, decisiones, contratos, archivos previstos y pruebas. Una DP bloqueante debe resolverse antes de marcar READY. Se puede reducir alcance sin implementar la conducta bloqueada, dejando explícita la exclusión.

Pedir aprobación del resultado concreto de la spec; la autorización explícita de implementación sobre una spec sin bloqueos permite pasar READY e IN_PROGRESS. No pedir aprobación repetida para acciones ya autorizadas.

## Implementación

Leer spec y código. Reutilizar componentes; cambios acotados. Actualizar contratos, fixtures y documentación afectada juntos. Ejecutar pruebas necesarias. Registrar evidencia real y limitaciones. Dejar IN_PROGRESS al terminar.

## Revisión / preview

“Preview” significa revisar el resultado y, cuando hay UI o PDF, mostrarlo visualmente. Incluye revisión técnica del diff contra spec y pruebas, no solo capturas.

Por defecto puede hacerse en este mismo chat; no requiere crear otro chat ni subagentes. Si el usuario pide revisión independiente, usar subagente de solo lectura y darle spec, diff, archivos y evidencia. No afirmar independencia si revisa el mismo agente.

Reportar defectos materiales con escenario, impacto y ubicación. No añadir observaciones cosméticas como bloqueos. APPROVED si no hay defectos materiales en alcance; integración no probada se identifica y bloquea cierre si es un AC requerido.

## Correcciones y cierre

Con CHANGES_REQUESTED, corregir hallazgos dentro de alcance, ejecutar pruebas afectadas y volver a revisar cambios relevantes. Spec sigue IN_PROGRESS.

Tras aprobación humana de cierre y evidencia suficiente: DONE, resumen de resultado, limitaciones y siguiente spec DRAFT. Commit/push solo si autorizados explícitamente; cerrar spec no los autoriza.

## Evidencia mínima

Tabla con comprobación, comando/pasos, entorno/versión, resultado y clase REAL/SIMULADA/NO_VERIFICADA. No copiar antiguos “tests passed” sin comprobar código correspondiente. No ejecutar pruebas repetidas sin cambio o duda que lo justifique.

## Cambios de alcance

Si una nueva regla altera seguridad, período, promedio o conservación, actualizar análisis y spec antes de implementarla. Las dudas no detienen inspección ni trabajo independiente. Mantener registro breve de decisiones, sin crear burocracia por cada cambio de texto.
