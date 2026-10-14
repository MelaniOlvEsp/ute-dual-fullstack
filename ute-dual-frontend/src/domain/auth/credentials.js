// Coincide con la política de contraseña del backend.
export function validateRegistration(email, password) {
  if (!email?.trim().toLowerCase().endsWith('@ute.edu.mx')) {
    throw new Error('Debes usar tu correo institucional (@ute.edu.mx)')
  }
  if (password.length < 12 || password.length > 128 ||
      !/[a-z]/.test(password) || !/[A-Z]/.test(password) ||
      !/[0-9]/.test(password)) {
    throw new Error('La contraseña requiere 12 caracteres, mayúscula, minúscula y número.')
  }
}
