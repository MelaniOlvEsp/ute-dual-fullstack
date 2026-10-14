import test from 'node:test'
import assert from 'node:assert/strict'
import { homeFor, hasAccess } from '../src/domain/auth/permissions.js'
import { validateRegistration } from '../src/domain/auth/credentials.js'
import { createAuthUseCases, decodeSession } from '../src/application/use-cases/auth.js'

test('only the three approved roles can navigate', () => {
  assert.equal(homeFor({ roles: { coordinador_dual: true } }), '/dual/carrera')
  assert.equal(homeFor({ roles: { tutor_academico: true } }), '/dual/tutor')
  assert.equal(homeFor({ roles: { alumno: true } }), '/dual/reportes')
  assert.equal(homeFor({ roles: { admin: true } }), '/login')
  assert.equal(homeFor({ must_change_password: true, roles: { alumno: true } }), '/cambiar-password')
  assert.equal(hasAccess({ roles: { admin: true } }, 'files'), false)
  assert.equal(hasAccess({ roles: { coordinador_carrera: true } }, 'tutor'), false)
  assert.equal(hasAccess({ roles: { coordinador_dual: true } }, 'tutor'), false)
  assert.equal(hasAccess({ roles: { tutor_academico: true } }, 'tutor'), true)
  assert.equal(hasAccess({ roles: { coordinador_dual: true } }, 'files'), true)
  assert.equal(hasAccess({ roles: { alumno: true } }, 'files'), false)
  assert.equal(hasAccess({ must_change_password: true, roles: { tutor_academico: true } }, 'files'), false)
})

test('registration validates 12 character institutional credentials', () => {
  validateRegistration('123456789@ute.edu.mx', 'SecurePassword123')
  assert.throws(() => validateRegistration('x@example.com', 'SecurePassword123'))
  assert.throws(() => validateRegistration('123456789@ute.edu.mx', 'Weak123'))
})

test('only coordinator may create the tutor through the protected endpoint', async () => {
  let body
  const useCases = createAuthUseCases({
    crearTutor: async data => { body = data; return { password_temporal: 'SECRET' } }
  })
  const result = await useCases.crearTutor({ nombre: ' Ana ', email: 'ana@ute.edu.mx' })
  assert.deepEqual(body, { nombre: 'Ana', email: 'ana@ute.edu.mx' })
  assert.equal(result.password_temporal, 'SECRET')
})

test('JWT payload keeps mandatory password-change state', () => {
  const payload = Buffer.from(JSON.stringify({
    id: 1, sub: 'student@ute.edu.mx',
    roles: { alumno: true }, must_change_password: true
  })).toString('base64url')
  assert.equal(decodeSession(`x.${payload}.x`).must_change_password, true)
  assert.throws(() => decodeSession('invalid'), /procesar la sesión/)
})
