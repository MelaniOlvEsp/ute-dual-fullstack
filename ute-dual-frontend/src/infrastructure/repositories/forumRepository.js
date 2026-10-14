// Conserva las rutas públicas del foro y del buzón de Dual.
export function createForumRepository(http) {
  return {
    posts: {
      listar: () => http.get('/foro/publicaciones'),
      crear: contenido => http.post('/foro/publicaciones', { contenido }),
      eliminar: id => http.delete(`/foro/publicaciones/${encodeURIComponent(id)}`),
      reaccionar: (id, tipo) => http.post(
        `/foro/publicaciones/${encodeURIComponent(id)}/reaccion`, { tipo }
      )
    },
    mailbox: {
      enviar: body => http.post('/foro/buzon/', body),
      listar: area => http.get(`/foro/buzon/?area=${encodeURIComponent(area)}`),
      mios: () => http.get('/foro/buzon/mios'),
      detalle: id => http.get(`/foro/buzon/${encodeURIComponent(id)}`),
      responder: (id, texto) => http.post(
        `/foro/buzon/${encodeURIComponent(id)}/respuestas`, { texto }
      ),
      marcarLeido: id => http.patch(`/foro/buzon/${encodeURIComponent(id)}/leido`),
      cerrar: id => http.patch(`/foro/buzon/${encodeURIComponent(id)}/cerrar`)
    }
  }
}
