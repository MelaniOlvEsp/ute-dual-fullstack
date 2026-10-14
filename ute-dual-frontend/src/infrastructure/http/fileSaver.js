// Gestiona las descargas sin introducir acceso al DOM en los casos de uso.
export function createFileSaver() {
  return {
    save(blob, filename) {
      const url = URL.createObjectURL(blob)
      const anchor = document.createElement('a')
      anchor.href = url
      anchor.download = filename
      document.body.appendChild(anchor)
      try { anchor.click() } finally {
        anchor.remove()
        URL.revokeObjectURL(url)
      }
    }
  }
}
