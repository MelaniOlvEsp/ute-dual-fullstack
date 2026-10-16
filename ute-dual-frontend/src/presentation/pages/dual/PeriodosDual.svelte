<script>
  // Períodos Dual: apertura y cierre manual por Coordinación (DP-04 / MP-18).
  import { onMount } from 'svelte'
  import { api } from '../../../composition/api.js'
  import Navbar from '../../components/layout/Navbar.svelte'
  import PageHeader from '../../components/ui/PageHeader.svelte'
  import { PERIODOS_CUATRIMESTRE, ANIOS_DISPONIBLES, etiquetaPeriodo, construirPeriodo, fechasPeriodo, formatearFechaCorta } from '../../../domain/dual/periods.js'

  let actual = null
  let cargando = true
  let errorEstado = ''

  let claveApertura = ''
  let anioApertura = new Date().getFullYear()
  let abriendo = false
  let errorApertura = ''
  let exitoApertura = ''

  let claveCierre = ''
  let anioCierre = new Date().getFullYear()
  let cerrando = false
  let errorCierre = ''
  let exitoCierre = ''

  $: fechasApertura = claveApertura && anioApertura
    ? fechasPeriodo(claveApertura, anioApertura)
    : { inicio: '', fin: '' }

  onMount(cargarEstado)

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
      errorCierre = ''
      exitoCierre = ''
      await cargarEstado()
    } catch (e) {
      errorApertura = e.message || 'No se pudo abrir el período.'
    } finally {
      abriendo = false
    }
  }

  async function cerrar() {
    exitoCierre = ''
    errorCierre = ''
    if (!claveCierre || !anioCierre) {
      errorCierre = 'Selecciona el período y el año.'
      return
    }
    const etiqueta = construirPeriodo(claveCierre, anioCierre)
    cerrando = true
    try {
      await api.dual.cerrarCuatrimestre(etiqueta)
      exitoCierre = `Período "${etiqueta}" cerrado correctamente.`
      errorApertura = ''
      exitoApertura = ''
      await cargarEstado()
    } catch (e) {
      errorCierre = e.message || 'No se pudo cerrar el período.'
    } finally {
      cerrando = false
    }
  }
</script>

<svelte:head><title>Períodos | Portal Dual</title></svelte:head>
<Navbar />
<main class="main-container">
  <div class="content-wrapper">
    <PageHeader title="Períodos" subtitle="Solo Coordinación Dual abre y cierra períodos. Las semanas de cada incorporación se asignan al período que contiene su domingo." />

    <section class="panel-card" aria-labelledby="estado-titulo">
      <h2 id="estado-titulo">Estado actual</h2>
      {#if cargando}
        <p class="nota">Cargando estado del período…</p>
      {:else if errorEstado}
        <p class="error-msg" role="alert">{errorEstado}</p>
        <button class="btn-outline" on:click={cargarEstado}>Reintentar</button>
      {:else if actual?.abierto}
        <p><span class="badge badge-abierto">Abierto</span> <strong>{actual.periodo_label || actual.cuatrimestre}</strong></p>
        {#if actual.fecha_inicio}
          <p class="nota">Del {formatearFechaCorta(actual.fecha_inicio)} al {formatearFechaCorta(actual.fecha_fin)}</p>
        {/if}
      {:else if actual?.cerrado}
        <p><span class="badge badge-cerrado">Cerrado</span> <strong>{actual.periodo_label || actual.cuatrimestre}</strong></p>
        <p class="nota">No hay un período abierto. Abre el siguiente cuando corresponda.</p>
      {:else}
        <p class="nota">Aún no hay períodos. Abre el primero.</p>
      {/if}
    </section>

    <div class="split-layout">
      <section class="panel-card" aria-labelledby="abrir-titulo">
        <h2 id="abrir-titulo">Abrir período</h2>
        <p class="nota">
          Se abre manualmente con fechas explícitas en la zona America/Mexico_City. Solo puede haber un período abierto
          y las fechas no pueden solaparse con otro período.
        </p>
        <label for="apertura-periodo">Período</label>
        <select id="apertura-periodo" class="input-plain" bind:value={claveApertura}>
          <option value="">Selecciona</option>
          {#each PERIODOS_CUATRIMESTRE as p}
            <option value={p.clave}>{etiquetaPeriodo(p.clave)}</option>
          {/each}
        </select>
        <label for="apertura-anio">Año</label>
        <select id="apertura-anio" class="input-plain" bind:value={anioApertura}>
          {#each ANIOS_DISPONIBLES as anio}
            <option value={anio}>{anio}</option>
          {/each}
        </select>
        {#if fechasApertura.inicio}
          <p class="nota">Del {formatearFechaCorta(fechasApertura.inicio)} al {formatearFechaCorta(fechasApertura.fin)}</p>
        {/if}
        {#if errorApertura}<p class="error-msg" role="alert">{errorApertura}</p>{/if}
        {#if exitoApertura}<p class="success-msg" role="status">{exitoApertura}</p>{/if}
        <button class="btn-primary" disabled={abriendo} on:click={abrir}>
          {abriendo ? 'Abriendo...' : 'Abrir período'}
        </button>
      </section>

      <section class="panel-card" aria-labelledby="cerrar-titulo">
        <h2 id="cerrar-titulo">Cerrar período</h2>
        <p class="nota">
          Cierra la recepción del período indicado: los alumnos ya no podrán subir nuevos reportes para él.
          El tutor conserva la revisión de lo ya recibido.
        </p>
        <label for="cierre-periodo">Período</label>
        <select id="cierre-periodo" class="input-plain" bind:value={claveCierre}>
          <option value="">Selecciona</option>
          {#each PERIODOS_CUATRIMESTRE as p}
            <option value={p.clave}>{etiquetaPeriodo(p.clave)}</option>
          {/each}
        </select>
        <label for="cierre-anio">Año</label>
        <select id="cierre-anio" class="input-plain" bind:value={anioCierre}>
          {#each ANIOS_DISPONIBLES as anio}
            <option value={anio}>{anio}</option>
          {/each}
        </select>
        {#if errorCierre}<p class="error-msg" role="alert">{errorCierre}</p>{/if}
        {#if exitoCierre}<p class="success-msg" role="status">{exitoCierre}</p>{/if}
        <button class="btn-danger" disabled={cerrando} on:click={cerrar}>
          {cerrando ? 'Cerrando...' : 'Cerrar período'}
        </button>
      </section>
    </div>
  </div>
</main>

<style>
  .main-container { padding-top: 56px; min-height: 100vh; background: var(--bg-page); }
  .content-wrapper { max-width: 1100px; margin: 0 auto; padding: 32px 24px; display: flex; flex-direction: column; gap: 20px; }
  .split-layout { display: grid; grid-template-columns: 1fr 1fr; gap: 24px; align-items: start; }
  .panel-card { background: var(--bg-card); border: 1px solid var(--border); border-radius: var(--radius-card); padding: 24px; display: flex; flex-direction: column; gap: 12px; }
  .panel-card h2 { font-size: 18px; color: var(--text-primary); }
  .nota { font-size: 13px; color: var(--text-secondary); }
  .badge { display: inline-block; font-size: 12px; font-weight: 700; color: var(--text-primary); border: 1px solid; border-radius: 999px; padding: 2px 10px; margin-right: 6px; }
  .badge-abierto { border-color: var(--success); background: color-mix(in srgb, var(--success) 14%, transparent); }
  .badge-cerrado { border-color: var(--border-input); background: color-mix(in srgb, var(--text-disabled) 14%, transparent); }
  .btn-danger { background: var(--error); color: white; border: none; border-radius: var(--radius-btn); padding: 12px 20px; font-size: 14px; font-weight: 700; cursor: pointer; font-family: var(--font); }
  .btn-danger:disabled { opacity: 0.5; cursor: not-allowed; }
  .success-msg { color: var(--text-primary); border-left: 3px solid var(--success); padding-left: 10px; }
  .error-msg { color: var(--error); }
  @media (max-width: 860px) { .split-layout { grid-template-columns: 1fr; } }
</style>
