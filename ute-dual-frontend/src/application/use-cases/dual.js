import { validateWeeklyReport } from '../../domain/dual/report.js'

// Nombre de descarga generado en el cliente a partir de la etiqueta de la semana (no del archivo).
const slug = text => String(text || 'semana').toLowerCase().normalize('NFD')
  .replace(/[̀-ͯ]/g, '').replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '')

// Coordina la descarga del expediente sin acceder directamente al DOM.
export function createDualUseCases(repo, fileSaver, formBuilder) {
  return {
    ...repo,
    // Entrega o reenvía una obligación (C05): valida antes de crear el multipart.
    async submitDelivery(obligacionId, report) {
      validateWeeklyReport(report)
      return repo.entregarObligacion(obligacionId, formBuilder(report))
    },
    async downloadVersion(reporteId, numero, etiqueta) {
      const blob = await repo.descargarVersion(reporteId, numero)
      fileSaver.save(blob, `reporte-${slug(etiqueta)}-v${numero}.pdf`)
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
