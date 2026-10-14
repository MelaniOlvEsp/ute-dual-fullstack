import { prepareMessage, MAILBOX_AREA, REACTIONS } from '../../domain/foro/messages.js'

// Centraliza las reglas de envío y lectura del buzón.
export function createForumUseCases(repo) {
  return {
    foro: {
      ...repo.posts,
      crear: contenido => {
        const text = (contenido || '').trim()
        if (!text || text.length > 2000) {
          throw new Error('La publicación debe tener entre 1 y 2000 caracteres.')
        }
        return repo.posts.crear(text)
      },
      reaccionar: (id, tipo) => {
        if (!REACTIONS.some(item => item.tipo === tipo)) {
          throw new Error('Reacción no válida.')
        }
        return repo.posts.reaccionar(id, tipo)
      }
    },
    buzon: {
      ...repo.mailbox,
      enviar: data => repo.mailbox.enviar(prepareMessage(data)),
      listar: area => {
        if (area !== MAILBOX_AREA) throw new Error('Área de buzón no válida.')
        return repo.mailbox.listar(area)
      },
      responder: (id, texto) => {
        const response = (texto || '').trim()
        if (!response) throw new Error('Escribe tu respuesta.')
        return repo.mailbox.responder(id, response)
      }
    }
  }
}
