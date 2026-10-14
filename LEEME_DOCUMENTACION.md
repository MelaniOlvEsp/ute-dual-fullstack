# Formación Dual — documentación y ejecución

Fecha de corte: 14 de octubre de 2026.

Este paquete describe el producto acordado con el responsable del proyecto y organiza su continuación. No afirma que el sistema actual cumpla todos los requisitos. La autorización recibida cubre crear documentación; las specs de implementación permanecen en DRAFT.

## Empezar

1. Leer [índice documental](docs/README.md) y [estado actual](docs/analysis/ESTADO_ACTUAL_Y_BRECHAS.md).
2. Revisar [decisiones pendientes](docs/analysis/DECISIONES_PENDIENTES.md).
3. Leer la [primera spec](specs/C01-base-local/spec.md).
4. Para iniciar código, usar los [prompts](docs/construction/PROMPTS_DE_TRABAJO.md) indicando la spec aprobada.

El ciclo es: spec DRAFT → aprobación del alcance → implementación → revisión → correcciones si corresponden → aprobación de cierre → DONE y siguiente spec DRAFT.

Los documentos existentes README_INTEGRACION.md y database/README.md describen una versión anterior. Se conservan como evidencia; no sustituyen estas reglas funcionales. El SQL de database es una propuesta heredada, no el esquema definitivo aprobado.

## Estructura

- docs/analysis: producto, reglas, permisos, aceptación, datos, arquitectura, contratos, UX y brechas.
- docs/construction: plan, protocolo, prompts y validación local.
- specs: plantilla, primer incremento y registro de estado.
- AGENTS.md: instrucciones para agentes; CLAUDE.md remite a las mismas.

No se ejecutaron migraciones ni pruebas del software al crear este paquete. Las revisiones de esta entrega son documentales.
