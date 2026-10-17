const segment = value => encodeURIComponent(value)
const query = value => value ? `?${value}` : ''

// Implementa las operaciones de la modalidad Dual.
export function createDualRepository(http, baseUrl) {
  return {
    subirFirma: form => http.post('/dual/tutor/firma', form, { multipart: true }),
    estadoFirma: () => http.get('/dual/tutor/firma'),
    // C08: expediente propio por período (la matrícula sale de la sesión) y su paquete de archivo.
    miExpediente: () => http.get('/dual/alumno/expediente'),
    miPaquete: periodoId => http.get(`/dual/alumno/paquete?periodo_id=${segment(periodoId)}`, { blob: true }),
    entregarObligacion: (id, form) => http.post(`/dual/alumno/obligaciones/${segment(id)}/entrega`, form, { multipart: true }),
    versionesReporte: id => http.get(`/dual/alumno/reportes/${segment(id)}/versiones`),
    descargarVersion: (id, numero, documento = 'original') => http.get(`/dual/alumno/reportes/${segment(id)}/versiones/${segment(numero)}/pdf${query(documento === 'firmado' ? 'documento=firmado' : '')}`, { blob: true }),
    misObligaciones: periodo => http.get(`/dual/alumno/obligaciones${query(periodo ? `periodo=${segment(periodo)}` : '')}`),
    versionPdfUrlAlumno: (id, numero = 1, documento = 'firmado') => `${baseUrl}/dual/alumno/reportes/${segment(id)}/versiones/${segment(numero)}/pdf${query(documento === 'firmado' ? 'documento=firmado' : '')}`,
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
    listarAlumnos: params => http.get(`/dual/carrera/alumnos${query(params)}`),
    periodos: () => http.get('/dual/carrera/periodos'),
    // C08: expediente por período para el personal, descarga de aprobados por documento versionado
    // y paquetes de archivo (solo el tutor los genera).
    expedienteAlumno: id => http.get(`/dual/carrera/alumnos/${segment(id)}/expediente`),
    versionPdfUrlCarrera: (id, numero = 1, documento = 'firmado') => `${baseUrl}/dual/carrera/reportes/${segment(id)}/versiones/${segment(numero)}/pdf?documento=${documento === 'original' ? 'original' : 'firmado'}`,
    descargarAprobado: (id, numero, documento = 'firmado') => http.get(`/dual/carrera/reportes/${segment(id)}/versiones/${segment(numero)}/pdf?documento=${documento === 'original' ? 'original' : 'firmado'}`, { blob: true }),
    paqueteAlumno: (matricula, periodoId) => http.get(`/dual/carrera/paquetes/alumno/${segment(matricula)}?periodo_id=${segment(periodoId)}`, { blob: true }),
    paqueteCarrera: (codigo, periodoId) => http.get(`/dual/carrera/paquetes/carrera/${segment(codigo)}?periodo_id=${segment(periodoId)}`, { blob: true }),
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
