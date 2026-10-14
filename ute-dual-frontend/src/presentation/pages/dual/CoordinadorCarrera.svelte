<script>
  // src/routes/dual/CoordinadorCarrera.svelte
  import { onMount } from 'svelte'
  import { navigate, useLocation } from 'svelte-routing'
  import { get } from 'svelte/store'
  import { isAuthenticated, isCoordinadorCarrera, isTutorAcademico } from '../../stores/auth.js'
  import { api } from '../../../composition/api.js'
  import Navbar from '../../components/layout/Navbar.svelte'
  import VisorPDF from '../../components/shared/VisorPDF.svelte'
  import FiltrosBarra from '../../components/shared/FiltrosBarra.svelte'
  import LoadingSpinner from '../../components/ui/LoadingSpinner.svelte'
  import EmptyState from '../../components/ui/EmptyState.svelte'
  import { formatFecha } from '../../utils/formatters.js'

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

  let alumnos = []
  let loading = true
  let error = ''
  let filtroCuatrimestre = ''
  let filtroGrupo = ''
  let filtroBusqueda = ''
  let filtroCarrera = ''
  let filtroEstado = ''

  let alumnoSeleccionado = null
  let reportes = []
  let loadingExpediente = false
  let errorExpediente = ''
  let pdfSeleccionado = null
  let periodos = []
  let periodoSeleccionado = ''

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
    await Promise.all([cargarAlumnos(), cargarPeriodos()])
  })

  async function cargarPeriodos() {
    try {
      periodos = await api.dual.periodos()
      if (periodos.length && !periodoSeleccionado) {
        periodoSeleccionado = periodos[0].cuatrimestre
      }
    } catch (e) {
      // Silencioso — el dropdown simplemente no aparecerá
      periodos = []
    }
  }

  async function cargarAlumnos() {
    loading = true
    error = ''
    try {
      const params = new URLSearchParams()
      if (filtroCuatrimestre) {
        params.append('cuatrimestre', filtroCuatrimestre)
      }
      if (filtroGrupo) {
        params.append('grupo', filtroGrupo)
      }
      alumnos = await api.dual.listarAlumnos(params.toString())
    } catch (e) {
      error = e.message || 'Error al cargar alumnos.'
    } finally {
      loading = false
    }
  }

  $: carreras = [...new Set(alumnos.map(a => a.carrera).filter(Boolean))].sort()
  $: grupos = [...new Set(alumnos.map(a => a.nomenclatura || a.grupo).filter(Boolean))].sort()

  $: alumnosFiltrados = alumnos.filter(a => {
    const busqueda = filtroBusqueda.toLowerCase()
    const matchBusqueda = filtroBusqueda.trim()
      ? a.matricula.toLowerCase().includes(busqueda) || 
        a.nombre.toLowerCase().includes(busqueda)
      : true
      
    const carreraStr = filtroCarrera.toLowerCase()
    const matchCarrera = filtroCarrera
      ? (a.carrera && a.carrera.toLowerCase() === carreraStr) || 
        (a.nomenclatura && a.nomenclatura.toLowerCase().includes(carreraStr))
      : true
      
    return matchBusqueda && matchCarrera
  })

  async function abrirExpediente(alumno) {
    alumnoSeleccionado = alumno
    reportes = []
    errorExpediente = ''
    loadingExpediente = true
    vista = 'expediente'
    try {
      const paramCuatri = periodoSeleccionado || null
      reportes = await api.dual.expediente(alumno.matricula, paramCuatri)
    } catch (e) {
      errorExpediente = e.message || 'Error al cargar el expediente.'
    } finally {
      loadingExpediente = false
    }
  }

  async function cambiarPeriodo() {
    if (!alumnoSeleccionado) return
    reportes = []
    errorExpediente = ''
    loadingExpediente = true
    try {
      const paramCuatri = periodoSeleccionado || null
      reportes = await api.dual.expediente(alumnoSeleccionado.matricula, paramCuatri)
    } catch (e) {
      errorExpediente = e.message || 'Error al cargar el expediente.'
    } finally {
      loadingExpediente = false
    }
  }

  function volverDirectorio() {
    alumnoSeleccionado = null
    reportes = []
    pdfSeleccionado = null
    vista = 'directorio'
    navigate('/dual/carrera', { replace: true })
  }

  async function descargarCSV(matricula) {
    await api.dual.exportarCSV(matricula, periodoSeleccionado || undefined)
  }

  $: promedioExpediente = reportes.length
    ? (reportes.reduce((s, r) => s + Number(r.calificacion_alumno), 0) / reportes.length).toFixed(2)
    : null
    
  $: carreraCompletaExpediente = alumnoSeleccionado ? alumnoSeleccionado.carrera : '—'

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
    if (!archivoCSV || !grupoCreado) return
    subiendoCSV = true
    errorCSV = ''
    resultadoCSV = null

    try {
      const fd = new FormData()
      fd.append('file', archivoCSV)
      const respuesta = await api.dual.subirAlumnosCSV(grupoCreado.id, fd)

      resultadoCSV = {
        insertados: respuesta.insertados || [],
        actualizados: respuesta.actualizados || [],
        errores: respuesta.errores || [],
      }
      archivoCSV = null
      if (inputFileRef) inputFileRef.value = ""
      await cargarAlumnos()
    } catch (e) {
      errorCSV = e.message || 'Error de I/O al procesar el archivo.'
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
    previewIndividual = { accion, filas: filasAlumnos.map(f => ({ ...f })) }
  }

  function prepararEliminar() {
    errorIndividual = ''
    if (filasAlumnos.length !== 1 || !filasAlumnos[0].matricula) {
      errorIndividual = 'Ingresa una sola matrícula para eliminar.'
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
          await api.dual.agregarAlumno(grupoCreado.id, f)
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
      errorIndividual = e.message || 'Error al eliminar el alumno.'
      modalEliminar = null
    } finally {
      procesandoIndividual = false
    }
  }
</script>

<svelte:head>
  <title>Coordinador de Carrera | Portal UTE</title>
</svelte:head>

<Navbar />

<div class="main-content">

  {#if vista === 'directorio'}
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
        on:buscar={cargarAlumnos}
      />

      {#if loading}
        <LoadingSpinner />
      {:else if error}
        <p class="error-msg">{error}</p>
      {:else if alumnosFiltrados.length === 0}
        <EmptyState message="No hay alumnos duales con los filtros seleccionados." />
      {:else}
        <div class="table-wrap">
          <table class="tabla">
            <thead>
              <tr>
                <th>Matrícula</th>
                <th>Nombre</th>
                <th>Grupo</th>
                <th>Empresa</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {#each alumnosFiltrados as a}
                <tr>
                  <td class="td-matricula">{a.matricula}</td>
                  <td class="td-nombre">{a.nombre}</td>
                  <td class="td-grupo">{a.nomenclatura || '—'}</td>
                  <td>{a.empresa || 'Sin asignar'}</td>
                  <td style="text-align: right;">
                    <button class="btn-ver" on:click={() => abrirExpediente(a)}>
                      Ver Expediente
                    </button>
                  </td>
                </tr>
              {/each}
            </tbody>
          </table>
        </div>
      {/if}
    </div>

  {:else if vista === 'grupos' && $isTutorAcademico}
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
              <label class="grupos-barra-label">Carrera</label>
              <select class="input-plain input-sm" bind:value={filtroCarreraGrupos} on:change={cargarGrupos}>
                <option value="">Todas</option>
                <option value="ING.NME TEC DE LA INFORMACIÓN E INNOVACION DIGITAL">TII</option>
                <option value="ING. NME LOGISTICA">LOG</option>
                <option value="LIC. NME EDUCACIÓN">EDU</option>
              </select>
            </div>
            <div class="field">
              <label class="grupos-barra-label">
                {#if grupoCreado}
                  Grupo activo — <span class="highlight-orange">{grupoCreado.nomenclatura}</span>
                {:else}
                  Grupo activo
                {/if}
              </label>
              {#if loadingGrupos}
                <div class="spinner" style="width:18px;height:18px;border-width:2px;"></div>
              {:else}
                <select class="input-plain input-sm" class:select-activo={grupoCreado} on:change={(e) => {
                    const g = gruposExistentes.find(x => String(x.id) === e.target.value)
                    if (g) seleccionarGrupo(g)
                    else { grupoCreado = null; grupoSeleccionado = null }
                  }}>
                  <option value="">Sin grupo activo</option>
                  {#each gruposExistentes as g}
                    <option value={g.id} selected={grupoCreado?.id === g.id}>{g.nomenclatura}</option>
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
                <label>Carrera</label>
                <select class="input-plain input-sm" bind:value={formGrupo.carrera} disabled={grupoCreado}>
                  <option value="ING.NME TEC DE LA INFORMACIÓN E INNOVACION DIGITAL">ING.NME TEC DE LA INFORMACIÓN E INNOVACION DIGITAL</option>
                  <option value="ING. NME LOGISTICA">ING. NME LOGISTICA</option>
                  <option value="LIC. NME EDUCACIÓN">LIC. NME EDUCACIÓN</option>
                </select>
              </div>
              <div class="field">
                <label>Modalidad</label>
                <select class="input-plain input-sm" bind:value={formGrupo.modalidad} disabled={grupoCreado}>
                  <option value="bis">BIS</option>
                  <option value="intensivo">Intensivo</option>
                  <option value="mixta">Mixta</option>
                  <option value="despresurizada">Despresurizada</option>
                </select>
              </div>
              <div class="field">
                <label>Turno</label>
                <select class="input-plain input-sm" bind:value={formGrupo.turno} disabled={grupoCreado}>
                  <option value="Matutino">Matutino</option>
                  <option value="Vespertino">Vespertino</option>
                </select>
              </div>
              <div class="field">
                <label>Cuatrimestre</label>
                <select class="input-plain input-sm" bind:value={formGrupo.cuatrimestre} disabled={grupoCreado}>
                  {#each Array.from({length: 12}, (_, i) => i + 1) as n}
                    <option value={n}>{n}</option>
                  {/each}
                </select>
              </div>
              <div class="field">
                <label>Letra</label>
                <select class="input-plain input-sm" bind:value={formGrupo.letra} disabled={grupoCreado}>
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

                <button class="btn-primary" disabled={!archivoCSV || subiendoCSV} on:click={procesarCargaMasiva}>
                  {subiendoCSV ? 'Sincronizando...' : 'Ejecutar carga masiva'}
                </button>
              </div>

              {#if errorCSV}
                <div class="error-msg" style="margin-top:10px">{errorCSV}</div>
              {/if}

              {#if resultadoCSV}
                {@const total = resultadoCSV.insertados.length + resultadoCSV.actualizados.length + resultadoCSV.errores.length}
                <div class="resultado-csv">
                  {#if total === 0}
                    <p class="resultado-vacio">El archivo no contiene registros para procesar.</p>
                  {:else}
                    {#if resultadoCSV.insertados.length > 0}
                      <p class="resultado-ok">✓ {resultadoCSV.insertados.length} alumno{resultadoCSV.insertados.length !== 1 ? 's' : ''} insertado{resultadoCSV.insertados.length !== 1 ? 's' : ''} correctamente.</p>
                      <div class="resultado-alumnos">
                        <ul class="resultado-lista-alumnos">
                          {#each resultadoCSV.insertados as alumno}
                            <li><span class="ficha-mono">{alumno.matricula}</span> — {alumno.nombre}</li>
                          {/each}
                        </ul>
                      </div>
                    {/if}
                    {#if resultadoCSV.actualizados.length > 0}
                      <p class="resultado-actualizados">↻ {resultadoCSV.actualizados.length} alumno{resultadoCSV.actualizados.length !== 1 ? 's' : ''} ya existía{resultadoCSV.actualizados.length !== 1 ? 'n' : ''} y {resultadoCSV.actualizados.length !== 1 ? 'fueron' : 'fue'} reasignado{resultadoCSV.actualizados.length !== 1 ? 's' : ''} al grupo.</p>
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
            <p class="csv-instructions">Para actualizar o eliminar solo necesitas la matrícula. Para agregar, selecciona un grupo activo primero.</p>

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
                <button class="btn-eliminar" on:click={prepararEliminar}>Eliminar</button>
              </div>
            {/if}
          </div>

        </div>

      </div>
    </div>
  
  {:else if vista === 'expediente' && alumnoSeleccionado}
    <div class="page-wrap">
      <div class="expediente-topbar">
        <button class="btn-back" on:click={volverDirectorio}>
          <svg width="16" height="16" fill="none" stroke="currentColor" stroke-width="2.2" viewBox="0 0 24 24" style="display:inline; margin-right:4px; vertical-align:text-bottom;">
            <path stroke-linecap="round" stroke-linejoin="round" d="M10.5 19.5 L3 12 m0 0 l7.5-7.5 M3 12 h18" />
          </svg>
          Volver al directorio
        </button>

        {#if periodos.length > 0}
          <div class="periodo-selector">
            <label class="periodo-label" for="select-periodo">Periodo</label>
            <select
              id="select-periodo"
              class="input-plain input-sm"
              bind:value={periodoSeleccionado}
              on:change={cambiarPeriodo}
            >
              {#each periodos as p}
                <option value={p.cuatrimestre}>
                  {p.periodo_label || p.cuatrimestre}
                </option>
              {/each}
            </select>
          </div>
        {/if}
      </div>

      <div class="expediente-layout">
        <div class="ficha-card">
          <p class="ficha-titulo">Datos del alumno</p>
          <div class="ficha-divider"></div>
          <div class="ficha-grid">
            <span class="ficha-key">Nombre</span>
            <span class="ficha-val">{alumnoSeleccionado.nombre}</span>
            <span class="ficha-key">Matrícula</span>
            <span class="ficha-val ficha-mono">{alumnoSeleccionado.matricula}</span>
            <span class="ficha-key">Carrera</span>
            <span class="ficha-val">{carreraCompletaExpediente}</span>
            <span class="ficha-key">Grupo</span>
            <span class="ficha-val ficha-mono">{alumnoSeleccionado.nomenclatura || '—'}</span>
            <span class="ficha-key">Empresa</span>
            <span class="ficha-val bold-primary">{alumnoSeleccionado.empresa || 'Sin asignar'}</span>
            <span class="ficha-key">Turno</span>
            <span class="ficha-val">{alumnoSeleccionado.turno || '—'}</span>
          </div>

          {#if promedioExpediente}
            <div class="promedio-box">
              <p class="promedio-label">Promedio General</p>
              <p class="promedio-valor">{promedioExpediente}</p>
            </div>
          {/if}

          <div class="ficha-acciones">
            <button class="btn-primary" on:click={() => descargarCSV(alumnoSeleccionado.matricula)}>Exportar CSV</button>
            <button
              class="btn-outline"
              on:click={async () => {
                errorExpediente = ''
                try {
                  await api.dual.exportarZip(alumnoSeleccionado.matricula, periodoSeleccionado || undefined)
                } catch (e) {
                  errorExpediente = e.message || 'Error al descargar ZIP'
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

            {#if loadingExpediente}
              <LoadingSpinner />
            {:else if errorExpediente}
              <p class="error-msg">{errorExpediente}</p>
            {:else if reportes.length === 0}
              <EmptyState message="Este alumno no tiene reportes aprobados aún." />
            {:else}
              <div class="expediente-split">
                <div class="expediente-tabla-col">
                  <div class="table-wrap">
                    <table class="tabla">
                      <thead>
                        <tr>
                          <th>Semana</th>
                          <th class="td-center">Calif.</th>
                          <th></th>
                        </tr>
                      </thead>
                      <tbody>
                        {#each reportes as r}
                          <tr
                            class:row-selected={pdfSeleccionado?.id === r.id}
                            on:click={() => pdfSeleccionado = r}
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
                    {reportes.length} reporte{reportes.length !== 1 ? 's' : ''}
                  </p>
                </div>
                <div class="expediente-pdf-col">
                  <VisorPDF
                    url={pdfSeleccionado ? api.dual.reportePdfUrlCarrera(pdfSeleccionado.id) : ''}
                    titulo={pdfSeleccionado ? `Semana ${pdfSeleccionado.semana}` : 'Selecciona un reporte'}
                  />
                </div>
              </div>
            {/if}
          </div>
        </div>
      </div>
    </div>
  {/if}

  {#if modalEliminar}
    <div class="modal-overlay" on:click={() => modalEliminar = null}>
      <div class="modal-box" on:click|stopPropagation>
        <p class="modal-titulo">¿Eliminar alumno?</p>
        <p class="modal-cuerpo">
          Se eliminará completamente a <strong>{modalEliminar.nombre || modalEliminar.matricula}</strong> del sistema (datos, usuario, reportes y asignaciones duales). Esta acción no se puede deshacer.
        </p>
        <div class="modal-acciones">
          <button class="btn-eliminar" disabled={procesandoIndividual} on:click={confirmarEliminar}>
            {procesandoIndividual ? 'Eliminando...' : 'Sí, eliminar'}
          </button>
          <button class="btn-outline" disabled={procesandoIndividual} on:click={() => modalEliminar = null}>
            Cancelar
          </button>
        </div>
      </div>
    </div>
  {/if}

</div>

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
  .btn-pdf:hover { background: var(--orange-hover); color: white; border-color: var(--orange-hover); }

  .count-label { font-size: 12px; color: var(--text-disabled); text-align: right; margin-top: 4px; font-weight: 500; }

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
  
  .btn-eliminar { padding: 9px 18px; border: 1.5px solid var(--error); border-radius: var(--radius-input); background: transparent; color: var(--error); font-family: var(--font); font-size: 14px; font-weight: 600; cursor: pointer; transition: all 0.15s; }
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
  .resultado-ok { color: var(--success); font-weight: 600; font-size: 13px; margin: 0; }
  .resultado-actualizados { color: #d97706; font-weight: 600; font-size: 13px; margin: 0; }
  .resultado-vacio { color: var(--text-disabled); font-size: 13px; font-style: italic; margin: 0; }
  .resultado-alumnos { margin-top: 2px; }
  .resultado-lista-alumnos { margin: 0; padding-left: 16px; font-size: 12px; color: var(--text-secondary); display: flex; flex-direction: column; gap: 2px; }
  .resultado-err-titulo { color: var(--error); font-weight: 600; font-size: 12px; margin: 0; }
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