# UX y flujos de pantalla

Diseño objetivo, no capturas de interfaz ya terminada. Mantener Svelte y componentes existentes cuando sirvan.

## Acceso y navegación

Login → cambio obligatorio si corresponde → foro. Registro solo para matrícula previamente cargada; errores explican el siguiente paso sin revelar datos de otras cuentas. Recuperación orienta a contactar tutor.

Navbar alumno: Foro, Reportes, Mi expediente, Buzón, Perfil.
Navbar tutor: Foro, Revisión, Pendientes de entrega, Alumnos y grupos, Empresas/asignaciones, Expedientes, Buzón, Firma/perfil.
Navbar coordinador: Foro, Tutores, Períodos y cierres, Expedientes, Plantillas, Buzón, Perfil.
Agrupación visual propuesta; no crear roles por cada menú.

## Alumno: reportes

1. Mostrar período e incorporación; si falta empresa/inicio, explicar que tutor debe configurarlos.
2. Dos descargas visibles: plantilla Word y PDF.
3. Lista de semanas con rango, estado y acción. Separar “Sin entregar”, “Atrasado”, “En revisión”, “Rechazado” y “Aprobado”.
4. Seleccionar semana elegible, adjuntar PDF, capturar fechas y nota; presentar resumen antes de enviar.
5. Tras recibir, indicar que está en revisión; permitir otras semanas.
6. Rechazo muestra nota y permite nueva versión si recepción está abierta.
7. Si cerró, explicar que ya no acepta archivos aunque tutor siga revisando.

No sugerir que falta entregar una semana futura ni ocultar atrasos cuando exista un reporte posterior.

## Tutor: revisión

Bandeja con filtros período/carrera/grupo/estado y alumno. Abrir detalle con PDF y datos lado a lado. Comparar fechas y nota, corregir con trazabilidad y aprobar con firma o rechazar con nota obligatoria. Mostrar versión revisada y evitar decisión sobre versión obsoleta.

Lista de faltantes comparte calendario con alumno. Identificar diferencia entre nunca entregado y rechazado. Cierre anticipado no debe etiquetar automáticamente como moroso a quien no pudo entregar semana futura.

## Organización académica

Crear grupo con nomenclatura aprobada, agregar alumnos individual/CSV y asignar empresa/inicio. Actualizar grupo por período sin reescribir el histórico. Baja con fecha y resumen de efecto; no botón ambiguo “eliminar” que borre expediente.

## Coordinador: cierre

Panel por período muestra fechas calendario, recepción, evaluación, conteos recibidos/pendientes/rechazados/faltantes y promedios provisionales.

Acción “Cerrar recepción” muestra consecuencia: alumnos ya no suben ni reemplazan; tutor sigue revisando. Confirmación identifica período exacto.
Acción “Finalizar evaluación” disponible solo con recepción cerrada y cero pendientes. Muestra resumen y convierte promedios en finales. No mover fechas calendario ni abrir otro período implícitamente.

## Expediente

Alumno, carrera/grupo histórico, período, reportes aprobados con descarga, nota validada, promedio y conteo usados. Selector de períodos anteriores. Usuario alumno solo el suyo; personal consulta todos.

## Plantillas y buzón

Coordinador previsualiza pareja Word/PDF antes de publicar. Mostrar versión/fecha vigente.
Buzón: listado de hilos, detalle cronológico, autores y respuesta. Alumno ve solo propios, personal todos. Cierre claramente visible según política DP-09.

## Estados comunes y accesibilidad

Carga, vacío, error y reintento; etiquetas asociadas a campos; teclado y foco; no usar color como única señal. Botón ocupado evita doble envío, pero servidor también controla duplicación. Probar pantallas principales en ancho de escritorio y móvil sin esconder acciones esenciales.
