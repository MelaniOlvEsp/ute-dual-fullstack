const PUBLIC_AUTH_PATHS = new Set([
  '/auth/login', '/auth/register'
])

export class ApiError extends Error {
  constructor(message, status) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

// Adapta fetch al transporte requerido por los repositorios.
export function createHttpClient({ baseUrl, fetcher, getToken, onUnauthorized }) {
  let expired = false

  async function request(method, path, body = null, options = {}) {
    const { multipart = false, blob = false } = options
    const headers = {}
    const jwt = getToken()
    if (jwt) headers.Authorization = `Bearer ${jwt}`
    if (!multipart && body !== null) headers['Content-Type'] = 'application/json'
    const payload = multipart || body === null ? body : JSON.stringify(body)

    let response
    try {
      response = await fetcher(`${baseUrl}${path}`, {
        method, headers, body: payload
      })
    } catch {
      throw new ApiError('No se pudo conectar con el servidor.', 0)
    }

    if (response.status === 401 && jwt && !PUBLIC_AUTH_PATHS.has(path)) {
      if (!expired) {
        expired = true
        onUnauthorized()
      }
      throw new ApiError('Sesión expirada. Inicia sesión nuevamente.', 401)
    }

    if (blob && response.ok) return response.blob()
    const data = await response.json().catch(() => ({}))
    if (!response.ok) {
      const detail = data?.detail || (blob ? 'Error al descargar el archivo' : 'Error en el servidor')
      const message = Array.isArray(detail)
        ? detail.map(item => item.msg || String(item)).join(', ')
        : typeof detail === 'string' ? detail : JSON.stringify(detail)
      throw new ApiError(message, response.status)
    }
    return data
  }

  return {
    get: (path, options) => request('GET', path, null, options),
    post: (path, body, options) => request('POST', path, body, options),
    patch: (path, body, options) => request('PATCH', path, body, options),
    delete: path => request('DELETE', path)
  }
}
