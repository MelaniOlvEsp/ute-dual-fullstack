// Convierte los datos de una entrega a multipart/form-data. La semana la fija la obligación
// de la ruta; el cliente no envía ni número de semana ni período.
export function createReportForm(report) {
  const form = new FormData()
  form.append('calificacion_alumno', String(report.grade).trim())
  form.append('fecha_inicio', report.startDate)
  form.append('fecha_fin', report.endDate)
  form.append('archivo', report.file)
  return form
}
