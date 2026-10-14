const MAX_PDF_BYTES = 2 * 1024 * 1024

// Valida archivos antes de enviarlos al backend.
export function validateReportFile(file) {
  if (!file) throw new Error('Adjunta el PDF del reporte.')
  if (!file.name?.toLowerCase().endsWith('.pdf')) {
    throw new Error('Solo se aceptan archivos PDF.')
  }
  if (file.size > MAX_PDF_BYTES) {
    throw new Error('El PDF es muy pesado. Comprímelo a un máximo de 2 MB.')
  }
}

// Revisa datos obligatorios y rangos del reporte semanal.
export function validateWeeklyReport(report) {
  const week = Number(report.week)
  const grade = Number(report.grade)
  if (!Number.isInteger(week) || week < 1 || week > 18) {
    throw new Error('La semana debe estar entre 1 y 18.')
  }
  if (!report.grade || !Number.isFinite(grade) || grade < 1 || grade > 10) {
    throw new Error('La calificación debe estar entre 1 y 10.')
  }
  if (!/^\d{4}-\d{2}-\d{2}$/.test(report.startDate || '') ||
      !/^\d{4}-\d{2}-\d{2}$/.test(report.endDate || '')) {
    throw new Error('Selecciona ambas fechas del reporte.')
  }
  if (report.startDate > report.endDate) {
    throw new Error('La fecha de inicio debe ser anterior al fin.')
  }
  validateReportFile(report.file)
}
