# Formación Dual — instrucciones de ejecución

## Fuentes y alcance

Leer docs/README.md, docs/construction/PLAN_MAESTRO.md y la spec activa. Reglas confirmadas en docs/analysis/REGLAS_DE_NEGOCIO.md; dudas en DECISIONES_PENDIENTES.md. No copiar requisitos ni stack de PC-Refresh.

La documentación describe objetivo; README_INTEGRACION.md y database/README.md contienen afirmaciones históricas que deben verificarse. No asumir que código presente está probado.

Trabajar un incremento por vez. Antes de implementar, spec DRAFT y aprobación explícita del usuario; registrar READY y luego IN_PROGRESS. La autorización para documentar no autoriza ejecutar SQL o implementar. No pedir aprobación repetida si el usuario ya autorizó el alcance.

## Reglas esenciales

Tres roles, tutores transversales, alumnos limitados a recursos propios. Período calendario distinto de grado académico. Cierre de recepción manual del coordinador; permite revisión de recibidos. Finalización posterior congela promedio de aprobados. Conservar versiones, original/firmado, grupo histórico y bajas sin borrar expediente.

No resolver DP abiertas por suposición cuando cambien calendario, permisos, notas o conservación. Detener solo conducta afectada y continuar trabajo independiente.

## Implementación

Conservar FastAPI/PostgreSQL y Svelte por capas; dominio independiente de persistencia/framework cuando aporte valor. SOLID y separación pragmática, sin capas vacías ni reescrituras amplias. SQL parametrizado, permisos en API, archivos privados, validación explícita. No incorporar servicios o infraestructura innecesarios.

Base nueva de pruebas y datos sintéticos. No ejecutar limpiezas históricas ni SQL sobre destinos no verificados. No imprimir/subir secretos, tokens, firmas personales ni PII. No alterar archivos ajenos al alcance.

## Validación y revisión

Seguir docs/construction/PROTOCOLO_SDD_LITE.md. Evidencia REAL, SIMULADA o NO_VERIFICADA. Pruebas proporcionales; build/contratos no sustituyen recorrido real. Actualizar API/frontend/fixtures juntos si cambia contrato. Revisión contra diff y spec; preview visual si cambió UI/PDF. No afirmar revisión independiente si la hizo el mismo agente.

No crear subagentes por defecto. Usarlos cuando el usuario los solicite o autorice una revisión independiente con subagente. No crear otro chat sin solicitud.

## Cierre

DONE solo tras criterios cumplidos, revisión aprobada y aprobación humana de cierre. Preparar siguiente spec DRAFT. No hacer commit ni push sin autorización explícita. Resumir cambios, pruebas y limitaciones.
