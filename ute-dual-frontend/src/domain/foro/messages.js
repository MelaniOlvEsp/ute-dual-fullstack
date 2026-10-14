export const MAILBOX_AREA = 'dual'
export const REACTIONS = Object.freeze([
  { tipo: 'like', emoji: '👍', label: 'Me gusta' },
  { tipo: 'love', emoji: '❤️', label: 'Me encanta' },
  { tipo: 'haha', emoji: '😆', label: 'Me divierte' },
  { tipo: 'wow', emoji: '😮', label: 'Me asombra' },
  { tipo: 'sad', emoji: '😢', label: 'Me entristece' },
  { tipo: 'angry', emoji: '😡', label: 'Me enoja' }
])

// Acepta únicamente mensajes dirigidos al área activa.
export function prepareMessage(data) {
  const area = data.area
  const asunto = (data.asunto || '').trim()
  const mensaje = (data.mensaje || '').trim()
  if (area !== MAILBOX_AREA) throw new Error('Área de buzón no válida.')
  if (asunto.length < 3 || asunto.length > 150) {
    throw new Error('El asunto debe tener entre 3 y 150 caracteres.')
  }
  if (!mensaje || mensaje.length > 500) {
    throw new Error('El mensaje debe tener entre 1 y 500 caracteres.')
  }
  return { area, asunto, mensaje }
}
