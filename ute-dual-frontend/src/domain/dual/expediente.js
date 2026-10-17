// Textos y reglas de presentación del expediente (C08). El servidor decide qué se puede descargar;
// aquí solo se formatea lo que devuelve.

export function etiquetaPromedio(resumen) {
  if (!resumen || resumen.promedio === null || resumen.promedio === undefined) return 'Sin calificación'
  return resumen.promedio
}

// El promedio es final solo después de finalizar la evaluación (RN-22): hasta entonces se rotula como provisional.
export function tipoPromedio(resumen) {
  return resumen?.definitivo ? 'final' : 'provisional'
}

export function situacionAlumno(alumno) {
  if (!alumno) return ''
  return alumno.activo ? 'Incorporación activa' : 'Dado de baja (el expediente se conserva)'
}

// Mensaje de la ventana del alumno (una semana desde la finalización, DP-14).
export function mensajeVentana(paquete, formato = fecha => fecha) {
  if (!paquete) return ''
  if (paquete.disponible) {
    return paquete.hasta
      ? `Tu paquete estará disponible hasta el ${formato(paquete.hasta)}. Después ya no podrás descargarlo.`
      : 'Tu paquete está disponible.'
  }
  return paquete.motivo || 'El paquete no está disponible.'
}

export function tieneCorreccion(aprobado) {
  return Boolean(aprobado?.corregida)
}

export const SITUACIONES = [
  { valor: 'todos', etiqueta: 'Todos' },
  { valor: 'activos', etiqueta: 'Activos' },
  { valor: 'baja', etiqueta: 'Dados de baja' }
]

// Paginación por servidor: rango visible y si hay página anterior o siguiente.
export function paginacion({ total = 0, limite = 50, desplazamiento = 0 } = {}) {
  const desde = total === 0 ? 0 : desplazamiento + 1
  const hasta = Math.min(desplazamiento + limite, total)
  return {
    desde, hasta, total,
    hayAnterior: desplazamiento > 0,
    haySiguiente: desplazamiento + limite < total
  }
}
