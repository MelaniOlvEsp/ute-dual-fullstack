// Formatea fechas para las vistas de Formación Dual.
export function formatFecha(iso) {
  const options = {
    day: 'numeric',
    month: 'short',
    year: 'numeric'
  }
  return new Date(iso).toLocaleDateString('es-MX', options)
}

// Devuelve la clase visual que corresponde al estado de un reporte.
export function estadoBadgeClass(status) {
  const classes = {
    pendiente: 'badge-pendiente',
    en_revision: 'badge-en_revision',
    aprobada: 'badge-aprobada',
    rechazada: 'badge-rechazada'
  }
  return `badge ${classes[status?.toLowerCase()] || ''}`
}
