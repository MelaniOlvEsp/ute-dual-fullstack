// Convierte datos de aplicación a multipart/form-data.
export function createReportForm(report) {
  const form = new FormData()
  form.append('semana', String(report.week))
  form.append('calificacion_alumno', String(report.grade))
  form.append('fecha_inicio', report.startDate)
  form.append('fecha_fin', report.endDate)
  form.append('archivo', report.file)
  return form
}
