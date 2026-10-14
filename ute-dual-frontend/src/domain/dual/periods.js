// Catalogo unico de periodos de cuatrimestre.
// Siempre son los mismos 3 rangos de meses; lo unico que cambia es el año.
// Se usa en cualquier parte que pida seleccionar un periodo de cuatrimestre
// (apertura/cierre de cuatrimestre dual, etc.)

export const PERIODOS_CUATRIMESTRE = [
  { clave: 'ENE-ABR', mesInicio: 'Enero', mesFin: 'Abril', numInicio: 1, numFin: 4 },
  { clave: 'MAY-AGO', mesInicio: 'Mayo', mesFin: 'Agosto', numInicio: 5, numFin: 8 },
  { clave: 'SEP-DIC', mesInicio: 'Septiembre', mesFin: 'Diciembre', numInicio: 9, numFin: 12 }
]

export const ANIOS_DISPONIBLES = Array.from({ length: 5 }, (_, i) => new Date().getFullYear() + i)

// Etiqueta legible para el <select>, ej. "Enero - Abril"
export function etiquetaPeriodo(clave) {
  const p = PERIODOS_CUATRIMESTRE.find(x => x.clave === clave)
  return p ? `${p.mesInicio} - ${p.mesFin}` : ''
}

// Arma el string de periodo
// construirPeriodo('MAY-AGO', 2026) -> "Mayo-Agosto 2026"
export function construirPeriodo(clave, anio) {
  const p = PERIODOS_CUATRIMESTRE.find(x => x.clave === clave)
  if (!p || !anio) return ''
  return `${p.mesInicio}-${p.mesFin} ${anio}`
}

// Calcula fecha de inicio y fin (YYYY-MM-DD) deterministas para un periodo,
// ej. fechasPeriodo('SEP-DIC', 2026) -> { inicio: '2026-09-01', fin: '2026-12-31' }
export function fechasPeriodo(clave, anio) {
  const p = PERIODOS_CUATRIMESTRE.find(x => x.clave === clave)
  if (!p || !anio) return { inicio: '', fin: '' }
  const inicio = `${anio}-${String(p.numInicio).padStart(2, '0')}-01`
  const ultimoDia = new Date(anio, p.numFin, 0).getDate()
  const fin = `${anio}-${String(p.numFin).padStart(2, '0')}-${String(ultimoDia).padStart(2, '0')}`
  return { inicio, fin }
}

// Formatea un string YYYY-MM-DD a "D mmm AAAA" sin pasar por Date/UTC,
// para evitar que el timezone del navegador corra la fecha un día
const _MESES_CORTO = ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sep', 'oct', 'nov', 'dic']
export function formatearFechaCorta(fechaISO) {
  if (!fechaISO) return ''
  const [anio, mes, dia] = fechaISO.split('-').map(Number)
  return `${dia} ${_MESES_CORTO[mes - 1]} ${anio}`
}

// Devuelve los periodos que aun no han vencido para el año dado.
// - Año futuro: se devuelven los 3 periodos completos.
// - Año actual: se excluyen los periodos cuyo mes de fin ya pasó.
// - Año pasado: no hay periodos vigentes.
export function periodosVigentes(anio) {
  const anioActual = new Date().getFullYear()
  const mesActual = new Date().getMonth() + 1 // 1-12

  if (!anio || anio < anioActual) return []
  if (anio > anioActual) return PERIODOS_CUATRIMESTRE

  return PERIODOS_CUATRIMESTRE.filter(p => p.numFin >= mesActual)
}