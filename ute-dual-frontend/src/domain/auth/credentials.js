// Política compartida por registro y cambio de contraseña.
export function validatePassword(password) {
  if ([...password].length < 12 || [...password].length > 128 ||
      !/\p{Ll}/u.test(password) || !/\p{Lu}/u.test(password) || !/\p{Nd}/u.test(password)) {
    throw new Error('La contraseña requiere al menos 12 caracteres, mayúscula, minúscula y número.')
  }
  if (new TextEncoder().encode(password).length > 72) {
    throw new Error('La contraseña admite como máximo 72 bytes UTF-8.')
  }
}
export function validateRegistration(email, password) {
  if (!email?.trim().toLowerCase().endsWith('@ute.edu.mx')) {
    throw new Error('Debes usar tu correo institucional (@ute.edu.mx)')
  }
  validatePassword(password)
}
