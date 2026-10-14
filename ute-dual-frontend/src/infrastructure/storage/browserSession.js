const TOKEN_KEY = 'ute_token'
const USER_KEY = 'ute_user'

// Aísla sessionStorage para mantener el estado fuera del dominio.
export const browserSession = {
  readToken() {
    try { return sessionStorage.getItem(TOKEN_KEY) } catch { return null }
  },
  readUser() {
    try {
      const raw = sessionStorage.getItem(USER_KEY)
      return raw ? JSON.parse(raw) : null
    } catch { return null }
  },
  writeToken(value) {
    try {
      if (value) sessionStorage.setItem(TOKEN_KEY, value)
      else sessionStorage.removeItem(TOKEN_KEY)
    } catch { /* Navegadores con almacenamiento bloqueado. */ }
  },
  writeUser(value) {
    try {
      if (value) sessionStorage.setItem(USER_KEY, JSON.stringify(value))
      else sessionStorage.removeItem(USER_KEY)
    } catch { /* Navegadores con almacenamiento bloqueado. */ }
  }
}
