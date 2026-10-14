import test from 'node:test'
import assert from 'node:assert/strict'
import { validateReportFile, validateWeeklyReport } from '../src/domain/dual/report.js'
import { createDualUseCases } from '../src/application/use-cases/dual.js'

const goodReport = {
  week: '2', grade: '9.2', startDate: '2026-09-01',
  endDate: '2026-09-07', file: { name: 'reporte.pdf', size: 500 }
}

test('report validation enforces week, grade and date ranges', () => {
  validateWeeklyReport(goodReport)
  assert.throws(() => validateWeeklyReport({...goodReport, week: 19}), /semana/)
  assert.throws(() => validateWeeklyReport({...goodReport, grade: 15}), /calificación/)
  assert.throws(() => validateWeeklyReport({...goodReport, endDate: '2026-08-01'}), /inicio/)
  assert.throws(() => validateReportFile({name:'image.png',size:0}), /PDF/)
  assert.throws(() => validateReportFile({name:'r.pdf',size:3*1024*1024}), /pesado/)
})

test('report submission validates before creating FormData', async () => {
  const received = []
  const useCases = createDualUseCases({
    subirReporte: async form => received.push(form)
  }, {}, report => ({ ...report, converted: true }))
  await useCases.submitWeeklyReport(goodReport)
  assert.equal(received[0].converted, true)
  await assert.rejects(useCases.submitWeeklyReport({...goodReport, week: 20}))
  assert.equal(received.length, 1)
})
