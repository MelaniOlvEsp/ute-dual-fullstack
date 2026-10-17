# Índice documental

## Cómo interpretar los documentos

- CONFIRMADO: decisión explícita del usuario durante el levantamiento.
- PROPUESTO: diseño técnico o decisión operativa a validar en la spec correspondiente.
- PENDIENTE: falta información; no asumir autorización.
- EXISTENTE: localizado en código; no equivale a probado.
- REAL / SIMULADA / NO_VERIFICADA: calidad de la evidencia de validación.

Los requisitos confirmados prevalecen sobre el comportamiento heredado. Una propuesta no cambia una regla confirmada. Toda implementación nueva requiere una spec READY. Una duda bloquea únicamente la conducta afectada.

## Análisis

| Documento | Pregunta que resuelve |
|---|---|
| [Especificación funcional](analysis/ESPECIFICACION_FUNCIONAL.md) | Qué producto se necesita y para quién |
| [Reglas de negocio](analysis/REGLAS_DE_NEGOCIO.md) | Qué debe suceder en cada caso |
| [Roles y permisos](analysis/MATRIZ_DE_ROLES_Y_PERMISOS.md) | Quién puede hacer cada operación |
| [Criterios de aceptación](analysis/CRITERIOS_DE_ACEPTACION.md) | Cómo comprobar el resultado |
| [Flujos de pantalla](analysis/UX_Y_FLUJOS.md) | Cómo se utiliza |
| [Modelo de datos](analysis/MODELO_DE_DATOS.md) | Qué información se conserva y relaciona |
| [Arquitectura](analysis/DECISIONES_DE_ARQUITECTURA.md) | Cómo evolucionar el sistema |
| [Contrato API](analysis/CONTRATO_API.md) | Qué contratos existen y cuáles deben cambiar |
| [Archivos e importaciones](analysis/CONTRATO_DE_ARCHIVOS_E_IMPORTACIONES.md) | Cómo tratar PDFs, firmas, plantillas y CSV |
| [Estado actual](analysis/ESTADO_ACTUAL_Y_BRECHAS.md) | Qué existe y qué falta comprobar o construir |
| [Decisiones pendientes](analysis/DECISIONES_PENDIENTES.md) | Qué no está acordado todavía |

## Construcción

- [Plan maestro y backlog](construction/PLAN_MAESTRO.md)
- [Protocolo de trabajo](construction/PROTOCOLO_SDD_LITE.md)
- [Prompts reutilizables](construction/PROMPTS_DE_TRABAJO.md)
- [Validación y operación local](construction/VALIDACION_Y_OPERACION_LOCAL.md)
- [Guía de uso y operación del piloto](construction/GUIA_DE_USO_Y_OPERACION.md)
- [Registro de respaldos y pruebas de restauración](construction/REGISTRO_DE_RESPALDOS.md)
- [Índice de specs](../specs/README.md)
- [Plantilla de spec](../specs/_template/spec.md)
- [C01: base local](../specs/C01-base-local/spec.md)

## Fuentes del levantamiento

Conversación con el responsable del proyecto, código local y documentación existente del portal; estructura de docs/analysis y docs/construction de PC-Refresh como referencia metodológica. No se importan sus reglas de negocio, stack ni requisitos de integraciones.

Cada cambio de decisión debe indicar fecha, motivo y documentos/specs afectados. No duplicar todo el requisito dentro de cada spec: enlazar los IDs RN, US y AC.
