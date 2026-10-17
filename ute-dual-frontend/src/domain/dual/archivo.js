// Textos y reglas de presentación de la depuración de archivos (C08B). El servidor decide qué se puede
// depurar; aquí solo se formatea lo que devuelve.

export function formatearBytes(bytes) {
  const n = Number(bytes) || 0
  if (n < 1024) return `${n} B`
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`
  if (n < 1024 * 1024 * 1024) return `${(n / (1024 * 1024)).toFixed(1)} MB`
  return `${(n / (1024 * 1024 * 1024)).toFixed(2)} GB`
}

export const ETIQUETA_ESTADO = {
  sin_depurar: 'Sin depurar',
  programada: 'Depuración programada',
  parcial: 'Depurado en parte',
  depurado: 'Depurado'
}

// Aviso del archivo de un período para el alumno o el personal; las notas nunca dependen de este estado.
export function mensajeArchivo(archivo, formato = fecha => fecha) {
  if (!archivo || archivo.estado === 'normal') return ''
  if (archivo.estado === 'programada') {
    return `Los archivos PDF de este período se eliminarán el ${formato(archivo.eliminacion_en)}. Descarga tu copia antes de esa fecha; tus notas, tu promedio y tu historial se conservan.`
  }
  return `Los archivos PDF de este período se depuraron el ${formato(archivo.archivado_en)}. Tus notas, tu promedio y tu historial se conservan.`
}

// La depuración solo se confirma con el permiso escrito exacto y la confirmación marcada.
export function puedeConfirmar({ frase, esperada, guardada, ocupado }) {
  return Boolean(guardada) && !ocupado && String(frase || '').trim() === esperada
}

export function purgaVencida(purga, ahora = new Date()) {
  return purga?.estado === 'programada' && new Date(purga.ejecutar_en) <= ahora
}