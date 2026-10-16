// Mismo límite que la API (DP-08, C05): 10 MB.
export const MAX_PDF_BYTES = 10 * 1024 * 1024

// Valida archivos antes de enviarlos al backend. La API repite y completa estas comprobaciones.
export function validateReportFile(file) {
  if (!file) throw new Error('Adjunta el PDF del reporte.')
  if (!file.name?.toLowerCase().endsWith('.pdf')) {
    throw new Error('Solo se aceptan archivos PDF.')
  }
  if (!file.size) {
    throw new Error('El archivo está vacío.')
  }
  if (file.size > MAX_PDF_BYTES) {
    throw new Error('El PDF es muy pesado. El máximo es 10 MB.')
  }
}

// La calificación es un entero de 1 a 10 (RN-12): sin decimales, como en la API.
export function validateGrade(grade) {
  if (!/^\d{1,2}$/.test(String(grade ?? '').trim())) {
    throw new Error('La calificación debe ser un número entero entre 1 y 10.')
  }
  const value = Number(String(grade).trim())
  if (value < 1 || value > 10) {
    throw new Error('La calificación debe ser un número entero entre 1 y 10.')
  }
  return value
}

// Revisa datos obligatorios y rangos del reporte semanal. La semana la fija la obligación y
// solo se exige inicio ≤ fin (DP-12); el tutor verifica que correspondan a la semana.
export function validateWeeklyReport(report) {
  validateGrade(report.grade)
  if (!/^\d{4}-\d{2}-\d{2}$/.test(report.startDate || '') ||
      !/^\d{4}-\d{2}-\d{2}$/.test(report.endDate || '')) {
    throw new Error('Selecciona ambas fechas del reporte.')
  }
  if (report.startDate > report.endDate) {
    throw new Error('La fecha de inicio debe ser anterior o igual a la de fin.')
  }
  validateReportFile(report.file)
}
