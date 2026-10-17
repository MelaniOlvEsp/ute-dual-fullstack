import test from 'node:test'
import assert from 'node:assert/strict'
import { formatearBytes, mensajeArchivo, puedeConfirmar, purgaVencida, ETIQUETA_ESTADO } from '../src/domain/dual/archivo.js'

test('bytes are shown in readable units', () => {
  assert.equal(formatearBytes(0), '0 B')
  assert.equal(formatearBytes(1536), '1.5 KB')
  assert.equal(formatearBytes(5 * 1024 * 1024), '5.0 MB')
  assert.equal(formatearBytes(undefined), '0 B')
})

test('archive notice never mentions grades as lost and is empty when normal', () => {
  const formato = f => `<${f}>`
  assert.equal(mensajeArchivo({ estado: 'normal' }, formato), '')
  assert.equal(mensajeArchivo(null, formato), '')
  assert.match(mensajeArchivo({ estado: 'programada', eliminacion_en: '2026-10-24' }, formato), /se eliminarán el <2026-10-24>.*se conservan/s)
  assert.match(mensajeArchivo({ estado: 'archivado', archivado_en: '2026-10-25' }, formato), /se depuraron el <2026-10-25>.*se conservan/s)
})

test('purge needs the exact phrase and the saved-copy confirmation', () => {
  const base = { frase: 'DEPURAR X TII', esperada: 'DEPURAR X TII', guardada: true, ocupado: false }
  assert.equal(puedeConfirmar(base), true)
  assert.equal(puedeConfirmar({ ...base, frase: '  DEPURAR X TII ' }), true)
  for (const cambio of [{ frase: 'depurar x tii' }, { frase: '' }, { guardada: false }, { ocupado: true }]) {
    assert.equal(puedeConfirmar({ ...base, ...cambio }), false, JSON.stringify(cambio))
  }
})

test('only scheduled purges past their date are overdue', () => {
  const ahora = new Date('2026-10-20T00:00:00Z')
  assert.equal(purgaVencida({ estado: 'programada', ejecutar_en: '2026-10-19T00:00:00Z' }, ahora), true)
  assert.equal(purgaVencida({ estado: 'programada', ejecutar_en: '2026-10-21T00:00:00Z' }, ahora), false)
  assert.equal(purgaVencida({ estado: 'cancelada', ejecutar_en: '2026-10-19T00:00:00Z' }, ahora), false)
  assert.ok(ETIQUETA_ESTADO.programada)
})