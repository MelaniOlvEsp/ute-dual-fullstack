import test from 'node:test'
import assert from 'node:assert/strict'
import { MAX_PDF_BYTES, validateGrade, validateReportFile, validateWeeklyReport } from '../src/domain/dual/report.js'
import { createDualUseCases } from '../src/application/use-cases/dual.js'

const goodReport = {
  grade: '9', startDate: '2026-09-01',
  endDate: '2026-09-07', file: { name: 'reporte.pdf', size: 500 }
}

test('client and API share the same 10 MB PDF limit (DP-08)', () => {
  assert.equal(MAX_PDF_BYTES, 10 * 1024 * 1024)
  validateReportFile({ name: 'r.pdf', size: MAX_PDF_BYTES })
  assert.throws(() => validateReportFile({ name: 'r.pdf', size: MAX_PDF_BYTES + 1 }), /10 MB/)
  validateReportFile({ name: 'r.pdf', size: 3 * 1024 * 1024 }) // antes se rechazaba por el tope de 2 MB
})

test('grade must be an integer from 1 to 10 (AC-10)', () => {
  for (const ok of ['1', '10', 7, ' 8 ']) assert.doesNotThrow(() => validateGrade(ok), String(ok))
  for (const bad of ['0', '11', '8.5', '8.0', '8,5', '', 'abc', '-3', null, undefined]) {
    assert.throws(() => validateGrade(bad), /entero entre 1 y 10/, String(bad))
  }
})

test('report validation checks grade, dates and file; week comes from the obligation (DP-12)', () => {
  validateWeeklyReport(goodReport)
  validateWeeklyReport({ ...goodReport, startDate: '2026-09-07', endDate: '2026-09-07' })
  validateWeeklyReport({ ...goodReport, startDate: '2020-01-01', endDate: '2030-01-01' })
  assert.throws(() => validateWeeklyReport({ ...goodReport, grade: 15 }), /entero/)
  assert.throws(() => validateWeeklyReport({ ...goodReport, grade: '8.5' }), /entero/)
  assert.throws(() => validateWeeklyReport({ ...goodReport, endDate: '2026-08-01' }), /inicio/)
  assert.throws(() => validateWeeklyReport({ ...goodReport, startDate: '' }), /fechas/)
  assert.throws(() => validateReportFile({ name: 'image.png', size: 10 }), /PDF/)
  assert.throws(() => validateReportFile({ name: 'r.pdf', size: 0 }), /vacío/)
})

test('delivery validates before creating FormData and targets the obligation', async () => {
  const received = []
  const useCases = createDualUseCases({
    entregarObligacion: async (id, form) => received.push({ id, form })
  }, {}, report => ({ ...report, converted: true }))
  await useCases.submitDelivery('obl-1', goodReport)
  assert.equal(received[0].id, 'obl-1')
  assert.equal(received[0].form.converted, true)
  await assert.rejects(useCases.submitDelivery('obl-1', { ...goodReport, grade: '0' }))
  assert.equal(received.length, 1)
})

test('version download is delegated to the file saver with a safe generated name', async () => {
  const saved = []
  const useCases = createDualUseCases({
    descargarVersion: async () => new Blob(['pdf'])
  }, { save: (blob, name) => saved.push(name) }, report => report)
  await useCases.downloadVersion('rep-1', 3, 'Semana 4')
  assert.deepEqual(saved, ['reporte-semana-4-v3.pdf'])
})
