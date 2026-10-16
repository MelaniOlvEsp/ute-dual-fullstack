// Textos de estado y de confirmación del cierre de recepción y la finalización (C07).
// La recepción y la evaluación son independientes de las fechas calendario (RN-23).

const RECEPCION = { sin_abrir: 'Sin abrir', abierta: 'Recepción abierta', cerrada: 'Recepción cerrada' }
const EVALUACION = { en_curso: 'Evaluación en curso', finalizada: 'Evaluación finalizada' }

export function etiquetaRecepcion(estado) {
  return RECEPCION[estado] || 'Sin abrir'
}

export function etiquetaEvaluacion(estado) {
  return EVALUACION[estado] || 'Evaluación en curso'
}

const plural = (n, uno, varios) => `${n} ${n === 1 ? uno : varios}`

// Consecuencia que el coordinador debe leer antes de cerrar la recepción (RN-19).
export function mensajeCierre(periodo, conteos) {
  const label = periodo.periodo_label
  const porRevisar = conteos?.pendientes_revision ?? 0
  const rechazados = conteos?.rechazadas ?? 0
  const partes = [
    `Vas a cerrar la recepción de ${label}. Los alumnos ya no podrán entregar ni reenviar reportes de este período.`,
    'El tutor seguirá revisando lo ya recibido.'
  ]
  if (rechazados) {
    partes.push(`${plural(rechazados, 'reporte rechazado no podrá', 'reportes rechazados no podrán')} reenviarse.`)
  }
  if (porRevisar) partes.push(`Hay ${plural(porRevisar, 'reporte pendiente', 'reportes pendientes')} de revisión.`)
  partes.push('No se puede deshacer.')
  return partes.join(' ')
}

// Consecuencia de finalizar: convierte los promedios provisionales en finales (RN-22).
export function mensajeFinalizacion(periodo, alumnos) {
  const label = periodo.periodo_label
  return `Vas a finalizar la evaluación de ${label}. Los promedios de ${plural(alumnos?.length ?? 0, 'alumno', 'alumnos')} pasarán de provisionales a finales y ya no cambiarán. No se puede deshacer.`
}

export function motivoPeriodo(periodo) {
  if (!periodo) return ''
  if (periodo.cierre_efectivo) return `Cierre efectivo: ${periodo.cierre_efectivo}`
  return ''
}
