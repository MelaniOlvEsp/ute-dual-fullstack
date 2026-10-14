# Especificación funcional — Formación Dual

## Objetivo confirmado

Digitalizar el proceso en que un alumno elabora un reporte semanal, obtiene firma y calificación de su empresa, lo entrega a la universidad y el asesor académico lo revisa, firma y registra en su expediente. El promedio de reportes aprobados determina la calificación por período calendario.

El sistema será utilizado por alumnos y personal. El primer entorno será local, con datos sintéticos y base vacía. Se estima menos de 100 alumnos; no es una medición de concurrencia. La prioridad es completar el flujo y probarlo. No hay fecha de entrega concreta.

## Alcance

Incluye tres roles: alumno, tutor académico (también llamado asesor académico) y coordinador Dual. Atiende TIC, Logística y Mercadotecnia. Los tutores tienen acceso transversal a las tres carreras.

Incluye acceso, grupos y matrículas autorizadas, empresas e incorporación a Dual, calendario individual de reportes, entregas y correcciones, firma académica, expediente histórico, promedio por período, cierre manual, plantillas administrables, foro y buzón.

Excluye Becas, acceso de empresas al portal, firma criptográfica certificada, evaluación automática del PDF por OCR/IA, correo de verificación y recuperación por email. No incluye despliegue productivo o contratación de servicios en esta fase.

## Lenguaje común

| Término | Significado |
|---|---|
| Período | Enero–abril, mayo–agosto o septiembre–diciembre de un año |
| Cuatrimestre académico | Número cursado por el alumno/grupo; no identifica un período |
| Incorporación Dual | Participación del alumno en empresa, con fecha de inicio y eventual baja |
| Semana de reporte | Intervalo semanal asociado a la participación del alumno |
| Fecha del documento | Fechas de actividad que alumno y empresa escriben en el reporte |
| Pendiente de entrega | Obligación que aún no tiene un reporte recibido |
| Pendiente de revisión | Reporte recibido que espera decisión del tutor |
| Cierre de recepción | Bloqueo de nuevos archivos del período; permite revisar los recibidos |
| Finalización de evaluación | Confirmación del promedio final y congelación de la evaluación |

La relación exacta entre fechas del documento y semana calendario, en especial viernes frente a domingo, se resuelve en DP-01.

## Historias de usuario

| ID | Historia |
|---|---|
| US-01 | Como coordinador, doy de alta tutores y administro sus accesos. |
| US-02 | Como tutor, creo grupos y cargo matrícula/nombre para autorizar el registro. |
| US-03 | Como alumno autorizado, creo mi cuenta e ingreso sin verificación por correo. |
| US-04 | Como tutor, asigno empresa y fecha de inicio, actualizo grupo por período y doy de baja de Dual sin borrar historia. |
| US-05 | Como alumno, entro al foro y accedo a mis reportes desde la navegación. |
| US-06 | Como alumno, descargo Word/PDF, adjunto PDF firmado por empresa y registro fechas/calificación. |
| US-07 | Como alumno y tutor, identifico semanas pendientes, atrasadas y recibidas sin depender de aprobaciones anteriores. |
| US-08 | Como tutor, comparo PDF y datos, corrijo fechas/nota, apruebo con firma o rechazo con observación. |
| US-09 | Como alumno, reenvío un reporte rechazado y consulto la observación; el sistema conserva versiones. |
| US-10 | Como alumno, consulto y descargo reportes aprobados de todos mis períodos. |
| US-11 | Como tutor/coordinador, consulto expedientes y promedio provisional/final por período. |
| US-12 | Como coordinador, cierro entregas manualmente y después finalizo la evaluación. |
| US-13 | Como coordinador, actualizo la plantilla común Word/PDF. |
| US-14 | Como alumno y personal, conversamos mediante el buzón; el personal publica anuncios. |

## Definición de producto utilizable

Un recorrido completo con PostgreSQL y archivos reales permite incorporar un alumno, registrar su cuenta, entregar dos semanas independientes, rechazar y corregir una, aprobar ambas con firma, consultar el expediente, cerrar recepción, revisar lo recibido y finalizar el promedio. Además pasan controles de acceso, buzón, plantillas y restauración local. Un test de contratos o un build no demuestra por sí solo este recorrido.
