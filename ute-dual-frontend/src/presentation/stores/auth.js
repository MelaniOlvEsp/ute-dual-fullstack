import { writable, derived } from 'svelte/store'
import { browserSession } from '../../infrastructure/storage/browserSession.js'
import { hasAccess } from '../../domain/auth/permissions.js'

export const token = writable(browserSession.readToken())
export const user = writable(browserSession.readUser())

// Sincroniza únicamente los datos de sesión que consume la interfaz.
token.subscribe(value => browserSession.writeToken(value))
user.subscribe(value => browserSession.writeUser(value))

export const isAuthenticated = derived(token, value => Boolean(value))
export const isAlumno = derived(user, value => Boolean(value?.roles?.alumno))
export const isTutorAcademico = derived(user, value => hasAccess(value, 'tutor'))
export const isAlumnoDual = derived(user, value => hasAccess(value, 'dual-student'))
export const isCoordinadorDual = derived(user, value => hasAccess(value, 'coordinator'))
export const isCoordinadorCarrera = derived(user, value => hasAccess(value, 'files'))

// Finaliza la sesión tanto en memoria como en sessionStorage.
export function logout() {
  token.set(null)
  user.set(null)
}

// Actualiza la sesión después de validar la respuesta de inicio.
export function login(jwtToken, userData) {
  token.set(jwtToken)
  user.set(userData)
}
