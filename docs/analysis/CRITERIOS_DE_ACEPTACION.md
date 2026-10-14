# Criterios de aceptación y trazabilidad

Estos escenarios son objetivos; no resultados de pruebas. Evidencia inicial: NO_VERIFICADA. Casos afectados por DP abiertas se completan antes de aprobar su spec.

| ID | Dado / cuando / entonces | Reglas | Incremento |
|---|---|---|---|
| AC-01 | BD vacía: instalación documentada crea esquema y datos sintéticos; login no consulta columnas ausentes. | RN-01,29 | C01 |
| AC-02 | Matrícula no autorizada intenta registro: se rechaza; tutor la carga en grupo y puede registrarse con correo coincidente. | RN-02 | C02 |
| AC-03 | Clave temporal: solo permite cambio obligatorio; recuperación invalida sesión anterior. | RN-03 | C02 |
| AC-04 | Alumno modifica ID de expediente/PDF/buzón: no obtiene datos ajenos; tutor accede a las tres carreras. | RN-04,28 | C02/C08/C09 |
| AC-05 | Alumno cambia grupo: historial anterior conserva grupo y grado; baja no borra expediente. | RN-05,06,29 | C03 |
| AC-06 | Incorporación miércoles: primera semana parcial; dos alumnos con distintas incorporaciones tienen obligaciones correctas. | RN-06,07 | C04 |
| AC-07 | Semana termina en mayo: pertenece a mayo–agosto aunque empiece en abril; subir en junio no cambia período. | RN-08 | C04 |
| AC-08 | Viernes de semana vigente: permite entregar; lunes siguiente sin entrega: muestra atraso en alumno y tutor. | RN-09 | C04 |
| AC-09 | Semana anterior pendiente de revisión: alumno entrega otra semana válida sin bloqueo. | RN-10 | C05 |
| AC-10 | PDF y nota: acepta enteros 1 y 10; rechaza 0, 11 y 8.5; valida fechas y contenido real, límites iguales en cliente/API. | RN-12 | C05 |
| AC-11 | Reporte rechazado con nota: reenvío conserva versión anterior y crea nueva vigente; dos envíos simultáneos no duplican obligación. | RN-13,14 | C05 |
| AC-12 | Tutor corrige nota/fechas: se conserva antes/después; cambio de período no evade recepción cerrada. | RN-15 | C06 |
| AC-13 | Aprueba con firma: original y firmado legibles conservados; si falla guardado, no queda falsamente aprobado. | RN-16 | C06 |
| AC-14 | Coordinador cierra anticipadamente con reportes por revisar: bloquea entregas/reenvíos, permite revisión de recibidos. | RN-18,19 | C07 |
| AC-15 | Tutor intenta cerrar por API: denegado. Alumno envía concurrentemente con cierre: resultado consistente con orden transaccional. | RN-18 | C07 |
| AC-16 | Notas aprobadas 8,9,10 y un rechazo: promedio 9.00; sin aprobados: Sin calificación, no 0.00. | RN-21,22 | C07 |
| AC-17 | Hay pendiente de revisión: finalizar se rechaza; resuelto el último, coordinador finaliza y congela promedio. | RN-20,22 | C07 |
| AC-18 | Finaliza un período mientras el nuevo recibe: operación no modifica el nuevo; futuras semanas del cerrado no se reasignan. | RN-23,24 | C07 |
| AC-19 | Alumno consulta dos períodos y descarga aprobados: documentos correctos, grupo histórico y promedio correspondiente. | RN-25 | C08 |
| AC-20 | PDF en navegador: carga autenticada, zoom/lectura y descarga funcionan; error visible si falla y sin acceso público alternativo. | RN-25 | C08 |
| AC-21 | Coordinador publica nueva pareja Word/PDF: todos descargan versión vigente; fallar un archivo no publica pareja incompleta. | RN-26 | C09 |
| AC-22 | Login normal termina en foro; cambio obligatorio ocurre antes. Alumno no publica anuncios por API. | RN-27 | C09 |
| AC-23 | Alumno envía, tutor responde, coordinador consulta y alumno responde: conversación persiste y otro alumno no accede. | RN-28 | C09 |
| AC-24 | Restauración en entorno local aislado recupera BD y documentos; recorrido integral funciona con servicios reales. | RN-25,29 | C10 |

## Escenarios de calendario que requieren decisión

DP-01: viernes 30/04/2027 frente a domingo 02/05/2027. Definir si manda fecha del PDF o fin de semana calendario; no convertir esta ambigüedad en un test arbitrario.
DP-03: baja un miércoles, y cierre anticipado antes de terminar una semana. Registrar obligación final y etiqueta de semanas fuera de recepción.
DP-06: reporte vacacional sin evaluación empresarial; no inventar nota ni excluirlo sin decisión.

## Evidencia

Cada ejecución registra comando/recorrido, fecha, versión del código o hash disponible, entorno, datos sintéticos, resultado y limitaciones. REAL indica ejecución de ese nivel; un unit test real con repositorio falso sigue siendo evidencia SIMULADA para la integración. No trasladar aprobaciones de los README antiguos a esta versión.
