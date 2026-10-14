# Decisiones pendientes y supuestos

No requieren resolver todo ahora. Cada decisión bloquea únicamente el incremento indicado. No cambiar reglas confirmadas por conveniencia de implementación.

| ID | Decisión | Propuesta / evidencia | Antes de |
|---|---|---|---|
| DP-01 | Fecha que determina período cuando alumno entrega viernes y semana termina domingo en otro período | Usuario confirmó fecha de fin. Falta precisar si es fin escrito en PDF o domingo de obligación. Ejemplo 30/04/2027–02/05/2027. Mantener semana estable y fechas del PDF separadas; elegir atribución explícita. | C04 |
| DP-02 | Corrección del tutor cambia período o semana | Proponer impedir movimiento hacia período cerrado/finalizado; si ambos abiertos, operación explícita con validación de duplicado e historia. No permitir PATCH que mueva silenciosamente. | C06 |
| DP-03 | Baja dentro de semana, semanas futuras de período cerrado anticipadamente | Proponer última semana parcial hasta baja; distinguir no recibido al cierre de obligación no habilitada por corte, sin recalificar al alumno. Confirmar inclusividad de fecha de baja. | C04 |
| DP-04 | Apertura de períodos, zona y recepción simultánea | Cierre manual está confirmado. Apertura automática no quedó confirmada. Proponer apertura manual por coordinador, zona America/Mexico_City; permitir revisar anteriores. Resolver si pueden recibir dos períodos a la vez. | C04/C07 |
| DP-05 | Nombres oficiales y nomenclatura de grupos; promoción | Confirmadas TIC, Logística, Mercadotecnia. SQL tiene Educación. Faltan códigos oficiales, campos necesarios y regla de promoción masiva. Mantener historial por período. | C03 |
| DP-06 | Nota en reportes de período vacacional sin actividad | Hay obligación de reportar y nota entera 1–10; falta saber cómo califica la empresa. No asignar 10, 0 o exclusión automática. | C05 |
| DP-07 | Ubicación visual de firma del tutor | Crear muestras con plantilla real: espacio existente vs hoja adicional. Usuario debe revisar legibilidad y formato antes de fijar posición. | C06 |
| DP-08 | Tamaños y almacenamiento | Cliente actual 2 MB, API 10 MB. Proponer PDF 10 MB en ambos, firma 1 MB y almacenamiento privado local para piloto; Drive opcional por adaptador. No afirmar disponibilidad gratuita de hosting. | C05/C06 |
| DP-09 | Moderación y cierre del buzón | Confirmada conversación alumno/personal. Proponer solo personal cierra, cerrado queda consulta; decidir reapertura y moderación de anuncios antes de ampliar comportamiento. | C09 |
| DP-10 | Reapertura de recepción o rectificación final | No solicitadas. Proponer fuera de V1; una necesidad institucional cambia spec y política de auditoría. | Solo si se solicita |
| DP-11 | Promedio y conservación operativa | Dos decimales y aprobados únicamente confirmados. Proponer HALF_UP y snapshot al finalizar. Retención/borrado y responsable de respaldos deben definirse antes de uso real. | C07/C10 |

## Decisiones ya confirmadas

Solo Dual, tres roles, tutores transversales, login sin verificación por correo, grupo y matrícula autorizada, expediente histórico, semanas independientes, reenvío con historia, nota entera, promedio de aprobados, cierre manual del coordinador y revisión posterior al cierre. Base inicial vacía. No hay datos productivos por migrar.

## Diseño técnico propuesto

Base nueva con identificadores de período y obligaciones semanales, versiones de reporte y documentos privados; separar incorporación laboral de pertenencia académica. Se valida en las specs, no constituye código entregado.

## Registro de resolución

Al cerrar una DP registrar: fecha, decisión textual del responsable, motivo, RN/AC afectados y spec. No borrar el contexto de la decisión. Las restricciones de acceso y conservación aplican mientras no exista excepción autorizada.
