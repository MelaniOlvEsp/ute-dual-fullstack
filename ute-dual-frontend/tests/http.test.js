import test from 'node:test'
import assert from 'node:assert/strict'
import { createHttpClient, ApiError } from '../src/infrastructure/http/httpClient.js'
import { createDualUseCases } from '../src/application/use-cases/dual.js'

test('HTTP client encodes JSON and bearer token', async () => {
  let received
  const http = createHttpClient({
    baseUrl: 'http://localhost:8000', getToken: () => 'token',
    onUnauthorized: () => {},
    fetcher: async (url, options) => {
      received = { url, options }
      return { ok: true, status: 200, json: async () => ({ done: true }) }
    }
  })
  assert.deepEqual(await http.post('/dual/demo', { value: 1 }), { done: true })
  assert.equal(received.options.headers.Authorization, 'Bearer token')
  assert.equal(received.options.body, '{"value":1}')
})

test('HTTP client handles multipart upload without JSON headers', async () => {
  const body = { test: 1 }
  const http = createHttpClient({
    baseUrl: '', getToken: () => null, onUnauthorized: () => {},
    fetcher: async (url, options) => {
      assert.equal(options.body, body)
      assert.equal(options.headers['Content-Type'], undefined)
      return { ok: true, status: 200, json: async () => ({}) }
    }
  })
  await http.post('/dual/alumno/', body, { multipart: true })
})

test('repeated 401 errors invalidate session only once', async () => {
  let calls = 0
  const http = createHttpClient({
    baseUrl: '', getToken: () => 'expired', onUnauthorized: () => { calls++ },
    fetcher: async () => ({ status: 401, ok: false })
  })
  await assert.rejects(http.get('/foro/publicaciones'), ApiError)
  await assert.rejects(http.get('/dual/alumno/semana-actual'), ApiError)
  assert.equal(calls, 1)
})

test('file export is delegated to a file adapter', async () => {
  const calls = []
  const api = createDualUseCases({
    exportarCSV: async () => new Blob(['csv'])
  }, { save: (blob, name) => calls.push(name) })
  await api.exportarCSV('22000000', 'Mayo-Agosto 2026')
  assert.deepEqual(calls, ['expediente_22000000.csv'])
})

test('validation errors are shown without the technical "Value error," prefix', async () => {
  const http = createHttpClient({
    baseUrl: '', getToken: () => 'token', onUnauthorized: () => {},
    fetcher: async () => ({
      status: 422, ok: false,
      json: async () => ({ detail: [{ msg: 'Value error, El período terminó.' }, { msg: 'Campo requerido' }] })
    })
  })
  await assert.rejects(
    http.post('/dual/tutor/abrir-cuatrimestre', {}),
    error => error.message === 'El período terminó., Campo requerido'
  )
})

test('public registration errors do not invalidate a previous session', async () => {
  let redirected = false
  const http = createHttpClient({
    baseUrl: '', getToken: () => 'old-token',
    onUnauthorized: () => { redirected = true },
    fetcher: async () => ({
      status: 401, ok: false, json: async () => ({ detail: 'Código inválido' })
    })
  })
  await assert.rejects(http.post('/auth/register', { codigo: '000000' }), /Código/)
  assert.equal(redirected, false)
})
