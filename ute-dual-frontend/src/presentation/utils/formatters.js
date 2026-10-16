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

// Fecha civil AAAA-MM-DD sin conversión de zona: new Date('2026-10-14') se lee en UTC y
// mostraría el día anterior en México.
export function formatFechaCivil(iso) {
  if (!iso) return ''
  const [anio, mes, dia] = String(iso).slice(0, 10).split('-').map(Number)
  return new Date(Date.UTC(anio, mes - 1, dia)).toLocaleDateString('es-MX', {
    day: 'numeric', month: 'short', year: 'numeric', timeZone: 'UTC'
  })
}

// Fecha de hoy (AAAA-MM-DD) en la zona operativa America/Mexico_City, no en UTC:
// toISOString() adelanta el día después de las 18:00 hora de México.
export function hoyOperativo() {
  return new Intl.DateTimeFormat('en-CA', {
    timeZone: 'America/Mexico_City', year: 'numeric', month: '2-digit', day: '2-digit'
  }).format(new Date())
}
