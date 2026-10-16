<script>
  // Períodos Dual: apertura, cierre de recepción y finalización de la evaluación por Coordinación
  // (DP-04 / MP-11 / MP-18). La recepción y la evaluación son independientes de las fechas calendario.
  import { onMount } from 'svelte'
  import { api } from '../../../composition/api.js'
  import Navbar from '../../components/layout/Navbar.svelte'
  import PageHeader from '../../components/ui/PageHeader.svelte'
  import { PERIODOS_CUATRIMESTRE, ANIOS_DISPONIBLES, etiquetaPeriodo, construirPeriodo, fechasPeriodo, formatearFechaCorta } from '../../../domain/dual/periods.js'
  import { etiquetaRecepcion, etiquetaEvaluacion, mensajeCierre, mensajeFinalizacion } from '../../../domain/dual/closure.js'

  let actual = null
  let cargando = true
  let errorEstado = ''

  let claveApertura = ''
  let anioApertura = new Date().getFullYear()
  let abriendo = false
  let errorApertura = ''
  let exitoApertura = ''

  // Panel por período (C07)
  let periodos = []
  let periodoId = ''
  let resumen = null
  let cargandoResumen = false
  let errorResumen = ''
  let confirmando = ''
  let ejecutando = false
  let errorAccion = ''
  let exitoAccion = ''

  $: fechasApertura = claveApertura && anioApertura
    ? fechasPeriodo(claveApertura, anioApertura)
    : { inicio: '', fin: '' }

  $: conteos = resumen?.conteos
  $: periodo = resumen?.periodo
  $: alumnos = resumen?.alumnos || []

  onMount(async () => {
    await cargarEstado()
    await cargarPeriodos()
  })

  async function cargarEstado() {
    cargando = true
    errorEstado = ''
    try {
      actual = await api.dual.cuatrimestreActual()
    } catch (e) {
      actual = null
      errorEstado = e.message || 'No se pudo cargar el estado del período.'
    } finally {
      cargando = false
    }
  }

  async function cargarPeriodos() {
    try {
      periodos = (await api.dual.periodosEstado()).filter(p => p.recepcion !== 'sin_abrir')
      if (periodos.length && !periodos.some(p => p.id === periodoId)) {
        periodoId = (periodos.find(p => p.recepcion === 'abierta') || periodos[0]).id
      }
      if (periodoId) await cargarResumen()
    } catch (e) {
      periodos = []
      errorResumen = e.message || 'No se pudieron cargar los períodos.'
    }
  }

  async function cargarResumen() {
    cargandoResumen = true
    errorResumen = ''
    confirmando = ''
    try {
      resumen = await api.dual.resumenPeriodo(periodoId)
    } catch (e) {
      resumen = null
      errorResumen = e.message || 'No se pudo cargar el resumen del período.'
    } finally {
      cargandoResumen = false
    }
  }

  async function abrir() {
    exitoApertura = ''
    errorApertura = ''
    if (!claveApertura || !anioApertura) {
      errorApertura = 'Selecciona el período y el año.'
      return
    }
    const etiqueta = construirPeriodo(claveApertura, anioApertura)
    const { inicio, fin } = fechasPeriodo(claveApertura, anioApertura)
    abriendo = true
    try {
      await api.dual.abrirCuatrimestre({ periodo_label: etiqueta, fecha_inicio: inicio, fecha_fin: fin })
      exitoApertura = `Período "${etiqueta}" abierto correctamente.`
      exitoAccion = ''
      await cargarEstado()
      periodoId = ''
      await cargarPeriodos()
    } catch (e) {
      errorApertura = e.message || 'No se pudo abrir el período.'
    } finally {
      abriendo = false
    }
  }

  async function ejecutar() {
    errorAccion = ''
    exitoAccion = ''
    ejecutando = true
    try {
      const respuesta = confirmando === 'cierre'
        ? await api.dual.cerrarRecepcion(periodoId)
        : await api.dual.finalizarEvaluacion(periodoId)
      exitoAccion = confirmando === 'cierre'
        ? `Recepción de "${respuesta.periodo.periodo_label}" cerrada. El tutor puede seguir revisando lo recibido.`
        : `Evaluación de "${respuesta.periodo.periodo_label}" finalizada. Los promedios quedaron finales.`
      confirmando = ''
      await cargarEstado()
      await cargarPeriodos()
    } catch (e) {
      errorAccion = e.message || 'No se pudo completar la acción.'
      confirmando = ''
      await cargarResumen()
    } finally {
      ejecutando = false
    }
  }
</script>

<svelte:head><title>Períodos | Portal Dual</title></svelte:head>
<Navbar />
<main class="main-container">
  <div class="content-wrapper">
    <PageHeader title="Períodos" subtitle="Solo Coordinación Dual abre períodos, cierra la recepción y finaliza la evaluación. Las semanas de cada incorporación se asignan al período que contiene su domingo." />

    <section class="panel-card" aria-labelledby="estado-titulo">
      <h2 id="estado-titulo">Estado actual</h2>
      {#if cargando}
        <p class="nota">Cargando estado del período…</p>
      {:else if errorEstado}
        <p class="error-msg" role="alert">{errorEstado}</p>
        <button class="btn-outline" on:click={cargarEstado}>Reintentar</button>
      {:else if actual?.abierto}
        <p><span class="badge badge-abierto">Recepción abierta</span> <strong>{actual.periodo_label || actual.cuatrimestre}</strong></p>
        {#if actual.fecha_inicio}
          <p class="nota">Del {formatearFechaCorta(actual.fecha_inicio)} al {formatearFechaCorta(actual.fecha_fin)}</p>
        {/if}
      {:else if actual?.cerrado}
        <p><span class="badge badge-cerrado">Recepción cerrada</span> <strong>{actual.periodo_label || actual.cuatrimestre}</strong></p>
        <p class="nota">No hay un período recibiendo entregas. Abre el siguiente cuando corresponda.</p>
      {:else}
        <p class="nota">Aún no hay períodos. Abre el primero.</p>
      {/if}
    </section>

    <section class="panel-card" aria-labelledby="abrir-titulo">
      <h2 id="abrir-titulo">Abrir período</h2>
      <p class="nota">
        Se abre manualmente con fechas explícitas en la zona America/Mexico_City. Solo un período recibe entregas a la vez,
        las fechas no pueden solaparse con otro período y un período cerrado no se reabre.
      </p>
      <div class="fila-abrir">
        <div class="campo">
          <label for="apertura-periodo">Período</label>
          <select id="apertura-periodo" class="input-plain" bind:value={claveApertura}>
            <option value="">Selecciona</option>
            {#each PERIODOS_CUATRIMESTRE as p}
              <option value={p.clave}>{etiquetaPeriodo(p.clave)}</option>
            {/each}
          </select>
        </div>
        <div class="campo">
          <label for="apertura-anio">Año</label>
          <select id="apertura-anio" class="input-plain" bind:value={anioApertura}>
            {#each ANIOS_DISPONIBLES as anio}
              <option value={anio}>{anio}</option>
            {/each}
          </select>
        </div>
      </div>
      {#if fechasApertura.inicio}
        <p class="nota">Del {formatearFechaCorta(fechasApertura.inicio)} al {formatearFechaCorta(fechasApertura.fin)}</p>
      {/if}
      {#if errorApertura}<p class="error-msg" role="alert">{errorApertura}</p>{/if}
      {#if exitoApertura}<p class="success-msg" role="status">{exitoApertura}</p>{/if}
      <button class="btn-primary" disabled={abriendo} on:click={abrir}>
        {abriendo ? 'Abriendo...' : 'Abrir período'}
      </button>
    </section>

    <section class="panel-card" aria-labelledby="cierre-titulo">
      <h2 id="cierre-titulo">Cierre y calificación</h2>
      {#if !periodos.length}
        <p class="nota">Cuando abras un período podrás cerrar su recepción y finalizar la evaluación aquí.</p>
      {:else}
        <label for="periodo-panel">Período</label>
        <select id="periodo-panel" class="input-plain" bind:value={periodoId} on:change={() => { exitoAccion = ''; errorAccion = ''; cargarResumen() }}>
          {#each periodos as p (p.id)}
            <option value={p.id}>{p.periodo_label} · {etiquetaRecepcion(p.recepcion)} · {etiquetaEvaluacion(p.evaluacion)}</option>
          {/each}
        </select>

        {#if cargandoResumen}
          <p class="nota">Cargando resumen…</p>
        {:else if errorResumen}
          <p class="error-msg" role="alert">{errorResumen}</p>
        {:else if resumen}
          <div class="estados">
            <span class="badge" class:badge-abierto={periodo.recepcion === 'abierta'} class:badge-cerrado={periodo.recepcion !== 'abierta'}>{etiquetaRecepcion(periodo.recepcion)}</span>
            <span class="badge" class:badge-final={periodo.evaluacion === 'finalizada'} class:badge-cerrado={periodo.evaluacion !== 'finalizada'}>{etiquetaEvaluacion(periodo.evaluacion)}</span>
          </div>
          <p class="nota">
            Calendario: {formatearFechaCorta(periodo.fecha_inicio)} – {formatearFechaCorta(periodo.fecha_fin)}
            {#if periodo.cierre_efectivo}· Recepción cerrada el {formatearFechaCorta(periodo.cierre_efectivo)}{/if}
          </p>

          <dl class="conteos">
            <div><dt>Semanas</dt><dd>{conteos.obligaciones}</dd></div>
            <div><dt>Recibidas</dt><dd>{conteos.recibidas}</dd></div>
            <div><dt>Por revisar</dt><dd>{conteos.pendientes_revision}</dd></div>
            <div><dt>Aprobadas</dt><dd>{conteos.aprobadas}</dd></div>
            <div><dt>Rechazadas</dt><dd>{conteos.rechazadas}</dd></div>
            <div><dt>Sin entrega</dt><dd>{conteos.sin_entrega}</dd></div>
            <div><dt>No recibidas por cierre</dt><dd>{conteos.no_recibidas_por_cierre}</dd></div>
          </dl>

          {#if alumnos.length}
            <div class="tabla-wrap" role="region" aria-label="Promedios por alumno">
              <table class="tabla">
                <thead>
                  <tr><th>Matrícula</th><th>Alumno</th><th>Grupo</th><th class="num">Aprobados</th><th class="num">Promedio</th></tr>
                </thead>
                <tbody>
                  {#each alumnos as a (a.matricula)}
                    <tr>
                      <td>{a.matricula}</td>
                      <td>{a.nombre}</td>
                      <td>{a.nomenclatura || '—'}</td>
                      <td class="num">{a.aprobados}</td>
                      <td class="num">
                        {a.promedio_texto}
                        <span class="tipo-promedio">{a.definitivo ? 'final' : 'provisional'}</span>
                      </td>
                    </tr>
                  {/each}
                </tbody>
              </table>
            </div>
          {:else}
            <p class="nota">Este período aún no tiene semanas de alumnos.</p>
          {/if}

          {#if errorAccion}<p class="error-msg" role="alert">{errorAccion}</p>{/if}
          {#if exitoAccion}<p class="success-msg" role="status">{exitoAccion}</p>{/if}

          {#if confirmando}
            <div class="confirmacion" role="alertdialog" aria-labelledby="confirmar-titulo" aria-describedby="confirmar-texto">
              <h3 id="confirmar-titulo">{confirmando === 'cierre' ? 'Cerrar recepción' : 'Finalizar evaluación'} · {periodo.periodo_label}</h3>
              <p id="confirmar-texto">{confirmando === 'cierre' ? mensajeCierre(periodo, conteos) : mensajeFinalizacion(periodo, alumnos)}</p>
              <div class="acciones">
                <button class="btn-danger" disabled={ejecutando} on:click={ejecutar}>
                  {ejecutando ? 'Procesando...' : 'Confirmar'}
                </button>
                <button class="btn-outline" disabled={ejecutando} on:click={() => confirmando = ''}>Cancelar</button>
              </div>
            </div>
          {:else}
            <div class="acciones">
              {#if resumen.puede_cerrar_recepcion}
                <button class="btn-danger" on:click={() => { confirmando = 'cierre'; errorAccion = ''; exitoAccion = '' }}>Cerrar recepción</button>
              {/if}
              {#if periodo.recepcion === 'cerrada' && periodo.evaluacion !== 'finalizada'}
                <button class="btn-primary" disabled={!resumen.puede_finalizar}
                  on:click={() => { confirmando = 'finalizar'; errorAccion = ''; exitoAccion = '' }}>
                  Finalizar evaluación
                </button>
              {/if}
            </div>
            {#if resumen.motivo_finalizar && periodo.recepcion === 'cerrada' && periodo.evaluacion !== 'finalizada'}
              <p class="nota" role="status">{resumen.motivo_finalizar}</p>
            {/if}
          {/if}
        {/if}
      {/if}
    </section>
  </div>
</main>

<style>
  .main-container { padding-top: 56px; min-height: 100vh; background: var(--bg-page); }
  .content-wrapper { max-width: 1100px; margin: 0 auto; padding: 32px 24px; display: flex; flex-direction: column; gap: 20px; }
  .panel-card { background: var(--bg-card); border: 1px solid var(--border); border-radius: var(--radius-card); padding: 24px; display: flex; flex-direction: column; gap: 12px; }
  .panel-card h2 { font-size: 18px; color: var(--text-primary); }
  .nota { font-size: 13px; color: var(--text-secondary); }
  .fila-abrir { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
  .campo { display: flex; flex-direction: column; gap: 6px; }
  .estados { display: flex; gap: 8px; flex-wrap: wrap; }
  .badge { display: inline-block; font-size: 12px; font-weight: 700; color: var(--text-primary); border: 1px solid; border-radius: 999px; padding: 2px 10px; margin-right: 6px; }
  .badge-abierto { border-color: var(--success); background: color-mix(in srgb, var(--success) 14%, transparent); }
  .badge-cerrado { border-color: var(--border-input); background: color-mix(in srgb, var(--text-disabled) 14%, transparent); }
  .badge-final { border-color: var(--orange); background: color-mix(in srgb, var(--orange) 14%, transparent); }
  .conteos { display: grid; grid-template-columns: repeat(auto-fit, minmax(120px, 1fr)); gap: 10px; margin: 0; }
  .conteos div { border: 1px solid var(--border); border-radius: 10px; padding: 10px 12px; background: var(--bg-page); }
  .conteos dt { font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.04em; color: var(--text-disabled); }
  .conteos dd { margin: 4px 0 0; font-size: 22px; font-weight: 800; color: var(--text-primary); }
  .tabla-wrap { position: relative; overflow: auto; max-height: 420px; border: 1px solid var(--border); border-radius: 10px; }
  .tabla thead th { position: sticky; top: 0; background: var(--bg-card); }
  .tabla { width: 100%; min-width: 520px; border-collapse: collapse; font-size: 13px; }
  .tabla th { text-align: left; padding: 8px 10px; font-size: 11px; text-transform: uppercase; color: var(--text-disabled); border-bottom: 1px solid var(--border); white-space: nowrap; }
  .tabla td { padding: 8px 10px; color: var(--text-secondary); border-bottom: 1px solid var(--border); }
  .tabla tbody tr:last-child td { border-bottom: none; }
  .num { text-align: right; }
  .tipo-promedio { display: block; font-size: 11px; color: var(--text-disabled); }
  .acciones { display: flex; gap: 10px; flex-wrap: wrap; }
  .confirmacion { border: 1px solid var(--error); border-radius: 12px; padding: 16px; display: flex; flex-direction: column; gap: 10px; background: color-mix(in srgb, var(--error) 6%, transparent); }
  .confirmacion h3 { font-size: 15px; color: var(--text-primary); }
  .btn-danger { background: var(--error); color: white; border: none; border-radius: var(--radius-btn); padding: 12px 20px; font-size: 14px; font-weight: 700; cursor: pointer; font-family: var(--font); }
  .btn-danger:disabled, .btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }
  .success-msg { color: var(--text-primary); border-left: 3px solid var(--success); padding-left: 10px; }
  .error-msg { color: var(--error); }
  @media (max-width: 860px) { .fila-abrir { grid-template-columns: 1fr; } }
</style>
