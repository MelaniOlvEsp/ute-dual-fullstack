<script>
  // src/routes/dual/CoordinadorDual.svelte
  import { onMount } from 'svelte'
  import { navigate, useLocation } from 'svelte-routing'
  import { get } from 'svelte/store'
  import { isAuthenticated, isTutorAcademico } from '../../stores/auth.js'
  import { api } from '../../../composition/api.js'
  import FirmaTutor from '../../components/dual/FirmaTutor.svelte'
  import Navbar from '../../components/layout/Navbar.svelte'
  import FiltrosBarra from '../../components/shared/FiltrosBarra.svelte'
  import PageHeader from '../../components/ui/PageHeader.svelte'
  import LoadingSpinner from '../../components/ui/LoadingSpinner.svelte'
  import EmptyState from '../../components/ui/EmptyState.svelte'
  import { formatFecha, formatFechaCivil, hoyOperativo, estadoBadgeClass } from '../../utils/formatters.js'
  import VisorPDF from '../../components/shared/VisorPDF.svelte'

  const location = useLocation()

  let vista = 'bandeja'
  let mounted = false

  $: if (mounted) {
    const params = new URLSearchParams($location.search)
    const queryVista = params.get('vista')
    if (queryVista === 'empresas' && vista !== 'empresas') {
      vista = 'empresas'
      cargarEmpresas()
    } else if (queryVista === 'expediente' && vista !== 'expediente') {
      vista = 'expediente'
      cargarDirectorioExp()
    } else if (!queryVista && vista !== 'bandeja' && vista !== 'revision') {
      vista = 'bandeja'
      alumnoExpSeleccionado = null
      pdfExpSeleccionado = null
      reportesExp = []
      cargarReportes()
    }
  }

  let reportes = []
  let loading = true
  let error = ''
  let filtroEstado = 'Pendiente'
  let filtroBusqueda = ''
  let filtroCarrera = ''
  let filtroGrupo = ''

  $: grupos = [...new Set(reportes.map(r => r.nomenclatura).filter(Boolean))].sort()
  $: carreras = [...new Set(reportes.map(r => r.carrera).filter(Boolean))].sort()

  $: reportesFiltrados = reportes.filter(r => {
    const matchBusqueda = filtroBusqueda.trim()
      ? r.matricula.toLowerCase().includes(filtroBusqueda.toLowerCase()) ||
        (r.nombre && r.nombre.toLowerCase().includes(filtroBusqueda.toLowerCase()))
      : true

    const matchCarrera = filtroCarrera && r.carrera
      ? (r.carrera.toLowerCase() === filtroCarrera.toLowerCase())
      : true

    const matchGrupo = filtroGrupo && r.nomenclatura
      ? (r.nomenclatura.toLowerCase() === filtroGrupo.toLowerCase())
      : true

    const matchEstado = !modoNoEntregado && filtroEstado
      ? r.estado === filtroEstado
      : true

    return matchBusqueda && matchCarrera && matchGrupo && matchEstado
  })

  let seleccionado = null
  let accion = ''
  let nota = ''
  let enviando = false
  let exito = ''
  let errorAccion = ''
  
  let editCalificacion = ''
  let editFechaInicio = ''
  let editFechaFin = ''

  let empresas = []
  let loadingEmpresas = false
  let nuevaEmpresa = ''
  let empresaSeleccionada = ''
  let matriculaBusqueda = ''
  let alumnoPreview = null
  let loadingPreview = false
  let errorAsignacion = ''
  let exitoAsignacion = ''
  let guardandoAsignacion = false
  let fechaInicioIncorporacion = hoyOperativo()
  let fechaBajaIncorporacion = hoyOperativo()
  let historialIncorporaciones = []
  let obligacionesAlumno = []
  const ETIQUETA_ESTADO = {
    PENDIENTE: 'Pendiente', ATRASADA: 'Atrasada', RECIBIDA: 'Recibida',
    NO_RECIBIDA_POR_CIERRE: 'No recibida por cierre'
  }

  async function cargarObligaciones(matricula) {
    try {
      obligacionesAlumno = await api.dual.obligacionesAlumno(matricula)
    } catch {
      obligacionesAlumno = []
    }
  }
  let confirmandoBaja = false

  // Expediente / directorio
  let alumnosExpediente = []
  let loadingAlumnos = false
  let filtroCuatrimestreExp = ''
  let filtroBusquedaExp = ''
  let alumnoExpSeleccionado = null
  let reportesExp = []
  let loadingReportesExp = false
  let pdfExpSeleccionado = null
  let periodos = []
  let periodoSeleccionadoExp = ''

  onMount(() => {
    if (!get(isAuthenticated) || !get(isTutorAcademico)) {
      navigate('/login', { replace: true })
      return
    }

    const queryVista = new URLSearchParams(window.location.search).get('vista')
    let initialVista = 'bandeja'
    if (queryVista === 'empresas') initialVista = 'empresas'
    else if (queryVista === 'expediente') initialVista = 'expediente'

    vista = initialVista

    if (vista === 'empresas') {
      cargarEmpresas()
    } else if (vista === 'expediente') {
      cargarPeriodos()
      cargarDirectorioExp()
    } else {
      cargarReportes()
    }
    mounted = true
  })

  async function cargarPeriodos() {
    try {
      periodos = await api.dual.periodos()
      if (periodos.length && !periodoSeleccionadoExp) {
        periodoSeleccionadoExp = periodos[0].cuatrimestre
        filtroCuatrimestreExp = periodos[0].cuatrimestre
      }
    } catch {
      periodos = []
    }
  }

  let modoNoEntregado = false

  // C07: aviso del estado del período para el tutor (recepción abierta o cerrada sin finalizar).
  let avisoPeriodo = ''

  async function cargarAvisoPeriodo() {
    try {
      const lista = await api.dual.periodosEstado()
      const hoy = hoyOperativo()
      const abierto = lista.find(p => p.recepcion === 'abierta')
      const cerrado = lista.find(p => p.recepcion === 'cerrada' && p.evaluacion === 'en_curso' &&
        p.fecha_inicio && p.fecha_inicio <= hoy)
      if (abierto) {
        avisoPeriodo = `Período ${abierto.periodo_label}: recepción abierta.`
      } else if (cerrado) {
        avisoPeriodo = `La recepción de ${cerrado.periodo_label} se cerró el ${formatFechaCivil(cerrado.cierre_efectivo)}. Puedes seguir revisando lo recibido; la evaluación aún no está finalizada.`
      } else {
        avisoPeriodo = ''
      }
    } catch {
      avisoPeriodo = ''
    }
  }

  async function cargarReportes() {
    cargarAvisoPeriodo()
    loading = true
    error = ''
    try {
      if (filtroEstado === 'No entregado') {
        modoNoEntregado = true
        reportes = await api.dual.alumnosAtrasados()
      } else {
        modoNoEntregado = false
        const params = new URLSearchParams()
        if (filtroEstado) {
          params.append('estado', filtroEstado)
        }
        reportes = await api.dual.listarReportes(params.toString())
      }
    } catch (e) {
      error = e.message || 'Error al cargar reportes.'
    } finally {
      loading = false
    }
  }

  // C06: la revisión recae sobre una versión concreta; el detalle trae todas con sus decisiones.
  let detalle = null
  let cargandoDetalle = false
  let documentoVisor = 'original'

  $: versionVigente = detalle?.versiones?.[0] || null
  $: puedeRevisar = !!detalle?.puede_revisar
  $: urlVisor = detalle && detalle.version_vigente
    ? api.dual.versionPdfUrlTutor(detalle.id, verVersion ?? detalle.version_vigente, documentoVisor)
    : ''
  let verVersion = null

  function cargarCamposDeVersion(v) {
    editCalificacion = v ? String(v.validada_nota ?? v.nota) : ''
    editFechaInicio = v ? (v.validada_inicio || v.fecha_inicio || '') : ''
    editFechaFin = v ? (v.validada_fin || v.fecha_fin || '') : ''
  }

  async function cargarDetalle(id) {
    cargandoDetalle = true
    try {
      detalle = await api.dual.detalleReporte(id)
      verVersion = detalle.version_vigente
      documentoVisor = 'original'
      cargarCamposDeVersion(detalle.versiones?.[0])
    } catch (e) {
      errorAccion = e.message || 'No se pudo cargar el reporte.'
    } finally {
      cargandoDetalle = false
    }
  }

  function abrirRevision(reporte) {
    seleccionado = reporte
    detalle = null
    accion = ''
    nota = ''
    exito = ''
    errorAccion = ''
    editCalificacion = ''
    editFechaInicio = ''
    editFechaFin = ''
    vista = 'revision'
    cargarDetalle(reporte.id)
  }

  function volverBandeja() {
    seleccionado = null
    detalle = null
    vista = 'bandeja'
    cargarReportes()
  }

  async function enviarDecision() {
    if (!accion) {
      errorAccion = 'Selecciona una acción.'
      return
    }
    enviando = true
    errorAccion = ''
    exito = ''
    try {
      const resultado = await api.dual.submitReview(detalle.id, detalle.version_vigente, {
        decision: accion === 'aprobar' ? 'Aprobada' : 'Rechazada',
        observacion: nota,
        nota: editCalificacion,
        fechaInicio: editFechaInicio,
        fechaFin: editFechaFin
      })
      exito = accion === 'aprobar'
        ? 'Reporte aprobado y firmado.'
        : 'Reporte rechazado. El alumno podrá reenviar.'
      if (resultado?.firma === 'hoja_adicional') {
        exito += ' No se reconoció la celda de firma del formato; se agregó una hoja de firma al final.'
      }
      await cargarDetalle(detalle.id)
      if (accion === 'aprobar') documentoVisor = 'firmado'
      seleccionado = { ...seleccionado, estado: detalle.estado }
    } catch (e) {
      errorAccion = e.message || 'Error al enviar la decisión.'
    } finally {
      enviando = false
    }
  }

  const ETIQUETA_CORRECCION = { nota: 'Nota', fecha_inicio: 'Inicio', fecha_fin: 'Fin' }

  async function cargarEmpresas() {
    loadingEmpresas = true
    try {
      empresas = await api.dual.listarEmpresas()
    } catch {
      errorAsignacion = 'No se pudieron cargar las empresas.'
    } finally {
      loadingEmpresas = false
    }
  }

  async function buscarAlumno() {
    if (!matriculaBusqueda.trim()) {
      return
    }
    loadingPreview = true
    alumnoPreview = null
    errorAsignacion = ''
    try {
      alumnoPreview = await api.dual.buscarAlumno(matriculaBusqueda.trim())
      empresaSeleccionada = alumnoPreview.empresa_id || ''
      fechaInicioIncorporacion = alumnoPreview.fecha_inicio || hoyOperativo()
      try {
        historialIncorporaciones = await api.dual.historialIncorporaciones(matriculaBusqueda.trim())
      } catch {
        historialIncorporaciones = []
      }
      await cargarObligaciones(matriculaBusqueda.trim())
      confirmandoBaja = false
    } catch {
      errorAsignacion = 'Alumno no encontrado.'
    } finally {
      loadingPreview = false
    }
  }

  async function crearEmpresa() {
    if (!nuevaEmpresa.trim()) {
      return
    }
    try {
      const emp = await api.dual.crearEmpresa({ 
        nombre: nuevaEmpresa.trim() 
      })
      empresas = [...empresas, emp]
      empresaSeleccionada = emp.id
      nuevaEmpresa = ''
    } catch (e) {
      errorAsignacion = e.message || 'Error al crear la empresa.'
    }
  }

  async function guardarAsignacion() {
    errorAsignacion = ''
    exitoAsignacion = ''
    if (!alumnoPreview) { 
      errorAsignacion = 'Busca un alumno primero.'
      return 
    }
    if (!empresaSeleccionada) { 
      errorAsignacion = 'Selecciona una empresa.'
      return 
    }
    guardandoAsignacion = true
    try {
      await api.dual.actualizarAlumnoDual(alumnoPreview.matricula, {
        alumno_dual: true,
        empresa_id: empresaSeleccionada,
        fecha_inicio: fechaInicioIncorporacion
      })
      
      exitoAsignacion = 'Alumno dual actualizado correctamente.'
      const nombreEmpresa = empresas.find(e => e.id === empresaSeleccionada)?.nombre
      alumnoPreview = {
        ...alumnoPreview,
        es_alumno_dual: true,
        empresa_id: empresaSeleccionada,
        empresa: nombreEmpresa,
        fecha_inicio: fechaInicioIncorporacion
      }
      historialIncorporaciones = await api.dual.historialIncorporaciones(alumnoPreview.matricula)
      await cargarObligaciones(alumnoPreview.matricula)
    } catch (e) {
      errorAsignacion = e.message || 'Error al guardar la asignación.'
    } finally {
      guardandoAsignacion = false
    }
  }

  async function quitarDual() {
    if (!alumnoPreview) {
      return
    }
    guardandoAsignacion = true
    errorAsignacion = ''
    exitoAsignacion = ''
    try {
      await api.dual.actualizarAlumnoDual(alumnoPreview.matricula, { 
        alumno_dual: false,
        fecha_baja: fechaBajaIncorporacion
      })
      exitoAsignacion = 'Incorporación finalizada; cuenta, grupos y expediente conservados.'
      alumnoPreview = { 
        ...alumnoPreview, 
        es_alumno_dual: false, 
        activo: false 
      }
      confirmandoBaja = false
      historialIncorporaciones = await api.dual.historialIncorporaciones(alumnoPreview.matricula)
      await cargarObligaciones(alumnoPreview.matricula)
    } catch (e) {
      errorAsignacion = e.message || 'Error al quitar el rol dual.'
    } finally {
      guardandoAsignacion = false
    }
  }

  async function cargarDirectorioExp() {
    if (vista !== 'expediente') {
      vista = 'expediente'
      navigate('/dual/tutor?vista=expediente', { replace: true })
    }
    alumnoExpSeleccionado = null
    pdfExpSeleccionado = null
    reportesExp = []
    loadingAlumnos = true
    try {
      const params = new URLSearchParams()
      if (periodoSeleccionadoExp) params.append('cuatrimestre', periodoSeleccionadoExp)
      alumnosExpediente = await api.dual.listarAlumnos(params.toString())
    } catch (e) {
      alumnosExpediente = []
    } finally {
      loadingAlumnos = false
    }
  }

  function volverDirectorio() {
    alumnoExpSeleccionado = null
    pdfExpSeleccionado = null
    reportesExp = []
    errorExp = ''
  }

  $: alumnosExpFiltrados = alumnosExpediente.filter(a => {
    const b = filtroBusquedaExp.toLowerCase()
    return !b || a.matricula.toLowerCase().includes(b) || a.nombre.toLowerCase().includes(b)
  })

  async function abrirExpAlumno(alumno) {
    alumnoExpSeleccionado = alumno
    pdfExpSeleccionado = null
    reportesExp = []
    loadingReportesExp = true
    try {
      reportesExp = await api.dual.expediente(alumno.matricula, periodoSeleccionadoExp || null)
    } catch {
      reportesExp = []
    } finally {
      loadingReportesExp = false
    }
  }

  async function cambiarPeriodoExp() {
    if (alumnoExpSeleccionado) {
      filtroCuatrimestreExp = periodoSeleccionadoExp
      await abrirExpAlumno(alumnoExpSeleccionado)
    } else {
      filtroCuatrimestreExp = periodoSeleccionadoExp
      await cargarDirectorioExp()
    }
  }

  let errorExp = ''

  $: promedioExp = reportesExp.length
    ? (reportesExp.reduce((s, r) => s + Number(r.calificacion_alumno), 0) / reportesExp.length).toFixed(2)
    : null

  async function descargarCSVExp(matricula) {
    await api.dual.exportarCSV(matricula, periodoSeleccionadoExp || undefined)
  }

  $: carreraCompletaRevision = seleccionado ? seleccionado.carrera : '—'
  $: carreraCompletaPreview = alumnoPreview ? alumnoPreview.carrera : '—'
  $: carreraExpSel = alumnoExpSeleccionado ? alumnoExpSeleccionado.carrera : '—'
</script>

<svelte:head>
  <title>Tutor académico | Portal Dual</title>
</svelte:head>

<Navbar />

<div class="main-content">

  {#if vista === 'bandeja'}
    <div class="page-wrap">
      <PageHeader 
        title="Bandeja de Reportes Duales" 
        subtitle="Revisión semanal de entregas de alumnos DUAL" 
      />

      {#if avisoPeriodo}
        <p class="aviso-periodo" role="status">{avisoPeriodo}</p>
      {/if}

      <FirmaTutor />
      <FiltrosBarra
        mostrarCarrera={true}
        mostrarGrupo={true}
        mostrarEstado={true}
        {grupos}
        {carreras}
        bind:filtroEstado
        bind:filtroBusqueda
        bind:filtroCarrera
        bind:filtroGrupo
        on:buscar={cargarReportes}
      />

      {#if loading}
        <LoadingSpinner />
      {:else if error}
        <p class="error-msg">{error}</p>
      {:else if reportesFiltrados.length === 0}
        <EmptyState message="No hay reportes con los filtros seleccionados." />
      {:else}
        <div class="table-wrap">
          <table class="reporte-table">
            <thead>
              {#if modoNoEntregado}
                <tr>
                  <th>Matrícula</th>
                  <th>Nombre</th>
                  <th>Grupo</th>
                  <th>Empresa</th>
                  <th class="td-center">Semana</th>
                  <th class="td-center">Estado</th>
                </tr>
              {:else}
                <tr>
                  <th>Matrícula</th>
                  <th>Nombre</th>
                  <th class="td-center">Calificación</th>
                  <th>Estado</th>
                  <th>Entregado</th>
                  <th></th>
                </tr>
              {/if}
            </thead>
            <tbody>
              {#if modoNoEntregado}
                {#each reportesFiltrados as r}
                  <tr>
                    <td class="td-matricula">{r.matricula}</td>
                    <td class="td-nombre">{r.nombre || '—'}</td>
                    <td style="font-family: monospace;">{r.nomenclatura || '—'}</td>
                    <td>{r.empresa || '—'}</td>
                    <td class="td-center" style="font-weight: 700; color: var(--text-primary);">
                      Semana {r.semana_esperada}{#if r.parcial}&nbsp;(parcial){/if}
                      <div style="font-weight: 400; font-size: 12px; color: var(--text-secondary);">
                        {formatFechaCivil(r.inicio_efectivo)} – {formatFechaCivil(r.fin_efectivo)}
                      </div>
                    </td>
                    <td class="td-center">
                      {#if r.status === 'Overdue'}
                        <span class="badge-overdue">Overdue</span>
                      {:else if r.status === 'NotReceived'}
                        <span class="badge-pending-filter">No recibida por cierre</span>
                      {:else}
                        <span class="badge-pending-filter">Pending</span>
                      {/if}
                    </td>
                  </tr>
                {/each}
              {:else}
                {#each reportesFiltrados as r}
                  <tr class:row-pendiente={r.estado === 'Pendiente'}>
                    <td class="td-matricula">{r.matricula}</td>
                    <td class="td-nombre">{r.nombre || '—'}</td>
                    <td class="td-cal">{r.calificacion_alumno}</td>
                    <td>
                      <span class={estadoBadgeClass(r.estado)}>
                        {r.estado}
                      </span>
                    </td>
                    <td class="td-fecha">{formatFecha(r.created_at)}</td>
                    <td style="text-align: right;">
                      <button class="btn-revisar" on:click={() => abrirRevision(r)}>
                        {r.estado === 'Pendiente' ? 'Revisar' : 'Ver'}
                      </button>
                    </td>
                  </tr>
                {/each}
              {/if}
            </tbody>
          </table>
        </div>
        <p class="count-label">
          {reportesFiltrados.length} {modoNoEntregado ? 'alumno' : 'reporte'}{reportesFiltrados.length !== 1 ? 's' : ''}
          {modoNoEntregado ? ' pendiente' : ''}{reportesFiltrados.length !== 1 && modoNoEntregado ? 's' : ''}
        </p>

      {/if}
    </div>

  {:else if vista === 'revision' && seleccionado}
    <div class="revision-wrap">
      <div class="revision-topbar">
        <button class="btn-back" on:click={volverBandeja}>
          <svg 
            width="16" 
            height="16" 
            fill="none" 
            stroke="currentColor" 
            stroke-width="2.2" 
            viewBox="0 0 24 24" 
            style="display:inline; margin-right:4px; vertical-align:text-bottom;"
          >
            <path stroke-linecap="round" stroke-linejoin="round" d="M10.5 19.5 L3 12 m0 0 l7.5-7.5 M3 12 h18" />
          </svg>
          Volver a la bandeja
        </button>
        <span class={estadoBadgeClass(seleccionado.estado)}>
          {seleccionado.estado}
        </span>
      </div>

      <div class="split-layout">
        <div class="panel-pdf">
          <div class="panel-label">Documento del reporte</div>
          {#if cargandoDetalle && !detalle}
            <LoadingSpinner />
          {:else if urlVisor}
            {#if detalle.versiones.some(v => v.numero === verVersion && v.firmado)}
              <div class="tabs-doc" role="group" aria-label="Documento a mostrar">
                <button class="tab-doc" class:activo={documentoVisor === 'original'} aria-pressed={documentoVisor === 'original'} on:click={() => documentoVisor = 'original'}>Original del alumno</button>
                <button class="tab-doc" class:activo={documentoVisor === 'firmado'} aria-pressed={documentoVisor === 'firmado'} on:click={() => documentoVisor = 'firmado'}>Firmado</button>
              </div>
            {/if}
            <VisorPDF
              url={urlVisor}
              titulo={`Semana ${detalle.semana} · versión ${verVersion}${documentoVisor === 'firmado' ? ' · firmado' : ''}`}
            />
          {:else}
            <div class="no-pdf">No hay un archivo PDF asociado a esta entrega.</div>
          {/if}
        </div>

        <div class="panel-acciones">
          <div class="panel-label">Revisión del tutor académico</div>

          <div class="dato-cal">
            <label class="dato-label" for="nota-empresa">Nota de la empresa (entero de 1 a 10)</label>
            {#if puedeRevisar}
              <input
                id="nota-empresa"
                type="number"
                inputmode="numeric"
                class="input-plain"
                style="font-size: 28px; font-weight: 800; color: var(--orange); text-align: center; margin-top: 8px; width: 100%;"
                min="1" max="10" step="1"
                bind:value={editCalificacion}
              />
              {#if versionVigente && editCalificacion !== '' && String(versionVigente.nota) !== String(editCalificacion)}
                <p class="hint-corr">Declarada por el alumno: {versionVigente.nota}. Se guardará como corrección.</p>
              {/if}
            {:else}
              <p class="dato-valor">{versionVigente?.validada_nota ?? versionVigente?.nota ?? seleccionado.calificacion_alumno}</p>
            {/if}
          </div>

          <div class="ficha-alumno">
            <p class="ficha-titulo">Ficha del estudiante</p>
            <div class="ficha-grid">
              <span class="ficha-key">Nombre</span>
              <span class="ficha-val">{seleccionado.nombre || '—'}</span>
              
              <span class="ficha-key">Matrícula</span>
              <span class="ficha-val ficha-mono">{seleccionado.matricula}</span>
              
              <span class="ficha-key">Carrera</span>
              <span class="ficha-val">{carreraCompletaRevision}</span>
              
              <span class="ficha-key">Empresa</span>
              <span class="ficha-val" style="font-weight:600; color:var(--text-primary);">
                {seleccionado.empresa || 'Sin asignar'}
              </span>
              
              <span class="ficha-key">Grupo</span>
              <span class="ficha-val ficha-mono">
                {seleccionado.nomenclatura || seleccionado.cuatrimestre || '—'}
              </span>
              
              <span class="ficha-key">Semana</span>
              <span class="ficha-val" style="font-weight:600;">
                Semana {detalle?.semana ?? seleccionado.semana}
                {#if detalle?.semana_inicio}
                  <span class="ficha-periodo">{formatFechaCivil(detalle.semana_inicio)} – {formatFechaCivil(detalle.semana_fin)}</span>
                {/if}
              </span>

              <span class="ficha-key">Fechas del reporte</span>
              {#if puedeRevisar}
                <div style="display:flex; gap:6px; flex-direction:column;">
                  <label class="sr-only" for="fecha-inicio-rev">Fecha de inicio del reporte</label>
                  <input id="fecha-inicio-rev" type="date" class="input-plain" style="padding: 4px 8px; font-size:12px;" bind:value={editFechaInicio} />
                  <label class="sr-only" for="fecha-fin-rev">Fecha de fin del reporte</label>
                  <input id="fecha-fin-rev" type="date" class="input-plain" style="padding: 4px 8px; font-size:12px;" bind:value={editFechaFin} />
                  <p class="hint-corr">Corregir las fechas no cambia la semana ni el período. Si el alumno entregó en la semana equivocada, recházalo con una observación.</p>
                </div>
              {:else if versionVigente}
                <span class="ficha-val ficha-periodo">
                  {formatFechaCivil(versionVigente.validada_inicio || versionVigente.fecha_inicio)} – {formatFechaCivil(versionVigente.validada_fin || versionVigente.fecha_fin)}
                </span>
              {/if}

              <span class="ficha-key">Entregado</span>
              <span class="ficha-val">{formatFecha(seleccionado.created_at)}</span>
            </div>
          </div>

          {#if detalle && detalle.versiones.length}
            <div class="historial-versiones">
              <p class="dato-label">Versiones y decisiones</p>
              <ul class="lista-versiones">
                {#each detalle.versiones as v (v.numero)}
                  <li>
                    <button class="btn-link" class:activo={v.numero === verVersion} aria-current={v.numero === verVersion ? 'true' : undefined}
                      on:click={() => { verVersion = v.numero; documentoVisor = 'original' }}>
                      Versión {v.numero}{v.numero === detalle.version_vigente ? ' (vigente)' : ''}
                    </button>
                    <span class="ver-estado">
                      {#if v.decision}{v.decision}{:else}Sin decidir{/if}
                      · recibida {formatFecha(v.recibido_en)}
                    </span>
                    {#if v.observacion}<p class="nota-texto">{v.observacion}</p>{/if}
                    {#each v.correcciones as c}
                      <p class="hint-corr">{ETIQUETA_CORRECCION[c.campo] || c.campo}: {c.previo} → {c.nuevo}</p>
                    {/each}
                    {#if v.firmado}<p class="hint-corr">Firmado ({v.firma_modo === 'celda' ? 'en la celda del tutor' : 'hoja adicional'}).</p>{/if}
                  </li>
                {/each}
              </ul>
            </div>
          {/if}

          {#if puedeRevisar}
            <div class="acciones-grupo">
              <div class="btn-decision-row">
                <button
                  class="btn-decision btn-aprobar"
                  class:activo={accion === 'aprobar'}
                  aria-pressed={accion === 'aprobar'}
                  disabled={!detalle.firma_registrada}
                  on:click={() => { accion = 'aprobar'; nota = '' }}
                >
                  ✓ Aprobar y firmar
                </button>
                <button
                  class="btn-decision btn-rechazar"
                  class:activo={accion === 'rechazar'}
                  aria-pressed={accion === 'rechazar'}
                  on:click={() => accion = 'rechazar'}
                >
                  ✕ Rechazar
                </button>
              </div>
              {#if !detalle.firma_registrada}
                <p class="hint-corr" style="margin-top:10px">Para aprobar primero registra tu firma académica en la bandeja.</p>
              {/if}

              {#if accion === 'rechazar' || accion === 'aprobar'}
                <div style="margin-top:14px; display: flex; flex-direction: column; gap: 4px;">
                  <label class="dato-label" for="observacion-rev">{accion === 'rechazar' ? 'Observación del rechazo (obligatoria)' : 'Retroalimentación opcional para el alumno'}</label>
                  <textarea
                    id="observacion-rev"
                    class="input-plain textarea-nota"
                    placeholder={accion === 'rechazar' ? 'Qué debe corregir el alumno…' : 'Comentario opcional…'}
                    rows="3"
                    maxlength="1000"
                    bind:value={nota}
                  ></textarea>
                  <div style="text-align: right; font-size: 11px; color: var(--text-disabled); font-weight: 500;">
                    {nota.length}/1000
                  </div>
                </div>
              {/if}

              {#if errorAccion}
                <p class="error-msg" style="margin-top:12px">{errorAccion}</p>
              {/if}
              {#if exito}
                <p class="exito-msg">{exito}</p>
              {/if}

              {#if !exito}
                <button
                  class="btn-primary"
                  style="width:100%; margin-top:14px"
                  on:click={enviarDecision}
                  disabled={enviando || !accion}
                >
                  {enviando ? 'Procesando…' : 'Enviar'}
                </button>
              {:else}
                <button class="btn-outline" style="width:100%; margin-top:12px" on:click={volverBandeja}>
                  Volver a la bandeja
                </button>
              {/if}
            </div>
          {:else}
            <div class="ya-revisado">
              {#if exito}<p class="exito-msg" role="status">{exito}</p>{/if}
              {#if detalle}
                <p>
                  {#if detalle.estado === 'Pendiente'}
                    Este reporte espera una nueva versión del alumno.
                  {:else}
                    La versión {detalle.version_vigente} fue
                    <span class="status-final" class:text-verde={detalle.estado === 'Aprobada'} class:text-rojo={detalle.estado === 'Rechazada'}>
                      {detalle.estado === 'Aprobada' ? 'aprobada' : 'rechazada'}
                    </span>.
                    {#if detalle.estado === 'Rechazada'}El alumno puede reenviar mientras la recepción del período esté abierta.{/if}
                  {/if}
                </p>
              {:else if !cargandoDetalle}
                <p class="error-msg">{errorAccion || 'No se pudo cargar el reporte.'}</p>
              {/if}
              <button class="btn-outline" style="margin-top:16px; width:100%" on:click={volverBandeja}>
                Regresar a la lista
              </button>
            </div>
          {/if}
        </div>
      </div>
    </div>

  {:else if vista === 'empresas'}
    <div class="page-wrap">
      <PageHeader 
        title="Gestión de Alumnos Duales" 
        subtitle="Asigna empresas y vincula roles a la comunidad DUAL" 
      />

      {#if loadingEmpresas}
        <LoadingSpinner />
      {:else}
        <div class="empresas-layout">
          <div class="card-seccion">
            <h2 class="seccion-title">Vincular Estudiante</h2>

            {#if errorAsignacion}
              <div class="error-msg">{errorAsignacion}</div>
            {/if}
            {#if exitoAsignacion}
              <div class="exito-msg">{exitoAsignacion}</div>
            {/if}

            <div class="nueva-empresa-row">
              <input
                class="input-plain"
                placeholder="Ingresa la matrícula…"
                bind:value={matriculaBusqueda}
                on:keydown={(e) => e.key === 'Enter' && buscarAlumno()}
              />
              <button 
                class="btn-primary" 
                style="white-space:nowrap; width:auto; padding:0 20px; height:42px;" 
                on:click={buscarAlumno} 
                disabled={loadingPreview}
              >
                {loadingPreview ? '...' : 'Buscar'}
              </button>
            </div>

            {#if alumnoPreview}
              <div class="ficha-alumno" style="margin:8px 0 0 0;">
                <p class="ficha-titulo font-semibold">Perfil Encontrado</p>
                <div class="ficha-grid">
                  <span class="ficha-key">Nombre</span>
                  <span class="ficha-val">{alumnoPreview.nombre}</span>
                  <span class="ficha-key">Carrera</span>
                  <span class="ficha-val">{carreraCompletaPreview}</span>
                  <span class="ficha-key">Grupo</span>
                  <span class="ficha-val ficha-mono">{alumnoPreview.nomenclatura || '—'}</span>
                  <span class="ficha-key">Estatus Dual</span>
                  <span class="ficha-val">
                    {alumnoPreview.es_alumno_dual ? '✅ Activo' : '❌ Inactivo'}
                  </span>
                  <span class="ficha-key">Empresa actual</span>
                  <span class="ficha-val" style="font-weight:600;">
                    {(alumnoPreview.es_alumno_dual && alumnoPreview.empresa) || 'Sin asignar'}
                  </span>
                </div>
              </div>

              <div class="field" style="margin-top:8px;">
                <label for="empresa-select">Asignar Unidad Económica</label>
                <select id="empresa-select" class="input-plain" bind:value={empresaSeleccionada} disabled={alumnoPreview.es_alumno_dual}>
                  <option value="">Selecciona una empresa corporativa</option>
                  {#each empresas as emp}
                    <option value={emp.id}>{emp.nombre}</option>
                  {/each}
                </select>
              </div>

              <div class="field">
                <label for="fecha-inicio-dual">Fecha real de inicio</label>
                <input id="fecha-inicio-dual" type="date" class="input-plain" bind:value={fechaInicioIncorporacion} disabled={alumnoPreview.es_alumno_dual} />
              </div>

              <div class="nueva-empresa-row">
                <input
                  class="input-plain"
                  placeholder="Añadir una nueva empresa al catálogo…"
                  bind:value={nuevaEmpresa}
                  on:keydown={(e) => e.key === 'Enter' && crearEmpresa()}
                />
                <button 
                  class="btn-outline" 
                  style="white-space:nowrap; height:42px;" 
                  on:click={crearEmpresa} 
                  disabled={!nuevaEmpresa.trim()}
                >
                  + Agregar
                </button>
              </div>

              <div style="display:flex; gap:10px; margin-top:12px">
                <button
                  class="btn-primary"
                  style="flex:1"
                  on:click={guardarAsignacion}
                  disabled={guardandoAsignacion || !empresaSeleccionada || alumnoPreview.es_alumno_dual || !fechaInicioIncorporacion}
                >
                  {guardandoAsignacion ? 'Guardando...' : alumnoPreview.es_alumno_dual ? 'Incorporación activa' : 'Activar Estatus Dual'}
                </button>
                {#if alumnoPreview.es_alumno_dual}
                  <button
                    class="btn-outline btn-danger"
                    style="flex:1"
                    on:click={() => confirmandoBaja = true}
                    disabled={guardandoAsignacion}
                  >
                    Baja del Programa
                  </button>
                {/if}
              </div>
              {#if confirmandoBaja}
                <div class="preview-individual" style="margin-top:12px">
                  <p><strong>Confirmar baja de Dual</strong></p>
                  <p>Finaliza obligaciones futuras desde la fecha indicada. La cuenta, los grupos por período y el expediente se conservan.</p>
                  <label for="fecha-baja-dual">Fecha de baja</label>
                  <input id="fecha-baja-dual" type="date" class="input-plain" bind:value={fechaBajaIncorporacion} />
                  <div style="display:flex;gap:8px"><button class="btn-primary" disabled={guardandoAsignacion} on:click={quitarDual}>Confirmar baja</button><button class="btn-outline" on:click={() => confirmandoBaja = false}>Cancelar</button></div>
                </div>
              {/if}
              {#if historialIncorporaciones.length > 0}
                <div style="margin-top:16px">
                  <h3 class="seccion-title">Historial de incorporación</h3>
                  <ul class="empresa-list">
                    {#each historialIncorporaciones as item}
                      <li class="empresa-item"><strong>{item.empresa || 'Sin empresa'}</strong><br />{item.fecha_inicio} — {item.fecha_baja || 'Activa'}</li>
                    {/each}
                  </ul>
                </div>
              {/if}
              {#if obligacionesAlumno.length > 0}
                <div style="margin-top:16px">
                  <h3 class="seccion-title">Semanas del alumno</h3>
                  <ul class="empresa-list">
                    {#each obligacionesAlumno as o (o.id)}
                      <li class="empresa-item">
                        <strong>Semana {o.ordinal}</strong>{#if o.parcial}&nbsp;(parcial){/if} — {ETIQUETA_ESTADO[o.estado]}<br />
                        {formatFechaCivil(o.inicio_efectivo)} – {formatFechaCivil(o.fin_efectivo)} · {o.periodo_label || 'Sin período'}
                      </li>
                    {/each}
                  </ul>
                </div>
              {/if}
            {/if}
          </div>

          <div class="card-seccion">
            <h2 class="seccion-title">Empresas en Convenio</h2>
            {#if empresas.length === 0}
              <p class="empty-msg">No hay entidades registradas en el catálogo actual.</p>
            {:else}
              <ul class="empresa-list">
                {#each empresas as emp}
                  <li class="empresa-item">
                    <span class="empresa-nombre">{emp.nombre}</span>
                  </li>
                {/each}
              </ul>
            {/if}
          </div>
        </div>
      {/if}
    </div>

  {:else if vista === 'expediente'}
    {#if !alumnoExpSeleccionado}
    <div class="page-wrap">
      <PageHeader
        title="Directorio de Alumnos"
        subtitle="Consulta y revisa expedientes de estudiantes DUAL"
      />

      <div class="reportes-card" style="padding: 16px;">
        <div style="display: flex; gap: 8px; margin-bottom: 12px; align-items: center;">
          {#if periodos.length > 0}
            <select class="input-plain input-sm" bind:value={periodoSeleccionadoExp} on:change={cambiarPeriodoExp} style="flex: 1">
              {#each periodos as p}
                <option value={p.cuatrimestre}>
                  {p.periodo_label || p.cuatrimestre}
                </option>
              {/each}
            </select>
          {:else}
            <input class="input-plain" placeholder="Cuatrimestre" bind:value={filtroCuatrimestreExp} style="flex: 1" />
          {/if}
          <input class="input-plain" placeholder="Buscar matrícula o nombre" bind:value={filtroBusquedaExp} style="flex: 1" />
          <button class="btn-primary" style="width: auto; padding: 0 16px;" on:click={cargarDirectorioExp}>Buscar</button>
        </div>
        {#if loadingAlumnos}
          <LoadingSpinner />
        {:else if alumnosExpFiltrados.length === 0}
          <EmptyState message="No se encontraron alumnos." />
        {:else}
          <div class="table-wrap" style="max-height: calc(100vh - 400px); overflow-y: auto;">
            <table class="reporte-table">
              <thead><tr><th>Matrícula</th><th>Nombre</th><th></th></tr></thead>
              <tbody>
                {#each alumnosExpFiltrados as a}
                  <tr>
                    <td class="td-matricula">{a.matricula}</td>
                    <td class="td-nombre">{a.nombre}</td>
                    <td style="text-align: right;">
                      <button class="btn-revisar" on:click={() => abrirExpAlumno(a)}>Ver</button>
                    </td>
                  </tr>
                {/each}
              </tbody>
            </table>
          </div>
          <p class="count-label">{alumnosExpFiltrados.length} alumno{alumnosExpFiltrados.length !== 1 ? 's' : ''}</p>
        {/if}
      </div>

    </div>
    {:else}
    <!-- EXPEDIENTE: layout idéntico a CoordinadorCarrera -->
    <div class="page-wrap expediente-page">
      <div class="expediente-topbar">
        <button class="btn-back" on:click={volverDirectorio}>
          <svg width="16" height="16" fill="none" stroke="currentColor" stroke-width="2.2" viewBox="0 0 24 24" style="display:inline; margin-right:4px; vertical-align:text-bottom;">
            <path stroke-linecap="round" stroke-linejoin="round" d="M10.5 19.5 L3 12 m0 0 l7.5-7.5 M3 12 h18" />
          </svg>
          Volver al directorio
        </button>
      </div>

      <div class="expediente-layout">
        <div class="ficha-card">
          <p class="ficha-titulo">Datos del alumno</p>
          <div class="ficha-divider"></div>
          <div class="ficha-grid">
            <span class="ficha-key">Nombre</span>
            <span class="ficha-val">{alumnoExpSeleccionado.nombre}</span>
            <span class="ficha-key">Matrícula</span>
            <span class="ficha-val ficha-mono">{alumnoExpSeleccionado.matricula}</span>
            <span class="ficha-key">Carrera</span>
            <span class="ficha-val">{carreraExpSel}</span>
            <span class="ficha-key">Grupo</span>
            <span class="ficha-val ficha-mono">{alumnoExpSeleccionado.nomenclatura || '—'}</span>
            <span class="ficha-key">Empresa</span>
            <span class="ficha-val bold-primary">{alumnoExpSeleccionado.empresa || 'Sin asignar'}</span>
            <span class="ficha-key">Turno</span>
            <span class="ficha-val">{alumnoExpSeleccionado.turno || '—'}</span>
          </div>

          {#if promedioExp}
            <div class="promedio-box">
              <p class="promedio-label">Promedio General</p>
              <p class="promedio-valor">{promedioExp}</p>
            </div>
          {/if}

          <div class="ficha-acciones">
            <button class="btn-primary" on:click={() => descargarCSVExp(alumnoExpSeleccionado.matricula)}>Exportar CSV</button>
            <button
              class="btn-outline"
              on:click={async () => {
                errorExp = ''
                try {
                  await api.dual.exportarZip(alumnoExpSeleccionado.matricula, periodoSeleccionadoExp || undefined)
                } catch (e) {
                  errorExp = e.message || 'Error al descargar ZIP'
                }
              }}
            >
              Descargar todos los PDFs (ZIP)
            </button>
          </div>
        </div>

        <div class="expediente-der">
          <div class="reportes-card" style="flex: 1; display: flex; flex-direction: column;">
            <h2 class="card-title">Reportes Aprobados</h2>

            {#if loadingReportesExp}
              <LoadingSpinner />
            {:else if errorExp}
              <p class="error-msg">{errorExp}</p>
            {:else if reportesExp.length === 0}
              <EmptyState message="Este alumno no tiene reportes aprobados aún." />
            {:else}
              <div class="expediente-split">
                <div class="expediente-tabla-col">
                  <div class="table-wrap">
                    <table class="reporte-table">
                      <thead>
                        <tr>
                          <th>Semana</th>
                          <th class="td-center">Calif.</th>
                          <th></th>
                        </tr>
                      </thead>
                      <tbody>
                        {#each reportesExp as r}
                          <tr
                            class:row-selected={pdfExpSeleccionado?.id === r.id}
                            on:click={() => pdfExpSeleccionado = r}
                            style="cursor: pointer;"
                          >
                            <td><span class="sem-txt">Semana {r.semana}</span></td>
                            <td class="td-cal">{r.calificacion_alumno}</td>
                            <td style="text-align: right;">
                              <span class="chip-reportes">Ver</span>
                            </td>
                          </tr>
                        {/each}
                      </tbody>
                    </table>
                  </div>
                  <p class="count-label">
                    {reportesExp.length} reporte{reportesExp.length !== 1 ? 's' : ''}
                  </p>
                </div>
                <div class="expediente-pdf-col">
                  <VisorPDF
                    url={pdfExpSeleccionado ? api.dual.reportePdfUrlCoordinador(pdfExpSeleccionado.id) : ''}
                    titulo={pdfExpSeleccionado ? `Semana ${pdfExpSeleccionado.semana}` : 'Selecciona un reporte'}
                  />
                </div>
              </div>
            {/if}
          </div>
        </div>
      </div>
    </div>
    {/if}
  {/if}

</div>

<style>
  .main-content { padding-top: 56px; background: var(--bg-page); min-height: 100vh; }
  .page-wrap { padding: 40px 24px; max-width: 1000px; margin: 0 auto; display: flex; flex-direction: column; gap: 20px; }

  .table-wrap { overflow-x: auto; border: 1px solid var(--border); border-radius: var(--radius-card); background: var(--bg-card); box-shadow: var(--shadow-card); }
  .reporte-table { width: 100%; border-collapse: collapse; font-size: 14px; }
  .reporte-table thead { background: var(--bg-page); }
  .reporte-table th { text-align: left; padding: 12px 18px; font-weight: 600; color: var(--text-disabled); font-size: 11px; text-transform: uppercase; letter-spacing: 0.05em; border-bottom: 1px solid var(--border); white-space: nowrap; }
  .reporte-table td { padding: 14px 18px; color: var(--text-secondary); border-bottom: 1px solid var(--border); vertical-align: middle; }
  .reporte-table tbody tr:last-child td { border-bottom: none; }
  .reporte-table tbody tr:hover { background: var(--orange-light); }
  .row-pendiente { border-left: 4px solid var(--orange); }

  .td-matricula { font-family: monospace; font-weight: 600; color: var(--text-primary); }
  .td-nombre { font-weight: 600; color: var(--text-primary); }
  .td-cal { font-weight: 700; color: var(--orange); font-size: 15px; }
  .td-fecha { color: var(--text-secondary); font-size: 13px; white-space: nowrap; }

  .btn-revisar { background: transparent; border: 1.5px solid var(--border-input); border-radius: 8px; padding: 6px 14px; font-size: 13px; font-weight: 600; color: var(--text-primary); cursor: pointer; transition: all 0.2s ease; }
  .btn-revisar:hover { border-color: var(--orange); color: var(--orange); background: var(--orange-light); }

  .count-label { font-size: 12px; color: var(--text-disabled); text-align: right; margin-top: 4px; font-weight: 500; }

  .revision-wrap { display: flex; flex-direction: column; height: calc(100vh - 56px); overflow: hidden; background: var(--bg-page); }
  .revision-topbar { display: flex; align-items: center; justify-content: space-between; padding: 14px 24px; background: var(--bg-card); border-bottom: 1px solid var(--border); box-shadow: 0 1px 2px rgba(0,0,0,0.02); }
  
  .btn-back { background: none; border: none; cursor: pointer; font-family: var(--font); font-size: 14px; font-weight: 600; color: var(--text-secondary); display: flex; align-items: center; transition: color 0.15s; }
  .btn-back:hover { color: var(--orange); }
  
  .split-layout { display: grid; grid-template-columns: 1fr 360px; flex: 1; overflow: hidden; }
  .panel-pdf { display: flex; flex-direction: column; border-right: 1px solid var(--border); overflow: hidden; background: #1e293b; min-height: 0; }
  .panel-label { font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; color: var(--text-disabled); padding: 10px 20px; border-bottom: 1px solid var(--border); background: var(--bg-page); }
  .pdf-iframe { flex: 1; width: 100%; border: none; background: #fff; }
  .link-externo { display: block; padding: 10px 20px; font-size: 13px; font-weight: 500; color: var(--orange); text-decoration: none; border-top: 1px solid var(--border); background: var(--bg-card); transition: background 0.15s; }
  .link-externo:hover { background: var(--orange-light); }
  .no-pdf { display: flex; align-items: center; justify-content: center; flex: 1; color: #94a3b8; font-size: 14px; font-style: italic; }
  
  .panel-acciones { display: flex; flex-direction: column; overflow-y: auto; background: var(--bg-card); gap: 1px; }

  .dato-cal { margin: 20px 20px 0; padding: 16px; background: rgba(249, 115, 22, 0.06); border: 1px solid rgba(249, 115, 22, 0.15); border-radius: 12px; }
  .dato-label { font-size: 11px; font-weight: 700; color: var(--text-disabled); margin: 0 0 4px; text-transform: uppercase; letter-spacing: 0.05em; }
  .dato-valor { font-size: 36px; font-weight: 800; color: var(--orange); margin: 0; line-height: 1; letter-spacing: -0.02em; }

  .ficha-alumno { margin: 16px 20px 0; padding: 16px; border: 1px solid var(--border); border-radius: 12px; background: var(--bg-page); }
  .ficha-titulo { font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; color: var(--text-disabled); margin: 0 0 12px; }
  .ficha-grid { display: grid; grid-template-columns: auto 1fr; gap: 8px 16px; align-items: baseline; }
  .ficha-key { font-size: 11px; font-weight: 600; color: var(--text-disabled); text-transform: uppercase; }
  .ficha-val { font-size: 13px; font-weight: 500; color: var(--text-secondary); word-break: break-word; }
  .ficha-mono { font-family: monospace; font-weight: 600; color: var(--text-primary); }
  .ficha-periodo { font-weight: 600; white-space: normal; line-height: 1.5; }

  .nota-previa { margin: 16px 20px 0; padding: 14px; background: rgba(249, 115, 22, 0.04); border: 1px solid var(--border); border-radius: 12px; }
  .nota-texto { font-size: 13px; color: var(--text-secondary); margin: 4px 0 0; line-height: 1.5; }
  .aviso-periodo { margin: 0 0 12px; padding: 10px 14px; font-size: 13px; color: var(--text-primary); border: 1px solid var(--border); border-left: 3px solid var(--orange); border-radius: 8px; background: var(--bg-card); }
  .sr-only { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0 0 0 0); white-space: nowrap; }
  .hint-corr { margin: 4px 0 0; font-size: 11px; line-height: 1.4; color: var(--orange); }
  .tabs-doc { display: flex; gap: 6px; padding: 8px 0; flex-wrap: wrap; }
  .tab-doc { background: var(--bg-card); border: 1px solid var(--border); border-radius: 8px; padding: 6px 12px; font: inherit; font-size: 12px; font-weight: 600; color: var(--text-secondary); cursor: pointer; }
  .tab-doc.activo { border-color: var(--orange); color: var(--orange); }
  .historial-versiones { padding: 16px 20px; border-top: 1px solid var(--border); }
  .lista-versiones { list-style: none; margin: 8px 0 0; padding: 0; display: flex; flex-direction: column; gap: 10px; }
  .lista-versiones .btn-link { background: none; border: none; padding: 0; color: var(--orange); font: inherit; font-weight: 600; cursor: pointer; text-decoration: underline; }
  .lista-versiones .btn-link.activo { color: var(--text-primary); text-decoration: none; cursor: default; }
  .ver-estado { display: block; font-size: 12px; color: var(--text-secondary); margin-top: 2px; }
  .btn-decision:disabled { opacity: 0.5; cursor: not-allowed; }

  .acciones-grupo { padding: 20px; margin-top: auto; }
  .btn-decision-row { display: flex; gap: 10px; }
  .btn-decision { flex: 1; padding: 12px 8px; border-radius: 8px; font-size: 13px; font-weight: 700; cursor: pointer; transition: all 0.15s ease; border: 1.5px solid transparent; text-align: center; }
  .btn-aprobar { background: rgba(34, 197, 94, 0.08); color: var(--success); border-color: rgba(34, 197, 94, 0.2); }
  .btn-aprobar:hover, .btn-aprobar.activo { background: var(--success); color: white; border-color: var(--success); }
  .btn-rechazar { background: rgba(239, 68, 68, 0.08); color: var(--error); border-color: rgba(239, 68, 68, 0.2); }
  .btn-rechazar:hover, .btn-rechazar.activo { background: var(--error); color: white; border-color: var(--error); }
  .textarea-nota { width: 100%; min-height: 84px; resize: none; margin-top: 4px; }
  .exito-msg { color: var(--success); background: rgba(34, 197, 94, 0.08); border: 1px solid rgba(34, 197, 94, 0.2); border-radius: 8px; padding: 10px 14px; font-size: 13px; margin-top: 12px; font-weight: 500; text-align: center; }
  
  .ya-revisado { padding: 24px 20px; font-size: 14px; color: var(--text-secondary); text-align: center; }
  .status-final { font-weight: 700; text-transform: uppercase; letter-spacing: 0.02em; }
  .text-verde { color: var(--success); }
  .text-rojo { color: var(--error); }
  
  .btn-danger { color: var(--error) !important; border-color: rgba(239, 68, 68, 0.3) !important; }
  .btn-danger:hover { background: var(--error) !important; color: white !important; border-color: var(--error) !important; }

  .empresas-layout { display: grid; grid-template-columns: 1fr 1fr; gap: 24px; margin-top: 8px; }
  .card-seccion { background: var(--bg-card); border-radius: var(--radius-card); box-shadow: var(--shadow-card); padding: 28px; display: flex; flex-direction: column; gap: 16px; border: 1px solid var(--border); }
  .seccion-title { font-size: 15px; font-weight: 700; color: var(--text-primary); margin: 0; }
  
  .field { display: flex; flex-direction: column; gap: 6px; }
  .field label { font-size: 13px; font-weight: 600; color: var(--text-secondary); }
  
  .nueva-empresa-row { display: flex; gap: 10px; align-items: center; width: 100%; }
  
  .empresa-list { list-style: none; padding: 0; margin: 0; display: flex; flex-direction: column; gap: 8px; overflow-y: auto; max-height: 380px; }
  .empresa-item { padding: 12px 16px; border: 1px solid var(--border); border-radius: 8px; background: var(--bg-page); }
  .empresa-nombre { font-size: 14px; font-weight: 600; color: var(--text-primary); }
  .empty-msg { font-size: 13px; color: var(--text-disabled); font-style: italic; margin: 0; }

  /* Not-submitted status badges */
  .badge-overdue {
    display: inline-block;
    background: rgba(239, 68, 68, 0.08);
    color: var(--error);
    font-weight: 700;
    font-size: 12px;
    border-radius: 6px;
    padding: 3px 10px;
    border: 1px solid rgba(239, 68, 68, 0.2);
  }
  .badge-pending-filter {
    display: inline-block;
    background: rgba(249, 115, 22, 0.08);
    color: var(--orange);
    font-weight: 700;
    font-size: 12px;
    border-radius: 6px;
    padding: 3px 10px;
    border: 1px solid rgba(249, 115, 22, 0.2);
  }

  .expediente-layout { display: grid; grid-template-columns: 320px 1fr; gap: 24px; align-items: start; }
  .expediente-topbar { margin-bottom: 16px; }

  .expediente-page { max-width: 1200px; }
  .expediente-split { display: grid; grid-template-columns: 260px 1fr; gap: 0; flex: 1; min-height: 0; border: 1px solid var(--border); border-radius: var(--radius-card); overflow: hidden; }
  .expediente-tabla-col { border-right: 1px solid var(--border); overflow-y: auto; background: var(--bg-card); }
  .expediente-pdf-col { min-height: 0; display: flex; flex: 1; }
  .expediente-pdf-col :global(.visor-wrap) { border-radius: 0; border: none; width: 100%; }
  .row-selected { background: var(--orange-light) !important; }

  .expediente-der { flex: 1; min-width: 0; }

  /* Ficha del alumno (compartido con CoordinadorCarrera) */
  .ficha-card { background: var(--bg-card); border-radius: var(--radius-card); border: 1px solid var(--border); box-shadow: var(--shadow-card); padding: 24px; display: flex; flex-direction: column; gap: 16px; position: sticky; top: calc(56px + 24px); }
  .ficha-titulo { font-size: 12px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; color: var(--text-disabled); margin: 0; }
  .ficha-divider { height: 1px; background: var(--border); width: 100%; margin-top: -4px; }
  .ficha-grid { display: grid; grid-template-columns: auto 1fr; gap: 10px 16px; align-items: baseline; }
  .ficha-key { font-size: 11px; font-weight: 600; color: var(--text-disabled); text-transform: uppercase; letter-spacing: 0.02em; }
  .ficha-val { font-size: 14px; font-weight: 500; color: var(--text-secondary); word-break: break-word; }
  .ficha-mono { font-family: monospace; font-weight: 600; color: var(--text-primary); }
  .bold-primary { color: var(--text-primary); font-weight: 600; }

  .promedio-box { background: rgba(249, 115, 22, 0.06); border: 1px solid rgba(249, 115, 22, 0.15); border-radius: 12px; padding: 14px; text-align: center; }
  .promedio-label { font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; color: var(--orange); margin: 0 0 4px; }
  .promedio-valor { font-size: 32px; font-weight: 800; color: var(--orange); margin: 0; line-height: 1; letter-spacing: -0.03em; }

  .ficha-acciones { display: flex; flex-direction: column; gap: 10px; margin-top: 4px; }

  .sem-txt { font-weight: 600; color: var(--text-primary); }
  .chip-reportes { display: inline-block; background: rgba(249, 115, 22, 0.08); color: var(--orange); font-weight: 700; font-size: 12px; border-radius: 6px; padding: 2px 10px; border: 1px solid rgba(249, 115, 22, 0.2); }

  .exito-msg { color: var(--success); background: rgba(34, 197, 94, 0.08); border: 1px solid rgba(34, 197, 94, 0.2); border-radius: 8px; padding: 10px 14px; font-size: 13px; font-weight: 500; }

  @media (max-width: 768px) {
    .page-wrap { padding: 24px 16px; }
    .split-layout { grid-template-columns: 1fr; }
    .panel-pdf { height: 300px; border-right: none; border-bottom: 1px solid var(--border); }
    .empresas-layout { grid-template-columns: 1fr; }
    .expediente-layout { grid-template-columns: 1fr; }
    .ficha-card { position: static; }
    .expediente-split { grid-template-columns: 1fr; }
    .expediente-pdf-col { min-height: 0; flex: 1; }
    .reporte-table th, .reporte-table td { padding: 10px 12px; font-size: 13px; }
  }
</style>
