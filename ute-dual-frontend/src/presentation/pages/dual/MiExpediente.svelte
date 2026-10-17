<script>
  // «Mi expediente» (C08): el alumno consulta sus períodos y descarga solo lo propio. La matrícula la
  // toma el servidor de la sesión; esta página nunca envía una matrícula.
  import { onMount } from 'svelte'
  import { api } from '../../../composition/api.js'
  import Navbar from '../../components/layout/Navbar.svelte'
  import PageHeader from '../../components/ui/PageHeader.svelte'
  import LoadingSpinner from '../../components/ui/LoadingSpinner.svelte'
  import ExpedienteAlumno from '../../components/dual/ExpedienteAlumno.svelte'
  import { mensajeVentana } from '../../../domain/dual/expediente.js'
  import { formatFechaCivil } from '../../utils/formatters.js'

  let datos = null
  let cargando = true
  let error = ''

  // Aviso destacado de los paquetes que aún se pueden descargar (una semana desde la finalización).
  $: disponibles = (datos?.periodos || []).filter(p => p.paquete?.disponible && p.paquete?.hasta)

  onMount(cargar)

  async function cargar() {
    cargando = true
    error = ''
    try {
      datos = await api.dual.miExpediente()
    } catch (e) {
      datos = null
      error = e.message || 'No se pudo cargar tu expediente.'
    } finally {
      cargando = false
    }
  }
</script>

<svelte:head><title>Mi expediente | Portal UTE</title></svelte:head>
<Navbar />
<main class="pagina">
  <div class="contenido">
    <PageHeader title="Mi expediente" subtitle="Tus reportes aprobados, notas y promedio por período. Solo tú puedes ver esta información." />

    {#each disponibles as p (p.periodo.id)}
      <p class="aviso" role="status">
        <strong>{p.periodo.periodo_label}:</strong> {mensajeVentana(p.paquete, formatFechaCivil)}
      </p>
    {/each}

    {#if cargando}
      <LoadingSpinner />
    {:else if error}
      <div class="error-caja" role="alert">
        <p>{error}</p>
        <button class="btn-outline" on:click={cargar}>Reintentar</button>
      </div>
    {:else}
      <ExpedienteAlumno {datos} modo="alumno" />
    {/if}
  </div>
</main>

<style>
  .pagina { padding-top: 56px; min-height: 100vh; background: var(--bg-page); }
  .contenido { max-width: 1000px; margin: 0 auto; padding: 32px 24px 64px; display: flex; flex-direction: column; gap: 20px; }
  .aviso { margin: 0; padding: 12px 16px; font-size: 14px; color: var(--text-primary); border: 1px solid var(--border); border-left: 3px solid var(--orange); border-radius: 8px; background: var(--bg-card); }
  .error-caja { display: flex; flex-direction: column; gap: 10px; align-items: flex-start; color: var(--error); }
  .error-caja p { margin: 0; }
</style>
