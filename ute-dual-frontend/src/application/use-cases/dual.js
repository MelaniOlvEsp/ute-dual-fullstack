import { validateWeeklyReport } from '../../domain/dual/report.js'

// Coordina la descarga del expediente sin acceder directamente al DOM.
export function createDualUseCases(repo, fileSaver, formBuilder) {
  return {
    ...repo,
    async submitWeeklyReport(report) {
      validateWeeklyReport(report)
      return repo.subirReporte(formBuilder(report))
    },
    async exportarCSV(matricula, periodo) {
      const blob = await repo.exportarCSV(matricula, periodo)
      fileSaver.save(blob, `expediente_${matricula}.csv`)
    },
    async exportarZip(matricula, periodo) {
      const blob = await repo.exportarZip(matricula, periodo)
      fileSaver.save(blob, `expediente_${matricula}.zip`)
    }
  }
}
