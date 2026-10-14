# Reglas de negocio

CONFIRMADO salvo donde se indique PROPUESTO o PENDIENTE. Fechas de actividad se modelan como fechas civiles; instantes de entrega, revisión y cierre incluyen zona. Zona operativa propuesta: America/Mexico_City, confirmar DP-04.

## Identidad y organización

- RN-01: solo alumno, tutor académico y coordinador Dual. El servidor aplica permisos.
- RN-02: tutor crea grupo y carga matrícula/nombre; solo matrículas autorizadas se registran con correo institucional correspondiente. Sin verificación por correo.
- RN-03: coordinador crea tutores; contraseña temporal y cambio obligatorio. Tutor genera recuperación temporal del alumno. No exponer claves después de la respuesta inicial.
- RN-04: tutores pueden atender las tres carreras. Alumno solo ve sus reportes, expediente y conversaciones.
- RN-05: cambios de grupo por período conservan pertenencia histórica. Promoción masiva con confirmación del tutor es PROPUESTA; nomenclatura oficial pendiente DP-05.
- RN-06: la incorporación a empresa tiene fecha real de inicio. Continúa entre períodos; la baja detiene obligaciones futuras, conserva historia y permite atrasos previos si recepción sigue abierta. Semana parcial de baja: DP-03.

## Semanas y entregas

- RN-07: semanas lunes–domingo; primera semana parcial desde incorporación. No exigir 18 semanas a todos ni usar grado académico como ID de período.
- RN-08: período de un reporte se determina por fecha de fin, no por fecha de subida ni por período marcado como actual. Semana que termina en mayo corresponde a mayo–agosto. Fecha de fin aplicable en semanas limítrofes: DP-01.
- RN-09: se puede entregar durante la semana, por ejemplo viernes. A partir del lunes siguiente, lo no entregado aparece atrasado. No habilitar semanas futuras solo porque la anterior fue aprobada.
- RN-10: recibir una semana no depende de aprobar otras. Distinguir no entregado, atrasado, pendiente de revisión, rechazado y aprobado.
- RN-11: vacaciones no suspenden por sí solas los reportes; pueden indicar período vacacional. Calificación sin actividad: pendiente DP-06.
- RN-12: alumno adjunta PDF firmado por empresa y captura inicio, fin y nota entera 1–10. El sistema valida archivo y datos; el tutor verifica coincidencia visual. No afirmar validación automática de firma empresarial.
- RN-13: permitir atrasos y reenvíos solo mientras esté abierta la recepción del período correspondiente.
- RN-14: rechazo requiere nota explicativa. Reenvío conserva archivo, datos y decisiones anteriores. Una versión vigente por obligación semanal; repetición/concurrencia no crea dos reportes lógicos.
- RN-15: tutor puede corregir fechas y nota con trazabilidad del valor previo, nuevo, autor e instante. Corrección que cambie semana/período requiere regla DP-02; no mover silenciosamente el expediente.
- RN-16: aprobación incorpora firma del tutor; conservar original y resultado firmado. Formato visual pendiente DP-07. Una aprobación no se completa si falla el guardado del firmado.
- RN-17: después de aprobar, el alumno no reemplaza el archivo. Rectificación excepcional posterior a aprobación/finalización no está autorizada para V1; requiere decisión explícita.

## Cierre y evaluación

- RN-18: solo coordinador cierra manualmente recepción, incluso antes del fin calendario. No cierre automático ni margen automático de siete días. No trasladar reportes futuros del período cerrado al siguiente.
- RN-19: cierre de recepción permite que el tutor revise y apruebe reportes ya recibidos. Los rechazados no pueden reenviarse después del cierre. Informar claramente esta consecuencia.
- RN-20: coordinador finaliza evaluación cuando no quedan reportes pendientes de revisión. Rechazados y no entregados no impiden finalizar.
- RN-21: promedio = suma de notas vigentes aprobadas / cantidad de reportes aprobados del alumno y período. No entregados, rechazados y pendientes no aportan cero ni entran al denominador.
- RN-22: promedio provisional hasta finalizar; final después. Mostrar dos decimales; sin aprobados mostrar “Sin calificación”. Redondeo decimal HALF_UP es PROPUESTA técnica a fijar en C07.
- RN-23: período calendario, recepción y evaluación son conceptos independientes. Puede revisarse un período anterior mientras otro recibe entregas. Apertura manual/automática y solapamiento de recepción: DP-04.
- RN-24: mostrar fechas calendario y cierre efectivo por separado. Reportes no recibidos por cierre anticipado no deben atribuirse automáticamente a incumplimiento del alumno; etiquetas de obligación cortada por cierre en DP-03.

## Expediente y comunicación

- RN-25: expediente conserva reportes aprobados y firma, notas, fechas, período y grupo histórico. Alumno descarga los suyos de cualquier período.
- RN-26: coordinador carga Word y PDF de plantilla común a las tres carreras. Versionar plantilla sin alterar reportes históricos.
- RN-27: foro es pantalla inicial tras completar acceso obligatorio. Tutores/coordinador publican; alumnos consultan.
- RN-28: buzón admite conversación del alumno con todos los tutores y coordinador. Otros alumnos no pueden verla. Política de respuesta a hilo cerrado: DP-09.
- RN-29: bajas no deben borrar expedientes, versiones o decisiones. Base inicial vacía; no ejecutar limpieza histórica de la demo como parte del arranque.

## Transiciones propuestas para implementación

Recepción: NO_ABIERTA → ABIERTA → CERRADA. Evaluación: EN_CURSO → FINALIZADA, solo con recepción cerrada y cero pendientes de revisión. Reapertura no incluida sin decisión.

Reporte: SIN_ENTREGA → PENDIENTE_REVISION → APROBADO o RECHAZADO. RECHAZADO → PENDIENTE_REVISION crea versión nueva, únicamente con recepción abierta. ATRASADO es un indicador temporal de una obligación sin entrega, no un archivo o estado de aprobación.

Cierre y entrega concurrentes deben serializarse: una entrega aceptada antes del cierre permanece revisable; después del cierre se rechaza sin crear reporte. Igual protección entre revisión y finalización.
