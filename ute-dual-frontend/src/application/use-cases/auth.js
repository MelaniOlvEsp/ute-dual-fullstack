import { validateRegistration } from '../../domain/auth/credentials.js'

// Decodifica los datos de navegación; el backend valida el JWT.
export function decodeSession(token) {
  try {
    const payload = token.split('.')[1]
    const padded = payload.replace(/-/g, '+').replace(/_/g, '/')
    const data = JSON.parse(atob(padded))
    return {
      id: data.id, roles: data.roles || {}, matricula: data.matricula,
      email: data.sub, dual_activo: data.dual_activo,
      must_change_password: Boolean(data.must_change_password)
    }
  } catch {
    throw new Error('Error al procesar la sesión. Intenta de nuevo.')
  }
}

// Reúne operaciones HTTP de identidad para las pantallas.
export function createAuthUseCases(repo) {
  return {
    ...repo,
    async loginSession(credentials) {
      const response = await repo.login(credentials)
      if (!response?.access_token) throw new Error('Credenciales incorrectas')
      const userData = decodeSession(response.access_token)
      return {
        accessToken: response.access_token, userData,
        mustChangePassword: Boolean(response.must_change_password || userData.must_change_password)
      }
    },
    async register(data) {
      validateRegistration(data.email, data.password)
      return repo.register(data)
    },
    async crearTutor(data) {
      if (!data.nombre?.trim() || !data.email?.trim()) {
        throw new Error('Nombre y correo son obligatorios.')
      }
      return repo.crearTutor({ nombre: data.nombre.trim(), email: data.email.trim() })
    }
  }
}
