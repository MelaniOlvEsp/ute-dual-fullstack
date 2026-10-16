import { validateWeeklyReport, validateReview, reviewBody } from '../../domain/dual/report.js'

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
    async downloadVersion(reporteId, numero, etiqueta, documento = 'original') {
      const blob = await repo.descargarVersion(reporteId, numero, documento)
      const sufijo = documento === 'firmado' ? '-firmado' : ''
      fileSaver.save(blob, `reporte-${slug(etiqueta)}-v${numero}${sufijo}.pdf`)
    },
    // Decisión del tutor (C06): valida lo que el servidor también exige, sobre una versión concreta.
    async submitReview(reporteId, numero, review) {
      validateReview(review)
      return repo.revisarVersion(reporteId, numero, reviewBody(review))
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
