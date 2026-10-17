import test from 'node:test'
import assert from 'node:assert/strict'
import {
  etiquetaPromedio, tipoPromedio, situacionAlumno, mensajeVentana, tieneCorreccion, paginacion
} from '../src/domain/dual/expediente.js'

test('average label never invents a grade', () => {
  assert.equal(etiquetaPromedio({ promedio: null }), 'Sin calificación')
  assert.equal(etiquetaPromedio(null), 'Sin calificación')
  assert.equal(etiquetaPromedio({ promedio: '9.34' }), '9.34')
  assert.equal(etiquetaPromedio({ promedio: 0 }), 0)
})

test('average is provisional until the evaluation is finalized', () => {
  assert.equal(tipoPromedio({ definitivo: true }), 'final')
  assert.equal(tipoPromedio({ definitivo: false }), 'provisional')
  assert.equal(tipoPromedio(undefined), 'provisional')
})

test('situation text distinguishes bajas and keeps the record', () => {
  assert.match(situacionAlumno({ activo: false }), /baja/i)
  assert.match(situacionAlumno({ activo: true }), /activa/i)
  assert.equal(situacionAlumno(null), '')
})

test('student window message shows the deadline or the server reason', () => {
  assert.match(mensajeVentana({ disponible: true, hasta: '2026-10-23' }, f => `<${f}>`), /<2026-10-23>/)
  assert.equal(mensajeVentana({ disponible: false, motivo: 'La ventana terminó.' }), 'La ventana terminó.')
  assert.equal(mensajeVentana(null), '')
})

test('corrected marker only for corrected approvals', () => {
  assert.equal(tieneCorreccion({ corregida: true }), true)
  assert.equal(tieneCorreccion({}), false)
})

test('server pagination range', () => {
  assert.deepEqual(paginacion({ total: 0 }), { desde: 0, hasta: 0, total: 0, hayAnterior: false, haySiguiente: false })
  assert.deepEqual(paginacion({ total: 120, limite: 50, desplazamiento: 50 }),
    { desde: 51, hasta: 100, total: 120, hayAnterior: true, haySiguiente: true })
  assert.equal(paginacion({ total: 120, limite: 50, desplazamiento: 100 }).haySiguiente, false)
})
