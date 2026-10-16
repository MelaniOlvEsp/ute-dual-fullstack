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

export const OBSERVACION_MAX = 1000

// Decisión del tutor (C06): el rechazo exige observación (RN-14) y las correcciones siguen las
// mismas reglas que la entrega. El servidor repite estas comprobaciones.
export function validateReview(review) {
  if (!['Aprobada', 'Rechazada'].includes(review.decision)) {
    throw new Error('Selecciona aprobar o rechazar.')
  }
  const observacion = String(review.observacion ?? '').trim()
  if (review.decision === 'Rechazada' && !observacion) {
    throw new Error('Escribe la observación del rechazo para que el alumno sepa qué corregir.')
  }
  if (observacion.length > OBSERVACION_MAX) {
    throw new Error(`La observación no puede pasar de ${OBSERVACION_MAX} caracteres.`)
  }
  if (String(review.nota ?? '').trim() !== '') validateGrade(review.nota)
  if (review.fechaInicio && review.fechaFin && review.fechaInicio > review.fechaFin) {
    throw new Error('La fecha de inicio debe ser anterior o igual a la de fin.')
  }
}

// Cuerpo de la solicitud: solo los datos presentes; el servidor calcula qué se corrigió.
export function reviewBody(review) {
  const body = { decision: review.decision }
  const observacion = String(review.observacion ?? '').trim()
  if (observacion) body.observacion = observacion
  if (String(review.nota ?? '').trim() !== '') body.calificacion = validateGrade(review.nota)
  if (review.fechaInicio) body.fecha_inicio = review.fechaInicio
  if (review.fechaFin) body.fecha_fin = review.fechaFin
  return body
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
