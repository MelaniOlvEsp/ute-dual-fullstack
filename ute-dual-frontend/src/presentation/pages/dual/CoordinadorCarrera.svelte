<script>
  // src/routes/dual/CoordinadorCarrera.svelte
  import { onMount } from 'svelte'
  import { navigate, useLocation } from 'svelte-routing'
  import { get } from 'svelte/store'
  import { isAuthenticated, isCoordinadorCarrera, isTutorAcademico } from '../../stores/auth.js'
  import { api } from '../../../composition/api.js'
  import Navbar from '../../components/layout/Navbar.svelte'
  import FiltrosBarra from '../../components/shared/FiltrosBarra.svelte'
  import LoadingSpinner from '../../components/ui/LoadingSpinner.svelte'
  import EmptyState from '../../components/ui/EmptyState.svelte'
  import ExpedienteAlumno from '../../components/dual/ExpedienteAlumno.svelte'
  import ArchivoDepuracion from '../../components/dual/ArchivoDepuracion.svelte'
  import { SITUACIONES, paginacion } from '../../../domain/dual/expediente.js'
  import { formatFecha, formatFechaCivil } from '../../utils/formatters.js'

  const location = useLocation()
  let vista = 'directorio'

  $: {
    const queryVista = new URLSearchParams($location.search).get('vista')
    if (queryVista === 'grupos' && !$isTutorAcademico) {
      navigate('/dual/carrera', { replace: true })
    } else if (queryVista === 'grupos' && vista !== 'grupos') {
      vista = 'grupos'
      cargarGrupos()
    } else if (!queryVista && vista === 'grupos') {
      vista = 'directorio'
      cargarAlumnos()
    }
  }

  // Directorio paginado por servidor (C08): incluye a los dados de baja (RN-29).
  const LIMITE = 50
  let alumnos = []
  let total = 0
  let desplazamiento = 0
  let loading = true
  let error = ''
  let filtroCuatrimestre = ''
  let filtroGrupo = ''
  let filtroBusqueda = ''
  let filtroCarrera = ''
  let filtroEstado = ''
  let filtroSituacion = 'todos'

  let alumnoSeleccionado = null
  let expedienteDatos = null
  let loadingExpediente = false
  let errorExpediente = ''
  let periodos = []
  let periodoSeleccionado = ''
  let periodoGrupoId = ''
  let carrerasInstitucionales = []

  // Paquete de archivo por carrera y período finalizado (DP-14); solo lo genera el tutor.
  let periodosFinalizados = []
  let paqueteCarrera = ''
  let paquetePeriodo = ''
  let generandoPaquete = false
  let errorPaquete = ''

  let formGrupo = {
    carrera: 'ING.NME TEC DE LA INFORMACIÓN E INNOVACION DIGITAL',
    cuatrimestre: 5,
    modalidad: 'bis',
    letra: 'A',
    turno: 'Matutino'
  }
  let grupoCreado = null
  let guardandoGrupo = false
  let errorGrupo = ''
  
  let archivoCSV = null
  let subiendoCSV = false
  let errorCSV = ''
  let exitoCSV = ''
  let gruposExistentes = []
  let loadingGrupos = false
  let filtroCarreraGrupos = ''
  let grupoSeleccionado = null

  onMount(async () => {
    if (!get(isAuthenticated) || !get(isCoordinadorCarrera)) {
      navigate('/login', { replace: true })
      return
    }
    await Promise.all([cargarAlumnos(), cargarPeriodos(), cargarCarreras(), cargarPeriodosFinalizados()])
  })

  async function cargarPeriodosFinalizados() {
    try {
      periodosFinalizados = (await api.dual.periodosEstado()).filter(p => p.evaluacion === 'finalizada')
      if (periodosFinalizados.length && !paquetePeriodo) paquetePeriodo = periodosFinalizados[0].id
    } catch {
      periodosFinalizados = []
    }
  }

  async function descargarPaqueteCarrera() {
    errorPaquete = ''
    if (!paqueteCarrera || !paquetePeriodo) {
      errorPaquete = 'Selecciona la carrera y el período.'
      return
    }
    const periodo = periodosFinalizados.find(p => p.id === paquetePeriodo)
    generandoPaquete = true
    try {
      await api.dual.downloadCareerPackage(paqueteCarrera, paquetePeriodo, periodo?.periodo_label || 'periodo')
    } catch (e) {
      errorPaquete = e.message || 'No se pudo generar el paquete.'
    } finally {
      generandoPaquete = false
    }
  }

  async function cargarCarreras() {
    try {
      carrerasInstitucionales = await api.dual.listarCarreras()
    } catch {
      carrerasInstitucionales = [
        { codigo: 'TII', nombre: 'ING.NME TEC DE LA INFORMACIÓN E INNOVACION DIGITAL' },
        { codigo: 'LOG', nombre: 'ING. NME LOGISTICA' },
        { codigo: 'MER', nombre: 'LIC. NME MERCADOTECNIA' }
      ]
    }
  }

  async function cargarPeriodos() {
    try {
      periodos = await api.dual.periodos()
      if (periodos.length && !periodoSeleccionado) {
        periodoSeleccionado = periodos[0].cuatrimestre
      }
      if (!periodoGrupoId) {
        periodoGrupoId = periodos.find(p => p.id)?.id || ''
      }
    } catch (e) {
      // Silencioso — el dropdown simplemente no aparecerá
      periodos = []
    }
  }

  async function cargarAlumnos(reiniciar = true) {
    if (reiniciar) desplazamiento = 0
    loading = true
    error = ''
    try {
      const params = new URLSearchParams()
      if (filtroCuatrimestre) params.append('cuatrimestre', filtroCuatrimestre)
      if (filtroGrupo) params.append('grupo', filtroGrupo)
      if (filtroBusqueda.trim()) params.append('q', filtroBusqueda.trim())
      params.append('situacion', filtroSituacion)
      params.append('limite', String(LIMITE))
      params.append('desplazamiento', String(desplazamiento))
      const respuesta = await api.dual.listarAlumnos(params.toString())
      alumnos = respuesta.items
      total = respuesta.total
    } catch (e) {
      error = e.message || 'Error al cargar alumnos.'
    } finally {
      loading = false
    }
  }

  function irA(delta) {
    desplazamiento = Math.max(0, desplazamiento + delta * LIMITE)
    cargarAlumnos(false)
  }

  $: pagina = paginacion({ total, limite: LIMITE, desplazamiento })

  // La nomenclatura institucional no incluye el ciclo de ingreso: dos grupos de ciclos
  // distintos pueden compartirla, así que los selectores lo muestran como texto aparte.
  const etiquetaGrupo = (g) => (g.ciclo_ingreso ? `${g.nomenclatura} · ingreso ${g.ciclo_ingreso}` : g.nomenclatura)

  $: carreras = [...new Set(alumnos.map(a => a.carrera).filter(Boolean))].sort()
  $: grupos = [...new Set(alumnos.map(a => a.nomenclatura || a.grupo).filter(Boolean))].sort()

  // La búsqueda por nombre o matrícula la hace el servidor; aquí solo se filtra por carrera la página visible.
  $: alumnosFiltrados = alumnos.filter(a => {
    const matchBusqueda = true
    const carreraStr = filtroCarrera.toLowerCase()
    const matchCarrera = filtroCarrera
      ? (a.carrera && a.carrera.toLowerCase() === carreraStr) || 
        (a.nomenclatura && a.nomenclatura.toLowerCase().includes(carreraStr))
      : true
      
    return matchBusqueda && matchCarrera
  })

  async function abrirExpediente(alumno) {
    alumnoSeleccionado = alumno
    expedienteDatos = null
    errorExpediente = ''
    loadingExpediente = true
    vista = 'expediente'
    try {
      expedienteDatos = await api.dual.expedienteAlumno(alumno.matricula)
    } catch (e) {
      errorExpediente = e.message || 'Error al cargar el expediente.'
    } finally {
      loadingExpediente = false
    }
  }

  function volverDirectorio() {
    alumnoSeleccionado = null
    expedienteDatos = null
    vista = 'directorio'
    navigate('/dual/carrera', { replace: true })
  }

  async function registrarGrupo() {
    guardandoGrupo = true
    errorGrupo = ''
    grupoCreado = null
    try {
      const res = await api.dual.crearGrupo(formGrupo)
      grupoCreado = res
    } catch (e) {
      errorGrupo = e.message || 'Error de integridad al registrar grupo.'
    } finally {
      guardandoGrupo = false
    }
  }

  function descargarPlantillaCSV() {
    const header = "matricula,nombre\n"
    const mockRow = "302410000,Ejemplo Apellido"
    const csvContent = `data:text/csv;charset=utf-8,${header}${mockRow}`
    
    const encodedUri = encodeURI(csvContent)
    const link = document.createElement("a")
    link.setAttribute("href", encodedUri)
    link.setAttribute("download", "plantilla_alumnos.csv")
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
  }

  let resultadoCSV = null 

  function limpiarInputCSV() {
    archivoCSV = null
    resultadoCSV = null
    errorCSV = ''
    if (inputFileRef) inputFileRef.value = ""
  }

  async function procesarCargaMasiva() {
    if (!archivoCSV || !grupoCreado || !periodoGrupoId) return
    subiendoCSV = true
    errorCSV = ''
    resultadoCSV = null

    try {
      const fd = new FormData()
      fd.append('file', archivoCSV)
      fd.append('periodo_id', periodoGrupoId)
      const respuesta = await api.dual.previewAlumnosCSV(grupoCreado.id, fd)

      resultadoCSV = {
        preview: true,
        validos: respuesta.validos || [],
        repetidos: respuesta.repetidos || [],
        errores: respuesta.errores || [],
        puedeAplicar: respuesta.puede_aplicar,
        grupo: respuesta.grupo,
        periodo: respuesta.periodo
      }
    } catch (e) {
      errorCSV = e.message || 'Error de I/O al procesar el archivo.'
    } finally {
      subiendoCSV = false
    }
  }

  async function confirmarCargaMasiva() {
    if (!archivoCSV || !grupoCreado || !periodoGrupoId || !resultadoCSV?.puedeAplicar) return
    subiendoCSV = true
    errorCSV = ''
    try {
      const fd = new FormData()
      fd.append('file', archivoCSV)
      fd.append('periodo_id', periodoGrupoId)
      const respuesta = await api.dual.subirAlumnosCSV(grupoCreado.id, fd)
      resultadoCSV = { ...respuesta, preview: false }
      archivoCSV = null
      if (inputFileRef) inputFileRef.value = ''
      await Promise.all([cargarAlumnos(), cargarGrupos()])
    } catch (e) {
      errorCSV = e.message || 'No se aplicó el lote.'
    } finally {
      subiendoCSV = false
    }
  }

  async function cargarGrupos() {
    loadingGrupos = true
    try {
      gruposExistentes = await api.dual.listarGrupos(filtroCarreraGrupos || null)
    } catch (e) {
      gruposExistentes = []
    } finally {
      loadingGrupos = false
    }
  }

  function seleccionarGrupo(grupo) {
    grupoCreado = grupo
    grupoSeleccionado = grupo
    errorGrupo = ''
    limpiarInputCSV()
  }

  let inputFileRef = null
  let filasAlumnos = [{ matricula: '', nombre: '' }]
  let errorIndividual = ''
  let previewIndividual = null  
  let modalEliminar = null      
  let procesandoIndividual = false
  let promocion = { grupo_origen_id: '', periodo_origen_id: '', grupo_destino_id: '', periodo_destino_id: '' }
  let previewPromocion = null
  let errorPromocion = ''
  let procesandoPromocion = false

  function agregarFila() {
    filasAlumnos = [...filasAlumnos, { matricula: '', nombre: '' }]
  }

  function resetIndividual() {
    filasAlumnos = [{ matricula: '', nombre: '' }]
    errorIndividual = ''
    previewIndividual = null
  }

  function validarFilasIndividuales(soloMatricula = false) {
    for (const f of filasAlumnos) {
      if (!f.matricula) return 'La matrícula es obligatoria.'
      if (!soloMatricula && !f.nombre.trim()) return 'El nombre es obligatorio.'
      if (!/^\d{9}$/.test(f.matricula)) return `Matrícula inválida: ${f.matricula} (deben ser 9 dígitos).`
    }
    return null
  }

  function prepararAccion(accion) {
    errorIndividual = ''
    const err = validarFilasIndividuales(false)
    if (err) { errorIndividual = err; return }
    if (accion === 'agregar' && !grupoCreado) {
      errorIndividual = 'Selecciona un grupo activo para agregar alumnos.'
      return
    }
    if (accion === 'agregar' && !periodoGrupoId) {
      errorIndividual = 'Selecciona el período académico de la pertenencia.'
      return
    }
    previewIndividual = { accion, filas: filasAlumnos.map(f => ({ ...f })) }
  }

  function prepararEliminar() {
    errorIndividual = ''
    if (filasAlumnos.length !== 1 || !filasAlumnos[0].matricula) {
      errorIndividual = 'Ingresa una sola matrícula para desactivar su acceso.'
      return
    }
    if (!/^\d{9}$/.test(filasAlumnos[0].matricula)) {
      errorIndividual = 'Matrícula inválida (deben ser 9 dígitos).'
      return
    }
    modalEliminar = { matricula: filasAlumnos[0].matricula, nombre: filasAlumnos[0].nombre }
  }

  async function confirmarAccion() {
    if (!previewIndividual) return
    procesandoIndividual = true
    errorIndividual = ''
    try {
      if (previewIndividual.accion === 'agregar') {
        for (const f of previewIndividual.filas) {
          await api.dual.agregarAlumno(grupoCreado.id, { ...f, periodo_id: periodoGrupoId })
        }
      } else if (previewIndividual.accion === 'actualizar') {
        for (const f of previewIndividual.filas) {
          await api.dual.actualizarAlumno(f.matricula, { nombre: f.nombre })
        }
      }
      resetIndividual()
      await cargarGrupos()
    } catch (e) {
      errorIndividual = e.message || 'Error al procesar la operación.'
    } finally {
      procesandoIndividual = false
    }
  }

  async function confirmarEliminar() {
    if (!modalEliminar) return
    procesandoIndividual = true
    errorIndividual = ''
    try {
      await api.dual.eliminarAlumno(modalEliminar.matricula)
      modalEliminar = null
      resetIndividual()
      await cargarGrupos()
    } catch (e) {
      errorIndividual = e.message || 'Error al desactivar el acceso.'
      modalEliminar = null
    } finally {
      procesandoIndividual = false
    }
  }

  async function revisarPromocion() {
    errorPromocion = ''
    previewPromocion = null
    if (Object.values(promocion).some(value => !value)) {
      errorPromocion = 'Selecciona grupo y período de origen y destino.'
      return
    }
    if (promocion.periodo_origen_id === promocion.periodo_destino_id) {
      errorPromocion = 'El período destino debe ser diferente al período origen.'
      return
    }
    procesandoPromocion = true
    try {
      previewPromocion = await api.dual.previewPromocion(promocion)
    } catch (e) {
      errorPromocion = e.message || 'No se pudo preparar la promoción.'
    } finally {
      procesandoPromocion = false
    }
  }

  async function confirmarPromocion() {
    if (!previewPromocion?.puede_aplicar) return
    procesandoPromocion = true
    errorPromocion = ''
    try {
      const result = await api.dual.aplicarPromocion(promocion)
      previewPromocion = { aplicado: true, validos: result.promovidos || [], repetidos: result.repetidos || [], errores: [] }
      await cargarGrupos()
    } catch (e) {
      errorPromocion = e.message || 'La promoción no se aplicó.'
    } finally {
      procesandoPromocion = false
    }
  }
</script>

<svelte:head>
  <title>Coordinador de Carrera | Portal UTE</title>
</svelte:head>

<Navbar />

<main class="main-content">

  {#if vista === 'directorio'}
    <h1 class="sr-only">Expedientes de alumnos</h1>
    <div class="page-wrap">
      <FiltrosBarra
        mostrarEstado={false}
        mostrarCarrera={true}
        mostrarGrupo={true}
        {grupos}
        {carreras}
        bind:filtroBusqueda
        bind:filtroGrupo
        bind:filtroCarrera
        bind:filtroEstado
        on:buscar={() => cargarAlumnos()}
      />

      <div class="filtros-extra">
        <div class="campo-filtro">
          <label for="filtro-periodo-dir">Período</label>
          <select id="filtro-periodo-dir" class="input-plain input-sm" bind:value={filtroCuatrimestre} on:change={() => cargarAlumnos()}>
            <option value="">Todos los períodos</option>
            {#each periodos as p}
              <option value={p.cuatrimestre}>{p.periodo_label || p.cuatrimestre}</option>
            {/each}
          </select>
        </div>
        <div class="campo-filtro">
          <label for="filtro-situacion-dir">Situación</label>
          <select id="filtro-situacion-dir" class="input-plain input-sm" bind:value={filtroSituacion} on:change={() => cargarAlumnos()}>
            {#each SITUACIONES as s}<option value={s.valor}>{s.etiqueta}</option>{/each}
          </select>
        </div>
      </div>

      {#if $isTutorAcademico}
        <section class="paquete-carrera" aria-labelledby="paquete-carrera-titulo">
          <h2 id="paquete-carrera-titulo" class="paquete-titulo">Paquete de archivo por carrera</h2>
          <p class="paquete-texto">Con el período finalizado, descarga un ZIP con los PDF firmados y originales aprobados de la carrera, con manifiesto y hashes, para guardarlo fuera del sistema.</p>
          {#if periodosFinalizados.length === 0}
            <p class="paquete-texto">Aún no hay períodos con la evaluación finalizada.</p>
          {:else}
            <div class="paquete-fila">
              <div class="campo-filtro">
                <label for="paquete-carrera-sel">Carrera</label>
                <select id="paquete-carrera-sel" class="input-plain input-sm" bind:value={paqueteCarrera}>
                  <option value="">Selecciona</option>
                  {#each carrerasInstitucionales as c}<option value={c.codigo}>{c.nombre}</option>{/each}
                </select>
              </div>
              <div class="campo-filtro">
                <label for="paquete-periodo-sel">Período finalizado</label>
                <select id="paquete-periodo-sel" class="input-plain input-sm" bind:value={paquetePeriodo}>
                  {#each periodosFinalizados as p}<option value={p.id}>{p.periodo_label}</option>{/each}
                </select>
              </div>
              <button class="btn-outline" disabled={generandoPaquete} on:click={descargarPaqueteCarrera}>
                {generandoPaquete ? 'Generando paquete…' : 'Descargar paquete (ZIP)'}
              </button>
            </div>
          {/if}
          {#if errorPaquete}<p class="error-msg" role="alert">{errorPaquete}</p>{/if}
        </section>
      {/if}

      <ArchivoDepuracion periodos={periodosFinalizados} />

      {#if loading}
        <LoadingSpinner />
      {:else if error}
        <p class="error-msg">{error}</p>
      {:else if alumnosFiltrados.length === 0}
        <EmptyState message="No hay alumnos duales con los filtros seleccionados." />
      {:else}
        <div class="table-wrap" role="region" tabindex="0" aria-label="Directorio de alumnos">
          <table class="tabla">
            <thead>
              <tr>
                <th>Matrícula</th>
                <th>Nombre</th>
                <th>Grupo</th>
                <th>Empresa</th>
                <th class="td-center">Aprobados</th>
                <th class="td-center">Promedio</th>
                <th class="col-accion"><span class="sr-only">Acciones</span></th>
              </tr>
            </thead>
            <tbody>
              {#each alumnosFiltrados as a (a.matricula)}
                <tr>
                  <td class="td-matricula">{a.matricula}</td>
                  <td class="td-nombre">
                    {a.nombre}
                    {#if !a.activo}<span class="chip-baja" title="Incorporación dada de baja; el expediente se conserva">Baja{#if a.fecha_baja}&nbsp;{formatFechaCivil(a.fecha_baja)}{/if}</span>{/if}
                  </td>
                  <td class="td-grupo">{a.nomenclatura || '—'}</td>
                  <td>{a.empresa || 'Sin asignar'}</td>
                  <td class="td-center">{a.reportes_aprobados}</td>
                  <td class="td-center">{a.promedio ?? 'Sin calificación'}</td>
                  <td class="col-accion" style="text-align: right;">
                    <button class="btn-ver" on:click={() => abrirExpediente(a)}>
                      Ver Expediente
                    </button>
                  </td>
                </tr>
              {/each}
            </tbody>
          </table>
        </div>
        <nav class="paginacion" aria-label="Paginación del directorio">
          <span class="count-label" role="status">{pagina.desde}–{pagina.hasta} de {pagina.total} alumnos</span>
          <button class="btn-outline" disabled={!pagina.hayAnterior || loading} on:click={() => irA(-1)}>Anterior</button>
          <button class="btn-outline" disabled={!pagina.haySiguiente || loading} on:click={() => irA(1)}>Siguiente</button>
        </nav>
      {/if}
    </div>

  {:else if vista === 'grupos' && $isTutorAcademico}
    <h1 class="sr-only">Alumnos y grupos</h1>
    <div class="page-wrap-grupos">

      <div class="grupos-topbar">
        <button class="btn-back" on:click={volverDirectorio}>
          <svg width="16" height="16" fill="none" stroke="currentColor" stroke-width="2.2" viewBox="0 0 24 24" style="display:inline; margin-right:4px; vertical-align:text-bottom;">
            <path stroke-linecap="round" stroke-linejoin="round" d="M10.5 19.5 L3 12 m0 0 l7.5-7.5 M3 12 h18" />
          </svg>
          Volver al directorio
        </button>
      </div>

      <div class="grupos-layout">

        <div class="grupos-col-izq">

          <div class="grupos-selector-card">
            <div class="field">
              <label class="grupos-barra-label" for="filtro-carrera-grupos">Carrera</label>
              <select id="filtro-carrera-grupos" class="input-plain input-sm" bind:value={filtroCarreraGrupos} on:change={cargarGrupos}>
                <option value="">Todas</option>
                {#each carrerasInstitucionales as carrera}
                  <option value={carrera.nombre}>{carrera.codigo}</option>
                {/each}
              </select>
            </div>
            <div class="field">
              <label class="grupos-barra-label" for="periodo-pertenencia">Período de pertenencia</label>
              <select id="periodo-pertenencia" class="input-plain input-sm" bind:value={periodoGrupoId} on:change={limpiarInputCSV}>
                <option value="">Selecciona un período</option>
                {#each periodos.filter(p => p.id) as periodo}
                  <option value={periodo.id}>{periodo.periodo_label || periodo.cuatrimestre}</option>
                {/each}
              </select>
            </div>
            <div class="field">
              <label class="grupos-barra-label" for="grupo-activo">
                {#if grupoCreado}
                  Grupo activo — <span class="highlight-orange">{grupoCreado.nomenclatura}</span>
                {:else}
                  Grupo activo
                {/if}
              </label>
              {#if loadingGrupos}
                <div class="spinner" style="width:18px;height:18px;border-width:2px;"></div>
              {:else}
                <select id="grupo-activo" class="input-plain input-sm" class:select-activo={grupoCreado} on:change={(e) => {
                    const g = gruposExistentes.find(x => String(x.id) === e.target.value)
                    if (g) seleccionarGrupo(g)
                    else { grupoCreado = null; grupoSeleccionado = null }
                  }}>
                  <option value="">Sin grupo activo</option>
                  {#each gruposExistentes as g}
                    <option value={g.id} selected={grupoCreado?.id === g.id}>{etiquetaGrupo(g)}</option>
                  {/each}
                </select>
              {/if}
            </div>
          </div>
          
          <div class="reportes-card reportes-card-compacta">
            <h2 class="card-title">Registrar grupo nuevo</h2>

            {#if errorGrupo}
              <div class="error-msg">{errorGrupo}</div>
            {/if}

            <div class="form-col">
              <div class="field">
                <label for="nuevo-grupo-carrera">Carrera</label>
                <select id="nuevo-grupo-carrera" class="input-plain input-sm" bind:value={formGrupo.carrera} disabled={grupoCreado}>
                  {#each carrerasInstitucionales as carrera}
                    <option value={carrera.nombre}>{carrera.codigo} — {carrera.nombre}</option>
                  {/each}
                </select>
              </div>
              <div class="field">
                <label for="nuevo-grupo-modalidad">Modalidad</label>
                <select id="nuevo-grupo-modalidad" class="input-plain input-sm" bind:value={formGrupo.modalidad} disabled={grupoCreado}>
                  <option value="bis">BIS</option>
                  <option value="intensivo">Intensivo</option>
                  <option value="mixta">Mixta</option>
                  <option value="despresurizada">Despresurizada</option>
                </select>
              </div>
              <div class="field">
                <label for="nuevo-grupo-turno">Turno</label>
                <select id="nuevo-grupo-turno" class="input-plain input-sm" bind:value={formGrupo.turno} disabled={grupoCreado}>
                  <option value="Matutino">Matutino</option>
                  <option value="Vespertino">Vespertino</option>
                </select>
              </div>
              <div class="field">
                <label for="nuevo-grupo-cuatrimestre">Cuatrimestre</label>
                <select id="nuevo-grupo-cuatrimestre" class="input-plain input-sm" bind:value={formGrupo.cuatrimestre} disabled={grupoCreado}>
                  {#each Array.from({length: 12}, (_, i) => i + 1) as n}
                    <option value={n}>{n}</option>
                  {/each}
                </select>
              </div>
              <div class="field">
                <label for="nuevo-grupo-letra">Letra</label>
                <select id="nuevo-grupo-letra" class="input-plain input-sm" bind:value={formGrupo.letra} disabled={grupoCreado}>
                  {#each ['A','B','C','D','E','F'] as l}
                    <option value={l}>{l}</option>
                  {/each}
                </select>
              </div>
            </div>

            {#if !grupoCreado}
              <button class="btn-primary" style="margin-top:6px" on:click={registrarGrupo} disabled={guardandoGrupo}>
                {guardandoGrupo ? 'Registrando...' : 'Registrar grupo'}
              </button>
            {:else}
              <button class="btn-outline" style="margin-top:6px" on:click={() => { grupoCreado = null; grupoSeleccionado = null; limpiarInputCSV() }}>
                Registrar otro grupo
              </button>
            {/if}
          </div>
        </div>

        <div class="grupos-col-der">
          {#if grupoCreado}
            <div class="reportes-card reportes-card-compacta">
              <h2 class="card-title">Carga masiva de alumnos</h2>
              <p class="csv-instructions">Descarga la plantilla, llénala y súbela para matricular alumnos en bloque.</p>

              <div class="carga-fila-botones">
                <button class="btn-outline" on:click={descargarPlantillaCSV}>Descargar CSV base</button>

                <input type="file" accept=".csv" bind:this={inputFileRef} style="display:none" on:change={(e) => { archivoCSV = e.target.files[0]; resultadoCSV = null; errorCSV = '' }} />
                <button class="btn-file" on:click={() => inputFileRef.click()}>
                  <svg width="15" height="15" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M3 16.5v2.25A2.25 2.25 0 0 0 5.25 21h13.5A2.25 2.25 0 0 0 21 18.75V16.5m-13.5-9L12 3m0 0 4.5 4.5M12 3v13.5" />
                  </svg>
                  {archivoCSV ? archivoCSV.name : 'Seleccionar archivo CSV'}
                </button>

                <button class="btn-primary" disabled={!archivoCSV || !periodoGrupoId || subiendoCSV} on:click={procesarCargaMasiva}>
                  {subiendoCSV ? 'Validando...' : 'Revisar archivo'}
                </button>
              </div>

              {#if errorCSV}
                <div class="error-msg" style="margin-top:10px">{errorCSV}</div>
              {/if}

              {#if resultadoCSV}
                {@const total = resultadoCSV.preview
                  ? resultadoCSV.validos.length + resultadoCSV.repetidos.length + resultadoCSV.errores.length
                  : resultadoCSV.insertados.length + resultadoCSV.actualizados.length + (resultadoCSV.repetidos || []).length + resultadoCSV.errores.length}
                <div class="resultado-csv">
                  {#if total === 0}
                    <p class="resultado-vacio">El archivo no contiene registros para procesar.</p>
                  {:else}
                    {#if resultadoCSV.preview}
                      <p class="resultado-actualizados">Vista previa para {resultadoCSV.grupo} · {resultadoCSV.periodo}</p>
                      <p class="resultado-ok">{resultadoCSV.validos.length} fila{resultadoCSV.validos.length !== 1 ? 's' : ''} lista{resultadoCSV.validos.length !== 1 ? 's' : ''} para aplicar.</p>
                      {#if resultadoCSV.repetidos.length > 0}
                        <p class="resultado-actualizados">{resultadoCSV.repetidos.length} fila{resultadoCSV.repetidos.length !== 1 ? 's' : ''} ya pertenece{resultadoCSV.repetidos.length === 1 ? '' : 'n'} al grupo en este período.</p>
                      {/if}
                      {#if resultadoCSV.puedeAplicar}
                        <button class="btn-primary" disabled={subiendoCSV} on:click={confirmarCargaMasiva}>Confirmar lote completo</button>
                      {:else}
                        <p class="resultado-err-titulo">Corrige todos los conflictos antes de aplicar.</p>
                      {/if}
                    {:else if resultadoCSV.insertados.length > 0}
                      <p class="resultado-ok">✓ {resultadoCSV.insertados.length} alumno{resultadoCSV.insertados.length !== 1 ? 's' : ''} insertado{resultadoCSV.insertados.length !== 1 ? 's' : ''} correctamente.</p>
                      <div class="resultado-alumnos">
                        <ul class="resultado-lista-alumnos">
                          {#each resultadoCSV.insertados as alumno}
                            <li><span class="ficha-mono">{alumno.matricula}</span> — {alumno.nombre}</li>
                          {/each}
                        </ul>
                      </div>
                    {/if}
                    {#if !resultadoCSV.preview && resultadoCSV.actualizados.length > 0}
                      <p class="resultado-actualizados">↻ Para {resultadoCSV.actualizados.length} alumno{resultadoCSV.actualizados.length !== 1 ? 's' : ''} existente{resultadoCSV.actualizados.length !== 1 ? 's' : ''} se registró la pertenencia de este período.</p>
                      <div class="resultado-alumnos">
                        <ul class="resultado-lista-alumnos">
                          {#each resultadoCSV.actualizados as alumno}
                            <li><span class="ficha-mono">{alumno.matricula}</span> — {alumno.nombre}</li>
                          {/each}
                        </ul>
                      </div>
                    {/if}
                    {#if resultadoCSV.errores.length > 0}
                      <p class="resultado-err-titulo">{resultadoCSV.errores.length} registro{resultadoCSV.errores.length !== 1 ? 's' : ''} no procesado{resultadoCSV.errores.length !== 1 ? 's' : ''}:</p>
                      <ul class="resultado-err-lista">
                        {#each resultadoCSV.errores as err}
                          <li><strong>Fila {err.fila}</strong> {err.matricula ? `(${err.matricula})` : ''}: {err.razon}</li>
                        {/each}
                      </ul>
                    {/if}
                  {/if}
                </div>
              {/if}

            </div>
          {/if}

          <div class="reportes-card" style={grupoCreado ? 'margin-top:16px' : ''}>
            <h2 class="card-title">Gestión individual de alumnos</h2>
            <p class="csv-instructions">Para actualizar o desactivar el acceso solo necesitas la matrícula. Para agregar, selecciona un grupo activo primero.</p>

            {#if errorIndividual}
              <div class="error-msg">{errorIndividual}</div>
            {/if}

            {#if previewIndividual}
              <div class="preview-individual">
                <p class="preview-titulo">{previewIndividual.accion === 'agregar' ? 'Confirmar alta' : 'Confirmar actualización'}</p>
                {#each previewIndividual.filas as f}
                  <div class="preview-fila">
                    <span class="ficha-mono">{f.matricula}</span>
                    <span>{f.nombre}</span>
                  </div>
                {/each}
                <div class="preview-acciones">
                  <button class="btn-primary" disabled={procesandoIndividual} on:click={confirmarAccion}>
                    {procesandoIndividual ? 'Procesando...' : 'Confirmar'}
                  </button>
                  <button class="btn-outline" disabled={procesandoIndividual} on:click={() => previewIndividual = null}>
                    Cancelar
                  </button>
                </div>
              </div>
            {:else}
              <div class="filas-individuales">
                {#each filasAlumnos as fila}
                  <div class="fila-alumno">
                    <input type="text" class="input-plain" placeholder="Matrícula (9 dígitos)" maxlength="9" bind:value={fila.matricula} />
                    <input type="text" class="input-plain" placeholder="Nombre completo" bind:value={fila.nombre} />
                  </div>
                {/each}
                <button class="btn-add-fila" on:click={agregarFila}>+ Agregar otro</button>
              </div>

              <div class="acciones-individuales">
                <button class="btn-outline" on:click={() => prepararAccion('agregar')}>Agregar</button>
                <button class="btn-outline" on:click={() => prepararAccion('actualizar')}>Actualizar</button>
                <button class="btn-eliminar" on:click={prepararEliminar}>Desactivar acceso</button>
              </div>
            {/if}
          </div>

          <div class="reportes-card" style="margin-top:16px">
            <h2 class="card-title">Promoción de grupo</h2>
            <p class="csv-instructions">Previsualiza el lote completo antes de crear la pertenencia del período destino. Los conflictos cancelan toda la operación.</p>
            <div class="form-col">
              <div class="field"><label for="promocion-grupo-origen">Grupo origen</label><select id="promocion-grupo-origen" class="input-plain input-sm" bind:value={promocion.grupo_origen_id}><option value="">Selecciona</option>{#each gruposExistentes as g}<option value={g.id}>{etiquetaGrupo(g)}</option>{/each}</select></div>
              <div class="field"><label for="promocion-periodo-origen">Período origen</label><select id="promocion-periodo-origen" class="input-plain input-sm" bind:value={promocion.periodo_origen_id}><option value="">Selecciona</option>{#each periodos.filter(p => p.id) as p}<option value={p.id}>{p.periodo_label}</option>{/each}</select></div>
              <div class="field"><label for="promocion-grupo-destino">Grupo destino</label><select id="promocion-grupo-destino" class="input-plain input-sm" bind:value={promocion.grupo_destino_id}><option value="">Selecciona</option>{#each gruposExistentes as g}<option value={g.id}>{etiquetaGrupo(g)}</option>{/each}</select></div>
              <div class="field"><label for="promocion-periodo-destino">Período destino</label><select id="promocion-periodo-destino" class="input-plain input-sm" bind:value={promocion.periodo_destino_id}><option value="">Selecciona</option>{#each periodos.filter(p => p.id) as p}<option value={p.id}>{p.periodo_label}</option>{/each}</select></div>
            </div>
            {#if errorPromocion}<div class="error-msg">{errorPromocion}</div>{/if}
            {#if previewPromocion}
              <div class="preview-individual">
                <p>{previewPromocion.validos?.length || 0} alumno(s) por promover; {previewPromocion.repetidos?.length || 0} ya estaban en destino.</p>
                {#if previewPromocion.errores?.length}<p class="resultado-err-titulo">Hay {previewPromocion.errores.length} conflicto(s); no se aplicará el lote.</p>{/if}
                {#if previewPromocion.aplicado}<p class="resultado-ok">Promoción aplicada y período anterior conservado.</p>{:else if previewPromocion.puede_aplicar}<button class="btn-primary" disabled={procesandoPromocion} on:click={confirmarPromocion}>Confirmar promoción</button>{/if}
              </div>
            {:else}
              <button class="btn-outline" disabled={procesandoPromocion} on:click={revisarPromocion}>Revisar promoción</button>
            {/if}
          </div>

        </div>

      </div>
    </div>
  
  {:else if vista === 'expediente' && alumnoSeleccionado}
    <h1 class="sr-only">Expediente del alumno</h1>
    <div class="page-wrap">
      <div class="expediente-topbar">
        <button class="btn-back" on:click={volverDirectorio}>
          <svg width="16" height="16" fill="none" stroke="currentColor" stroke-width="2.2" viewBox="0 0 24 24" style="display:inline; margin-right:4px; vertical-align:text-bottom;" aria-hidden="true">
            <path stroke-linecap="round" stroke-linejoin="round" d="M10.5 19.5 L3 12 m0 0 l7.5-7.5 M3 12 h18" />
          </svg>
          Volver al directorio
        </button>
      </div>

      {#if loadingExpediente}
        <LoadingSpinner />
      {:else if errorExpediente}
        <p class="error-msg" role="alert">{errorExpediente}</p>
        <button class="btn-outline" on:click={() => abrirExpediente(alumnoSeleccionado)}>Reintentar</button>
      {:else}
        <ExpedienteAlumno datos={expedienteDatos} modo="personal" puedeExportar={$isTutorAcademico}
          on:actualizar={() => abrirExpediente(alumnoSeleccionado)} />
      {/if}
    </div>
  {/if}

  {#if modalEliminar}
    <div class="modal-overlay" on:click={() => modalEliminar = null}>
      <div class="modal-box" on:click|stopPropagation>
        <p class="modal-titulo">¿Desactivar acceso del alumno?</p>
        <p class="modal-cuerpo">
          Se desactivará el acceso de <strong>{modalEliminar.nombre || modalEliminar.matricula}</strong> y se revocarán sus sesiones. Sus datos, reportes y asignaciones se conservan. Esto no da de baja su incorporación Dual.
        </p>
        <div class="modal-acciones">
          <button class="btn-eliminar" disabled={procesandoIndividual} on:click={confirmarEliminar}>
            {procesandoIndividual ? 'Desactivando...' : 'Sí, desactivar acceso'}
          </button>
          <button class="btn-outline" disabled={procesandoIndividual} on:click={() => modalEliminar = null}>
            Cancelar
          </button>
        </div>
      </div>
    </div>
  {/if}

</main>

<style>
  .main-content { padding-top: 56px; background: var(--bg-page); min-height: 100vh; }
  .page-wrap { padding: 40px 24px; max-width: 1100px; margin: 0 auto; display: flex; flex-direction: column; gap: 20px; }
  .page-wrap-grupos { padding: 32px 24px; max-width: 1100px; margin: 0 auto; display: flex; flex-direction: column; gap: 16px; }

  .header-flex { display: flex; justify-content: space-between; align-items: center; }
  .page-title { font-size: 22px; font-weight: 700; color: var(--text-primary); letter-spacing: -0.02em; }
  .page-sub { font-size: 14px; color: var(--text-secondary); margin-top: 2px; }

  .table-wrap { overflow-x: auto; border: 1px solid var(--border); border-radius: var(--radius-card); background: var(--bg-card); box-shadow: var(--shadow-card); }
  .tabla { width: 100%; border-collapse: collapse; font-size: 14px; }
  .tabla thead { background: var(--bg-page); }
  .tabla th { text-align: left; padding: 12px 18px; font-weight: 600; color: var(--text-disabled); font-size: 11px; text-transform: uppercase; letter-spacing: 0.05em; border-bottom: 1px solid var(--border); white-space: nowrap; }
  .tabla td { padding: 14px 18px; color: var(--text-secondary); border-bottom: 1px solid var(--border); vertical-align: middle; }
  .tabla tbody tr:last-child td { border-bottom: none; }
  .tabla tbody tr:hover { background: var(--orange-light); }
  .tabla tbody tr:hover > .col-accion { background: var(--orange-light); }

  .td-matricula { font-family: monospace; font-weight: 600; color: var(--text-primary); letter-spacing: 0.02em; }
  .td-nombre { font-weight: 600; color: var(--text-primary); }
  .td-grupo { font-family: monospace; font-size: 13px; color: var(--text-secondary); }
  .td-center { text-align: center; }
  .td-cal { font-weight: 700; color: var(--orange); font-size: 15px; text-align: center; }
  .td-fecha { font-size: 13px; color: var(--text-secondary); white-space: nowrap; }
  .td-promedio { font-weight: 700; color: var(--text-primary); }

  .text-secondary { color: var(--text-disabled); font-style: italic; }
  .empresa-txt { font-weight: 500; color: var(--text-primary); }
  .sem-txt { font-weight: 600; color: var(--text-primary); }

  .chip-reportes { display: inline-block; background: rgba(249, 115, 22, 0.08); color: var(--orange); font-weight: 700; font-size: 12px; border-radius: 6px; padding: 2px 10px; border: 1px solid rgba(249, 115, 22, 0.2); }
  
  .btn-ver { background: transparent; border: 1.5px solid var(--border-input); border-radius: 8px; padding: 6px 14px; font-size: 13px; font-weight: 600; color: var(--text-primary); cursor: pointer; transition: all 0.2s ease; }
  .btn-ver:hover { border-color: var(--orange); color: var(--orange); background: var(--orange-light); }

  .btn-pdf { display: inline-block; background: transparent; border: 1.5px solid var(--border-input); border-radius: 8px; padding: 5px 12px; font-size: 12px; font-weight: 600; color: var(--orange); text-decoration: none; transition: all 0.2s ease; }
  .btn-pdf:hover { background: var(--orange-action-hover); color: white; border-color: var(--orange-hover); }

  .count-label { font-size: 12px; color: var(--text-disabled); text-align: right; margin-top: 4px; font-weight: 500; }

  .filtros-extra { display: flex; gap: 16px; flex-wrap: wrap; }
  .campo-filtro { display: flex; flex-direction: column; gap: 4px; min-width: 200px; flex: 1 1 200px; }
  .campo-filtro label { font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; color: var(--text-disabled); }
  .paquete-carrera { background: var(--bg-card); border: 1px solid var(--border); border-radius: var(--radius-card); padding: 16px 20px; display: flex; flex-direction: column; gap: 10px; }
  .paquete-titulo { font-size: 15px; margin: 0; color: var(--text-primary); }
  .paquete-texto { margin: 0; font-size: 13px; color: var(--text-secondary); }
  .paquete-fila { display: flex; gap: 14px; flex-wrap: wrap; align-items: flex-end; }
  .chip-baja { display: inline-block; margin-left: 8px; font-size: 11px; font-weight: 700; color: var(--text-secondary); border: 1px solid var(--border-input); border-radius: 999px; padding: 1px 8px; white-space: nowrap; }
  .paginacion { display: flex; gap: 10px; align-items: center; justify-content: flex-end; flex-wrap: wrap; }
  .paginacion .count-label { margin: 0 auto 0 0; }

  .spinner { width: 28px; height: 28px; margin: 0 auto; border: 3px solid var(--border); border-top-color: var(--orange); border-radius: 50%; animation: spin 0.8s linear infinite; }
  @keyframes spin { to { transform: rotate(360deg); } }

  .expediente-topbar { display: flex; align-items: center; justify-content: space-between; gap: 16px; flex-wrap: wrap; }
  .btn-back { background: none; border: none; cursor: pointer; padding: 0; font-family: var(--font); font-size: 14px; font-weight: 600; color: var(--text-secondary); transition: color 0.15s; }
  .btn-back:hover { color: var(--orange); }
  .periodo-selector { display: flex; align-items: center; gap: 8px; }
  .periodo-label { font-size: 12px; font-weight: 600; color: var(--text-disabled); text-transform: uppercase; letter-spacing: 0.04em; white-space: nowrap; }
  .periodo-selector select { min-width: 180px; }

  .expediente-layout { display: grid; grid-template-columns: 320px 1fr; gap: 24px; align-items: start; }
  .ficha-card { background: var(--bg-card); border-radius: var(--radius-card); border: 1px solid var(--border); box-shadow: var(--shadow-card); padding: 24px; display: flex; flex-direction: column; gap: 16px; position: sticky; top: calc(56px + 24px); }
  .ficha-titulo { font-size: 12px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; color: var(--text-disabled); margin: 0; }
  .ficha-divider { height: 1px; background: var(--border); width: 100%; margin-top: -4px; }
  .ficha-grid { display: grid; grid-template-columns: auto 1fr; gap: 10px 16px; align-items: baseline; }
  .ficha-key { font-size: 11px; font-weight: 600; color: var(--text-disabled); text-transform: uppercase; letter-spacing: 0.02em; }
  .ficha-val { font-size: 14px; font-weight: 500; color: var(--text-secondary); word-break: break-word; }
  .ficha-mono { font-family: monospace; font-weight: 600; color: var(--text-primary); }

  .promedio-box { background: rgba(249, 115, 22, 0.06); border: 1px solid rgba(249, 115, 22, 0.15); border-radius: 12px; padding: 14px; text-align: center; }
  .promedio-label { font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; color: var(--orange); margin: 0 0 4px; }
  .promedio-valor { font-size: 32px; font-weight: 800; color: var(--orange); margin: 0; line-height: 1; letter-spacing: -0.03em; }

  .ficha-acciones { display: flex; flex-direction: column; gap: 10px; margin-top: 4px; }

  .reportes-card { background: var(--bg-card); border-radius: var(--radius-card); border: 1px solid var(--border); box-shadow: var(--shadow-card); padding: 28px; display: flex; flex-direction: column; gap: 20px; }
  .reportes-card-compacta { padding: 20px; gap: 12px; }
  .card-title { font-size: 16px; font-weight: 700; color: var(--text-primary); margin: 0; }

  .form-col { display: flex; flex-direction: column; gap: 8px; }
  .card-static { position: static; margin-top: 20px; }
  .highlight-orange { color: var(--orange); }
  .csv-upload-section { margin-top: 14px; }
  .csv-instructions { font-size: 13px; color: var(--text-secondary); margin-bottom: 12px; }
  
  .carga-header { display: flex; align-items: center; justify-content: space-between; gap: 12px; flex-wrap: wrap; }
  .carga-fila-botones { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 10px; align-items: stretch; }
  
  .btn-mb { margin-bottom: 16px; }
  .mt-10 { margin-top: 10px; }
  .mt-14 { margin-top: 14px; }
  .bold-primary { color: var(--text-primary); font-weight: 600; }

  .grupos-topbar { margin-bottom: 20px; }
  .grupos-layout { display: grid; grid-template-columns: 260px 1fr; gap: 20px; align-items: start; }
  .grupos-col-izq, .grupos-col-der { display: flex; flex-direction: column; gap: 0; }

  .grupos-selector-card { background: var(--bg-card); border-radius: var(--radius-card); border: 1px solid var(--border); box-shadow: var(--shadow-card); padding: 14px; display: flex; flex-direction: column; gap: 10px; margin-bottom: 16px; }
  .input-sm { padding-top: 6px !important; padding-bottom: 6px !important; font-size: 13px !important; }
  .select-activo { border-color: var(--orange); color: var(--orange); font-weight: 600; }

  .grupos-barra { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; background: var(--bg-card); padding: 16px; border-radius: var(--radius-card); border: 1px solid var(--border); box-shadow: var(--shadow-card); }
  .grupos-barra-col { display: flex; flex-direction: column; gap: 6px; }
  .grupos-barra-label { font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; color: var(--text-disabled); white-space: nowrap; }
  .grupos-barra-sep { color: var(--text-disabled); }
  .grupos-barra-empty { font-size: 13px; color: var(--text-disabled); }
  
  .grupos-chips { display: flex; flex-wrap: wrap; gap: 6px; }
  .grupo-chip { padding: 5px 12px; border-radius: 20px; border: 1.5px solid var(--border); background: var(--bg-page); font-family: monospace; font-size: 13px; font-weight: 700; color: var(--text-primary); cursor: pointer; transition: all 0.15s; }
  .grupo-chip:hover { border-color: var(--orange); color: var(--orange); background: var(--orange-light); }
  .grupo-chip-activo { border-color: var(--orange); background: var(--orange-light); color: var(--orange); }

  .grupos-der-header { display: flex; align-items: center; justify-content: space-between; gap: 12px; margin-bottom: 16px; }
  .select-carrera-grupos { width: auto; min-width: 100px; font-size: 13px; padding: 6px 10px; }
  .grupos-lista { display: flex; flex-direction: column; gap: 6px; }
  
  .grupo-item { display: flex; align-items: center; justify-content: space-between; padding: 10px 14px; border-radius: 10px; border: 1.5px solid var(--border); background: var(--bg-page); cursor: pointer; font-family: var(--font); transition: all 0.15s; text-align: left; width: 100%; }
  .grupo-item:hover { border-color: var(--orange); background: var(--orange-light); }
  .grupo-item-activo { border-color: var(--orange); background: var(--orange-light); }
  .grupo-nomenclatura { font-family: monospace; font-weight: 700; font-size: 14px; color: var(--text-primary); }
  .grupo-meta { font-size: 12px; color: var(--text-secondary); }

  .grupo-activo-banner { margin-bottom: 12px; padding: 10px 14px; background: var(--orange-light); border-radius: 8px; border: 1px solid rgba(249,115,22,0.2); display: flex; gap: 8px; align-items: center; }

  .btn-file { display: flex; align-items: center; gap: 8px; width: 100%; padding: 10px 14px; border: 1.5px dashed var(--border); border-radius: var(--radius-input); background: var(--bg-page); color: var(--text-secondary); font-family: var(--font); font-size: 13px; font-weight: 500; cursor: pointer; transition: all 0.15s; text-align: left; }
  .btn-file:hover { border-color: var(--orange); color: var(--orange); background: var(--orange-light); }

  .filas-individuales { display: flex; flex-direction: column; gap: 10px; }
  .fila-alumno { display: grid; grid-template-columns: 1fr 2fr; gap: 10px; }
  
  .btn-add-fila { align-self: flex-start; background: none; border: none; padding: 4px 0; font-family: var(--font); font-size: 13px; font-weight: 600; color: var(--orange); cursor: pointer; }
  .btn-add-fila:hover { color: var(--orange-hover); }

  .acciones-individuales { display: flex; gap: 10px; margin-top: 14px; flex-wrap: wrap; }
  
  .btn-eliminar { padding: 9px 18px; border: 1.5px solid var(--error); border-radius: var(--radius-input); background: transparent; color: var(--error-text); font-family: var(--font); font-size: 14px; font-weight: 600; cursor: pointer; transition: all 0.15s; }
  .btn-eliminar:hover { background: var(--error); color: white; }
  .btn-eliminar:disabled { opacity: 0.5; cursor: not-allowed; }

  .preview-individual { background: var(--bg-page); border: 1px solid var(--border); border-radius: var(--radius-input); padding: 14px; display: flex; flex-direction: column; gap: 10px; }
  .preview-titulo { font-size: 12px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; color: var(--text-disabled); margin: 0; }
  .preview-fila { display: flex; gap: 12px; font-size: 14px; color: var(--text-secondary); align-items: center; }
  .preview-acciones { display: flex; gap: 10px; margin-top: 4px; }

  .modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.35); display: flex; align-items: center; justify-content: center; z-index: 200; }
  .modal-box { background: var(--bg-card); border-radius: var(--radius-card); border: 1px solid var(--border); padding: 28px; max-width: 400px; width: 90%; display: flex; flex-direction: column; gap: 14px; }
  .modal-titulo { font-size: 16px; font-weight: 700; color: var(--text-primary); margin: 0; }
  .modal-cuerpo { font-size: 14px; color: var(--text-secondary); margin: 0; }
  .modal-acciones { display: flex; gap: 10px; }

  .resultado-csv { margin-top: 14px; padding: 12px; border-radius: 8px; background: var(--bg-page); border: 1px solid var(--border); display: flex; flex-direction: column; gap: 8px; }
  .resultado-ok { color: var(--success-text); font-weight: 600; font-size: 13px; margin: 0; }
  .resultado-actualizados { color: #d97706; font-weight: 600; font-size: 13px; margin: 0; }
  .resultado-vacio { color: var(--text-disabled); font-size: 13px; font-style: italic; margin: 0; }
  .resultado-alumnos { margin-top: 2px; }
  .resultado-lista-alumnos { margin: 0; padding-left: 16px; font-size: 12px; color: var(--text-secondary); display: flex; flex-direction: column; gap: 2px; }
  .resultado-err-titulo { color: var(--error-text); font-weight: 600; font-size: 12px; margin: 0; }
  .resultado-err-lista { margin: 0; padding-left: 16px; font-size: 12px; color: var(--text-secondary); }

  .expediente-der { flex: 1; min-width: 0; }
  .expediente-split {
    display: grid;
    grid-template-columns: 280px 1fr;
    gap: 0;
    flex: 1;
    min-height: 0;
  }
  .expediente-tabla-col {
    border-right: 1px solid var(--border);
    overflow-y: auto;
  }
  .expediente-pdf-col {
    min-height: 0;
    display: flex;
    flex: 1;
  }
  .expediente-pdf-col :global(.visor-wrap) {
    border-radius: 0;
    border: none;
    width: 100%;
  }
  .row-selected {
    background: var(--orange-light) !important;
    border-left: 3px solid var(--orange);
  }

  @media (max-width: 900px) {
    .page-wrap { padding: 24px 16px; }
    .page-wrap-grupos { padding: 24px 16px; }
    .expediente-layout { grid-template-columns: 1fr; }
    .ficha-card { position: static; }
    .expediente-split { grid-template-columns: 1fr; }
    .expediente-pdf-col { min-height: 0; flex: 1; }
    .grupos-layout { grid-template-columns: 1fr; }
    .grupos-barra { grid-template-columns: 1fr; }
    .carga-fila-botones { grid-template-columns: 1fr; }
    .fila-alumno { grid-template-columns: 1fr; }
  }
</style>
