import test from 'node:test'
import assert from 'node:assert/strict'
import { readdirSync, readFileSync, existsSync } from 'node:fs'
import { dirname, extname, join, resolve } from 'node:path'

const src = resolve('src')

function* files(folder) {
  for (const entry of readdirSync(folder, { withFileTypes: true })) {
    const path = join(folder, entry.name)
    if (entry.isDirectory()) yield* files(path)
    else yield path
  }
}

test('all local imports refer to existing files', () => {
  for (const file of files(src)) {
    if (!['.js', '.svelte'].includes(extname(file))) continue
    const content = readFileSync(file, 'utf8')
    for (const match of content.matchAll(/\bfrom\s+['"](\.[^'"]+)['"]/g)) {
      const dep = resolve(dirname(file), match[1])
      assert.ok(existsSync(dep), `${file}: ${match[1]}`)
    }
  }
})

test('inner layers never depend on infrastructure or presentation', () => {
  for (const area of ['domain', 'application']) {
    for (const file of files(join(src, area))) {
      const content = readFileSync(file, 'utf8')
      assert.doesNotMatch(content, /\bfrom\s+['"][^'"]*(?:infrastructure|presentation|composition)\//)
    }
  }
})

test('only auth, Dual and forum routes are registered', () => {
  const app = readFileSync(join(src, 'App.svelte'), 'utf8')
  const routes = [...app.matchAll(/<Route\s+path="([^"]+)"/g)]
    .map(match => match[1]).sort()
  assert.deepEqual(routes, [
    '/', '/cambiar-password', '/dual/accesos',
    '/dual/carrera', '/dual/expediente', '/dual/periodos', '/dual/plantillas', '/dual/reportes', '/dual/tutor', '/dual/tutores', '/foro',
    '/login', '/register'
  ])
})

test('repository modules cover only required features', () => {
  const repositories = readdirSync(join(src, 'infrastructure/repositories'))
    .filter(name => name.endsWith('.js')).sort()
  assert.deepEqual(repositories, [
    'authRepository.js', 'dualRepository.js', 'forumRepository.js'
  ])
})

test('student mailbox always targets Dual', () => {
  const forum = readFileSync(join(src, 'presentation/pages/foro/Foro.svelte'), 'utf8')
  assert.match(forum, /area: MAILBOX_AREA/)
  assert.doesNotMatch(forum, /bind:value=\{buzonArea\}/)
})


test('verification flow and obsolete roles are not exposed', () => {
  const app = readFileSync(join(src, 'App.svelte'), 'utf8')
  const permissions = readFileSync(join(src, 'domain/auth/permissions.js'), 'utf8')
  assert.doesNotMatch(app, /verificar|coordinador_carrera/)
  assert.doesNotMatch(permissions, /\badmin\b|coordinador_carrera/)
})
