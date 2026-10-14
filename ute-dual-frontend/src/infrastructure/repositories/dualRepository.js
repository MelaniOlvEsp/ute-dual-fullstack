const segment = value => encodeURIComponent(value)
const query = value => value ? `?${value}` : ''

// Implementa las operaciones de la modalidad Dual.
export function createDualRepository(http, baseUrl) {
  return {
    subirFirma: form => http.post('/dual/tutor/firma', form, { multipart: true }),
    estadoFirma: () => http.get('/dual/tutor/firma'),
    subirReporte: form => http.post('/dual/alumno/', form, { multipart: true }),
    misReportes: periodo => http.get(`/dual/alumno/mis-reportes${query(periodo ? `cuatrimestre=${segment(periodo)}` : '')}`),
    semanaActual: () => http.get('/dual/alumno/semana-actual'),
    reportePdfUrl: id => `${baseUrl}/dual/alumno/reporte/${segment(id)}/pdf`,
    listarReportes: params => http.get(`/dual/tutor/reportes${query(params)}`),
    revisarReporte: (id, data) => http.patch(`/dual/tutor/reportes/${segment(id)}`, data),
    listarEmpresas: () => http.get('/dual/tutor/empresas'),
    crearEmpresa: data => http.post('/dual/tutor/empresas', data),
    asignarEmpresa: data => http.post('/dual/tutor/asignaciones', data),
    buscarAlumno: id => http.get(`/dual/tutor/alumnos/${segment(id)}`),
    actualizarAlumnoDual: (id, data) => http.patch(`/dual/tutor/alumnos/${segment(id)}`, data),
    cerrarCuatrimestre: label => http.post('/dual/tutor/cierre', { periodo_label: label }),
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
    subirAlumnosCSV: (id, form) => http.post(`/dual/carrera/grupos/${segment(id)}/alumnos`, form, { multipart: true }),
    agregarAlumno: (id, data) => http.post(`/dual/carrera/grupos/${segment(id)}/alumnos/individual`, data),
    actualizarAlumno: (id, data) => http.patch(`/dual/carrera/alumnos/${segment(id)}`, data),
    eliminarAlumno: id => http.delete(`/dual/carrera/alumnos/${segment(id)}`),
    listarGrupos: carrera => http.get(`/dual/carrera/grupos${query(carrera ? `carrera=${segment(carrera)}` : '')}`)
  }
}
