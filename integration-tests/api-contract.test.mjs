import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, resolve } from 'node:path'
import { createHttpClient } from '../ute-dual-frontend/src/infrastructure/http/httpClient.js'
import { createAuthRepository } from '../ute-dual-frontend/src/infrastructure/repositories/authRepository.js'
import { createDualRepository } from '../ute-dual-frontend/src/infrastructure/repositories/dualRepository.js'
import { createForumRepository } from '../ute-dual-frontend/src/infrastructure/repositories/forumRepository.js'

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const contract = JSON.parse(readFileSync(resolve(root, 'ute-api-backend/tests/route_contract.json'), 'utf8'))
const prefixes = {
  auth: '/auth',
  'dual/alumno_dual': '/dual/alumno',
  'dual/coordinador_dual': '/dual/tutor',
  'dual/coordinador_carrera': '/dual/carrera',
  'dual/plantillas': '/dual/plantillas',
  'foro/publicaciones': '/foro',
  'foro/buzon': '/foro/buzon'
}
const serverRoutes = Object.entries(contract).flatMap(([module, routes]) =>
  routes.map(({ method, path }) => {
    const full = prefixes[module] + path
    const escaped = full.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
    const matcher = new RegExp('^' + escaped.replace(/\\\{[^}]+\\\}/g, '[^/]+') + '/?$')
    return { method, full, matcher }
  })
)
const calls = []
const server = {
  async fetch(url, options) {
    const pathname = new URL(url).pathname
    const matching = serverRoutes.filter(r => r.method === options.method && r.matcher.test(pathname))
    assert.ok(matching.length > 0, `Missing FastAPI route: ${options.method} ${pathname}`)
    assert.equal(options.headers.Authorization, 'Bearer token-for-tests')
    calls.push(`${options.method} ${pathname}`)
    const binary = pathname.endsWith('/pdf') || /\/paquetes?(\/|$)/.test(pathname)
    return new Response(binary ? 'test-bytes' : '{}', { status: 200 })
  }
}
const baseUrl = 'http://127.0.0.1:8000'
const http = createHttpClient({
  baseUrl,
  fetcher: (url, opts) => server.fetch(url, opts),
  getToken: () => 'token-for-tests',
  onUnauthorized: () => { throw new Error('Unexpected 401') }
})
const auth = createAuthRepository(http)
const dual = createDualRepository(http, baseUrl)
const forum = createForumRepository(http)

function sampleArgs(name) {
  const args = {
    eliminarTutor: ['00000000-0000-0000-0000-000000000001'],
    passwordProvisional: ['123456789'],
    crearTutor: [{nombre: 'Tutor',email:'tutor@ute.edu.mx'}],
    subirFirma: [new FormData()],
    studentProfile: [],
    entregarObligacion: ['00000000-0000-0000-0000-000000000001', new FormData()],
    versionesReporte: ['00000000-0000-0000-0000-000000000001'],
    descargarVersion: ['00000000-0000-0000-0000-000000000001', 2],
    miPaquete: ['00000000-0000-0000-0000-000000000002'],
    listarReportes: ['estado=Pendiente'],
    detalleReporte: ['00000000-0000-0000-0000-000000000001'],
    revisarVersion: ['00000000-0000-0000-0000-000000000001', 2, { decision: 'Aprobada' }],
    crearEmpresa: [{ nombre: 'Empresa' }],
    asignarEmpresa: [{ matricula: '123456789' }],
    buscarAlumno: ['123456789'],
    historialIncorporaciones: ['123456789'],
    actualizarAlumnoDual: ['123456789', { alumno_dual: false }],
    resumenPeriodo: ['00000000-0000-0000-0000-000000000001'],
    cerrarRecepcion: ['00000000-0000-0000-0000-000000000001'],
    finalizarEvaluacion: ['00000000-0000-0000-0000-000000000001'],
    abrirCuatrimestre: [{ periodo_label: '2026-3' }],
    alumnosSinReporte: ['2026-3', 2],
    listarAlumnos: ['grupo=abc'],
    expedienteAlumno: ['123456789'],
    descargarAprobado: ['00000000-0000-0000-0000-000000000001', 1, 'original'],
    paqueteAlumno: ['123456789', '00000000-0000-0000-0000-000000000002'],
    paqueteCarrera: ['ITI', '00000000-0000-0000-0000-000000000002'],
    plantillaVigente: [],
    plantillas: [],
    publicarPlantilla: [new FormData()],
    descargarPlantilla: [3, 'word'],
    reabrir: ['00000000-0000-0000-0000-000000000001'],
    archivoPeriodo: ['00000000-0000-0000-0000-000000000002'],
    programarPurga: ['00000000-0000-0000-0000-000000000002', { carrera: 'TII', confirmar: true, frase: 'x' }],
    cancelarPurga: ['00000000-0000-0000-0000-000000000002', '00000000-0000-0000-0000-000000000003'],
    ejecutarPurga: ['00000000-0000-0000-0000-000000000002', '00000000-0000-0000-0000-000000000003'],
    crearGrupo: [{ carrera: 'TI', cuatrimestre: 3 }],
    previewAlumnosCSV: ['00000000-0000-0000-0000-000000000001', new FormData()],
    subirAlumnosCSV: ['00000000-0000-0000-0000-000000000001', new FormData()],
    agregarAlumno: ['00000000-0000-0000-0000-000000000001', { matricula: '123456789', nombre: 'Alumno' }],
    actualizarAlumno: ['123456789', { nombre: 'Alumno' }],
    eliminarAlumno: ['123456789'],
    listarGrupos: ['TI'],
    historialGrupos: ['123456789'],
    previewPromocion: [{}],
    aplicarPromocion: [{}],
    reaccionar: ['00000000-0000-0000-0000-000000000001', 'like'],
    eliminar: ['00000000-0000-0000-0000-000000000001'],
    enviar: [{ area: 'dual', asunto: 'Prueba', mensaje: 'Prueba' }],
    listar: ['dual'],
    detalle: ['00000000-0000-0000-0000-000000000001'],
    responder: ['00000000-0000-0000-0000-000000000001', 'Respuesta'],
    marcarLeido: ['00000000-0000-0000-0000-000000000001'],
    cerrar: ['00000000-0000-0000-0000-000000000001']
  }
  return args[name] || [{}]
}

test('all frontend HTTP repository operations match backend route contracts', async () => {
  for (const repository of Object.values({auth, dual, posts: forum.posts, mailbox: forum.mailbox})) {
    for (const [name, operation] of Object.entries(repository)) {
      if (name.includes('PdfUrl')) {
        const url = operation('00000000-0000-0000-0000-000000000001')
        await http.get(url.slice(baseUrl.length), { blob: true })
        continue
      }
      await operation(...sampleArgs(name))
    }
  }
  assert.ok(calls.length >= 44, `Too few operations checked: ${calls.length}`)
  console.log(`Validated ${calls.length} frontend API calls against ${serverRoutes.length} backend routes`)
  assert.ok(calls.includes('GET /auth/me'))
  assert.ok(calls.includes('GET /dual/alumno/expediente'))
  assert.ok(calls.includes('POST /foro/buzon/'))
  assert.ok(calls.includes('GET /dual/carrera/paquetes/alumno/123456789'))
  assert.ok(calls.includes('GET /dual/carrera/paquetes/carrera/ITI'))
  assert.ok(!calls.some(call => /mis-reportes|exportar-(csv|zip)|\/dual\/(alumno|carrera|tutor)\/reporte\//.test(call)))
  assert.ok(!calls.some(call => call.includes('/alumnos/me')))
})
