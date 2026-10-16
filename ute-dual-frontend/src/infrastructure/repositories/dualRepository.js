const segment = value => encodeURIComponent(value)
const query = value => value ? `?${value}` : ''

// Implementa las operaciones de la modalidad Dual.
export function createDualRepository(http, baseUrl) {
  return {
    subirFirma: form => http.post('/dual/tutor/firma', form, { multipart: true }),
    estadoFirma: () => http.get('/dual/tutor/firma'),
    misReportes: periodo => http.get(`/dual/alumno/mis-reportes${query(periodo ? `cuatrimestre=${segment(periodo)}` : '')}`),
    entregarObligacion: (id, form) => http.post(`/dual/alumno/obligaciones/${segment(id)}/entrega`, form, { multipart: true }),
    versionesReporte: id => http.get(`/dual/alumno/reportes/${segment(id)}/versiones`),
    descargarVersion: (id, numero, documento = 'original') => http.get(`/dual/alumno/reportes/${segment(id)}/versiones/${segment(numero)}/pdf${query(documento === 'firmado' ? 'documento=firmado' : '')}`, { blob: true }),
    misObligaciones: periodo => http.get(`/dual/alumno/obligaciones${query(periodo ? `periodo=${segment(periodo)}` : '')}`),
    reportePdfUrl: id => `${baseUrl}/dual/alumno/reporte/${segment(id)}/pdf`,
    listarReportes: params => http.get(`/dual/tutor/reportes${query(params)}`),
    detalleReporte: id => http.get(`/dual/tutor/reportes/${segment(id)}`),
    revisarVersion: (id, numero, data) => http.post(`/dual/tutor/reportes/${segment(id)}/versiones/${segment(numero)}/revision`, data),
    versionPdfUrlTutor: (id, numero = 1, documento = 'original') => `${baseUrl}/dual/tutor/reportes/${segment(id)}/versiones/${segment(numero)}/pdf${query(documento === 'firmado' ? 'documento=firmado' : '')}`,
    listarEmpresas: () => http.get('/dual/tutor/empresas'),
    crearEmpresa: data => http.post('/dual/tutor/empresas', data),
    asignarEmpresa: data => http.post('/dual/tutor/asignaciones', data),
    buscarAlumno: id => http.get(`/dual/tutor/alumnos/${segment(id)}`),
    obligacionesAlumno: (id, periodo) => http.get(`/dual/tutor/alumnos/${segment(id)}/obligaciones${query(periodo ? `periodo=${segment(periodo)}` : '')}`),
    historialIncorporaciones: id => http.get(`/dual/tutor/alumnos/${segment(id)}/incorporaciones`),
    actualizarAlumnoDual: (id, data) => http.patch(`/dual/tutor/alumnos/${segment(id)}`, data),
    // C07: estado, cierre de recepción y finalización por ID de período (confirmación explícita).
    periodosEstado: () => http.get('/dual/tutor/periodos'),
    resumenPeriodo: id => http.get(`/dual/tutor/periodos/${segment(id)}/resumen`),
    cerrarRecepcion: id => http.post(`/dual/tutor/periodos/${segment(id)}/cierre-recepcion`, { confirmar: true }),
    finalizarEvaluacion: id => http.post(`/dual/tutor/periodos/${segment(id)}/finalizacion`, { confirmar: true }),
    abrirCuatrimestre: data => http.post('/dual/tutor/abrir-cuatrimestre', data),
    cuatrimestreActual: () => http.get('/dual/tutor/cuatrimestre-actual'),
    alumnosSinReporte: (periodo, semana) => http.get(`/dual/tutor/alumnos-sin-reporte?cuatrimestre=${segment(periodo)}&semana=${segment(semana)}`),
    alumnosAtrasados: () => http.get('/dual/tutor/alumnos-atrasados'),
    reportePdfUrlCoordinador: id => `${baseUrl}/dual/tutor/reporte/${segment(id)}/pdf`,
    listarAlumnos: params => http.get(`/dual/carrera/alumnos${query(params)}`),
    periodos: () => http.get('/dual/carrera/periodos'),
    expediente: (id, periodo) => http.get(`/dual/carrera/alumnos/${segment(id)}/reportes${query(periodo ? `cuatrimestre=${segment(periodo)}` : '')}`),
    reportePdfUrlCarrera: id => `${baseUrl}/dual/carrera/reporte/${segment(id)}/pdf`,
    exportarCSV: (id, periodo) => http.get(`/dual/carrera/alumnos/${segment(id)}/exportar-csv${query(periodo ? `cuatrimestre=${segment(periodo)}` : '')}`, { blob: true }),
    exportarZip: (id, periodo) => http.get(`/dual/carrera/alumnos/${segment(id)}/exportar-zip${query(periodo ? `cuatrimestre=${segment(periodo)}` : '')}`, { blob: true }),
    crearGrupo: data => http.post('/dual/carrera/grupos', data),
    listarCarreras: () => http.get('/dual/carrera/carreras'),
    previewAlumnosCSV: (id, form) => http.post(`/dual/carrera/grupos/${segment(id)}/alumnos/preview`, form, { multipart: true }),
    subirAlumnosCSV: (id, form) => http.post(`/dual/carrera/grupos/${segment(id)}/alumnos`, form, { multipart: true }),
    agregarAlumno: (id, data) => http.post(`/dual/carrera/grupos/${segment(id)}/alumnos/individual`, data),
    actualizarAlumno: (id, data) => http.patch(`/dual/carrera/alumnos/${segment(id)}`, data),
    eliminarAlumno: id => http.delete(`/dual/carrera/alumnos/${segment(id)}`),
    listarGrupos: carrera => http.get(`/dual/carrera/grupos${query(carrera ? `carrera=${segment(carrera)}` : '')}`),
    historialGrupos: id => http.get(`/dual/carrera/alumnos/${segment(id)}/grupos`),
    previewPromocion: data => http.post('/dual/carrera/grupos/promociones/preview', data),
    aplicarPromocion: data => http.post('/dual/carrera/grupos/promociones', data)
  }
}
