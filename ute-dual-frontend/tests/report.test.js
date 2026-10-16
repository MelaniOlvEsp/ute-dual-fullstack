import test from 'node:test'
import assert from 'node:assert/strict'
import {
  MAX_PDF_BYTES, OBSERVACION_MAX, reviewBody, validateGrade, validateReportFile, validateReview,
  validateWeeklyReport
} from '../src/domain/dual/report.js'
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
  await useCases.downloadVersion('rep-1', 3, 'Semana 4', 'firmado')
  assert.deepEqual(saved, ['reporte-semana-4-v3.pdf', 'reporte-semana-4-v3-firmado.pdf'])
})

test('review: rejection needs an observation and corrections follow the delivery rules (RN-14, AC-12)', () => {
  validateReview({ decision: 'Aprobada' })
  validateReview({ decision: 'Rechazada', observacion: ' Falta la firma de la empresa ' })
  assert.throws(() => validateReview({ decision: 'Rechazada', observacion: '   ' }), /observación del rechazo/)
  assert.throws(() => validateReview({ decision: 'Pendiente' }), /aprobar o rechazar/)
  assert.throws(() => validateReview({ decision: 'Aprobada', observacion: 'x'.repeat(OBSERVACION_MAX + 1) }), /1000/)
  for (const nota of ['0', '11', '8.5']) {
    assert.throws(() => validateReview({ decision: 'Aprobada', nota }), /entero entre 1 y 10/, nota)
  }
  assert.throws(() => validateReview({ decision: 'Aprobada', fechaInicio: '2026-10-17', fechaFin: '2026-10-12' }), /inicio/)
})

test('review request body carries only what the tutor provided', () => {
  assert.deepEqual(reviewBody({ decision: 'Aprobada', nota: '', fechaInicio: '', fechaFin: '' }), { decision: 'Aprobada' })
  assert.deepEqual(
    reviewBody({ decision: 'Rechazada', observacion: ' Corrige ', nota: '9', fechaInicio: '2026-10-12', fechaFin: '2026-10-16' }),
    { decision: 'Rechazada', observacion: 'Corrige', calificacion: 9, fecha_inicio: '2026-10-12', fecha_fin: '2026-10-16' })
})

test('review is validated before reaching the repository and targets a concrete version', async () => {
  const received = []
  const useCases = createDualUseCases({
    revisarVersion: async (id, numero, body) => received.push({ id, numero, body })
  }, {}, report => report)
  await useCases.submitReview('rep-1', 2, { decision: 'Rechazada', observacion: 'Falta firma' })
  assert.deepEqual(received[0], { id: 'rep-1', numero: 2, body: { decision: 'Rechazada', observacion: 'Falta firma' } })
  await assert.rejects(useCases.submitReview('rep-1', 2, { decision: 'Rechazada' }))
  assert.equal(received.length, 1)
})
