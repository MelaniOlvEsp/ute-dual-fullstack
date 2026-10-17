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
    // C08 / DP-14: paquetes de archivo (ZIP con manifiesto y hashes). El nombre se genera en el cliente
    // a partir de datos del servidor, nunca de un nombre de archivo del alumno.
    async downloadMyPackage(periodoId, etiqueta) {
      fileSaver.save(await repo.miPaquete(periodoId), `mi-paquete-${slug(etiqueta)}.zip`)
    },
    async downloadStudentPackage(matricula, periodoId, etiqueta) {
      fileSaver.save(await repo.paqueteAlumno(matricula, periodoId), `paquete-${slug(matricula)}-${slug(etiqueta)}.zip`)
    },
    async downloadCareerPackage(codigo, periodoId, etiqueta) {
      fileSaver.save(await repo.paqueteCarrera(codigo, periodoId), `paquete-${slug(codigo)}-${slug(etiqueta)}.zip`)
    },
    async downloadApproved(reporteId, numero, documento, etiqueta) {
      const sufijo = documento === 'original' ? '-original' : '-firmado'
      fileSaver.save(await repo.descargarAprobado(reporteId, numero, documento), `reporte-${slug(etiqueta)}-v${numero}${sufijo}.pdf`)
    }
  }
}
