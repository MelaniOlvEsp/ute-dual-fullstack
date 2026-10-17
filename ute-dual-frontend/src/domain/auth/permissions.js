export const STAFF_ROLES = Object.freeze(['tutor_academico', 'coordinador_dual'])

// Dirige al usuario según sus permisos activos.
export function homeFor(user) {
  if (!user) return '/login'
  if (user.must_change_password) return '/cambiar-password'
  const roles = user.roles || {}
  // C09 (RN-27, AC-22): el foro es la pantalla inicial de todos los roles; el cambio obligatorio va antes.
  if (roles.tutor_academico || roles.coordinador_dual || roles.alumno) return '/foro'
  return '/login'
}

// La API valida todos los permisos nuevamente.
export function hasAccess(user, permission) {
  if (!user) return false
  if (user.must_change_password) return permission === 'change-password'
  const roles = user.roles || {}
  if (permission === 'authenticated') return STAFF_ROLES.some(key => roles[key]) || Boolean(roles.alumno)
  if (permission === 'tutor') return Boolean(roles.tutor_academico)
  if (permission === 'coordinator') return Boolean(roles.coordinador_dual)
  if (permission === 'files') return Boolean(roles.tutor_academico || roles.coordinador_dual)
  if (permission === 'dual-student') return Boolean(roles.alumno)
  return false
}
